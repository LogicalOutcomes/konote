"""AI-powered FHIR metadata inference for PlanTargets.

Uses the existing OpenRouter integration (konote/ai.py pattern) to classify:
- continuous: maintenance vs. time-bound goal
- target_date: extract temporal language from goal descriptions

PII safety: Only goal name/description text is sent to LLM.
Never client names, identifiers, or note content.
"""
import json
import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

logger = logging.getLogger(__name__)

GOAL_METADATA_PROMPT = """You are a metadata classifier for a nonprofit outcome tracking system.
You will receive a goal name and description. Classify the following:

1. "continuous": Is this an ongoing maintenance goal (true) or a time-bound achievement goal (false)?
   - Ongoing examples: "maintain sobriety", "continue attending school", "stay housed", "manage anxiety"
   - Time-bound examples: "find housing", "complete GED", "get a job", "enrol in college"

2. "target_months": If the description contains temporal language, extract the number of months as an integer.
   - "within 6 months" → 6
   - "by the end of the year" → estimate months remaining
   - "in 3 weeks" → 1
   - No temporal language → null

Return ONLY valid JSON: {"continuous": true/false, "target_months": number|null}"""


class Command(BaseCommand):
    help = "AI-powered FHIR metadata inference for PlanTargets"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Show what would be classified without saving")
        parser.add_argument("--batch-size", type=int, default=50, help="Max targets to process per run")
        parser.add_argument(
            "--fields", nargs="+", default=["continuous", "target_date"],
            choices=["continuous", "target_date"],
            help="Which fields to infer",
        )

    def handle(self, *args, **options):
        from apps.plans.models import PlanTarget

        dry_run = options["dry_run"]
        batch_size = options["batch_size"]
        fields = options["fields"]

        # Check if AI is configured
        api_key = self._get_api_key()
        if not api_key:
            self.stdout.write(self.style.WARNING(
                "OPENROUTER_API_KEY not configured — cannot run AI inference"
            ))
            return

        # Find targets needing classification (only active/on_hold goals with a name)
        base_qs = PlanTarget.objects.exclude(
            _name_encrypted=b"",
        ).filter(
            status__in=["default", "on_hold"],
        )

        total_processed = 0

        if "continuous" in fields:
            needs_continuous = base_qs.exclude(
                metadata_sources__has_key="continuous",
            )[:batch_size]
            count = self._infer_batch(needs_continuous, dry_run, api_key, "continuous")
            total_processed += count

        if "target_date" in fields:
            remaining = max(0, batch_size - total_processed)
            if remaining > 0:
                needs_target = base_qs.filter(
                    target_date__isnull=True,
                ).exclude(
                    metadata_sources__has_key="target_date",
                )[:remaining]
                count = self._infer_batch(needs_target, dry_run, api_key, "target_date")
                total_processed += count

        self.stdout.write(self.style.SUCCESS(
            f"{'[DRY RUN] ' if dry_run else ''}Total processed: {total_processed}"
        ))

    def _infer_batch(self, queryset, dry_run, api_key, field_name):
        """Process targets for a specific field."""
        targets = list(queryset)
        if not targets:
            self.stdout.write(f"No targets need {field_name} inference")
            return 0

        self.stdout.write(f"Processing {len(targets)} targets for {field_name}...")
        processed = 0

        for target in targets:
            try:
                goal_name = target.name or ""
                goal_desc = target.description or ""
                if not goal_name:
                    continue

                prompt_text = f"Goal: {goal_name}"
                if goal_desc:
                    prompt_text += f"\nDescription: {goal_desc}"

                result = self._call_llm(api_key, GOAL_METADATA_PROMPT, prompt_text)
                if not result:
                    continue

                parsed = self._parse_json(result)
                if not parsed:
                    logger.warning(f"Could not parse LLM response for target {target.pk}: {result[:200]}")
                    continue

                meta = target.metadata_sources if isinstance(target.metadata_sources, dict) else {}
                update_fields = []

                if field_name == "continuous" and "continuous" in parsed:
                    target.continuous = bool(parsed["continuous"])
                    meta["continuous"] = "ai_inferred"
                    update_fields.extend(["continuous", "metadata_sources"])

                if field_name == "target_date" and parsed.get("target_months"):
                    try:
                        months = int(parsed["target_months"])
                        if 0 < months <= 120:  # Sanity check: 0-10 years
                            target.target_date = (target.created_at + timedelta(days=months * 30)).date()
                            meta["target_date"] = "ai_inferred"
                            update_fields.extend(["target_date", "metadata_sources"])
                    except (ValueError, TypeError):
                        pass

                if update_fields:
                    target.metadata_sources = meta
                    if not dry_run:
                        target.save(update_fields=list(set(update_fields)))
                    processed += 1
                    if not dry_run:
                        self.stdout.write(f"  {field_name}: {target.pk} → classified")
                    else:
                        self.stdout.write(f"  [DRY RUN] {field_name}: {target.pk} → would classify")

            except Exception as e:
                logger.warning(f"Failed to infer {field_name} for PlanTarget {target.pk}: {e}")
                continue

        prefix = "[DRY RUN] " if dry_run else ""
        self.stdout.write(self.style.SUCCESS(
            f"{prefix}Processed {processed}/{len(targets)} targets for {field_name}"
        ))
        return processed

    def _get_api_key(self):
        """Get OpenRouter API key from Django settings."""
        from django.conf import settings as django_settings
        return getattr(django_settings, "OPENROUTER_API_KEY", "")

    def _call_llm(self, api_key, system_prompt, user_message):
        """Call LLM via OpenRouter (matches konote/ai.py pattern)."""
        import requests

        try:
            resp = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "anthropic/claude-sonnet-4",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    "max_tokens": 200,
                    "temperature": 0.0,
                },
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            logger.warning(f"LLM call failed: {e}")
            return None

    def _parse_json(self, text):
        """Extract JSON from LLM response (handles markdown wrapping)."""
        # Try direct parse first
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            pass

        # Try extracting from markdown code block
        import re
        match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # Try finding first JSON object
        match = re.search(r'\{[^{}]*\}', text)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        return None
