"""Import CIDS code lists from Common Approach.

Fetches code lists from codelist.commonapproach.org and upserts them
into the CidsCodeList table. Supports --dry-run and --force flags.

Usage:
    python manage.py import_cids_codelists
    python manage.py import_cids_codelists --dry-run
    python manage.py import_cids_codelists --force
    python manage.py import_cids_codelists --lists ICNPOsector SDGImpacts
"""
import json
import logging
from datetime import date

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)

# The 17 CIDS code lists, ordered by relevance (High/Medium first).
# Each entry: (list_name, description, defined_by_name, defined_by_uri)
CODE_LIST_REGISTRY = [
    # High relevance
    ("ICNPOsector", "International Classification of Nonprofit Organizations",
     "United Nations", "https://unstats.un.org"),
    ("SDGImpacts", "UN Sustainable Development Goals",
     "United Nations", "https://sdgs.un.org"),
    ("IRISImpactTheme", "IRIS+ Impact Themes",
     "GIIN", "https://iris.thegiin.org"),
    ("IrisMetric53", "IRIS+ Core Metric Set",
     "GIIN", "https://iris.thegiin.org"),
    ("PopulationServed", "Population Served",
     "Common Approach", "https://commonapproach.org"),
    # Medium relevance
    ("ESDCSector", "ESDC Sector Codes",
     "Employment and Social Development Canada", "https://www.canada.ca/en/employment-social-development.html"),
    ("UnitsOfMeasureList", "Units of Measure",
     "Common Approach", "https://commonapproach.org"),
    ("IRISImpactCategory", "IRIS+ Impact Categories",
     "GIIN", "https://iris.thegiin.org"),
    ("EquityDeservingGroupsESDC", "Equity-Deserving Groups (ESDC)",
     "Employment and Social Development Canada", "https://www.canada.ca/en/employment-social-development.html"),
    ("ProvinceTerritory", "Canadian Provinces and Territories",
     "Statistics Canada", "https://www.statcan.gc.ca"),
    # Lower relevance (still imported)
    ("OrgTypeGOC", "Organisation Type (Government of Canada)",
     "Government of Canada", "https://www.canada.ca"),
    ("CanadianCorporateRegistries", "Canadian Corporate Registries",
     "Government of Canada", "https://www.canada.ca"),
    ("LocalityStatsCan", "Locality (Statistics Canada)",
     "Statistics Canada", "https://www.statcan.gc.ca"),
    ("FundingState", "Funding State",
     "Common Approach", "https://commonapproach.org"),
    ("RallyImpactArea", "Rally Impact Area",
     "Rally Assets", "https://rallyassets.com"),
    ("SELI-GLI", "SELI-GLI Indicators",
     "Common Approach", "https://commonapproach.org"),
    ("StatsCanSector", "Statistics Canada Sector Codes",
     "Statistics Canada", "https://www.statcan.gc.ca"),
]

BASE_URL = "https://codelist.commonapproach.org/api/v1"


def fetch_code_list(list_name, base_url=None):
    """Fetch a single code list from the Common Approach API.

    Returns a list of dicts with keys: code, label, label_fr, description.
    Raises ConnectionError or ValueError on failure.
    """
    import urllib.request
    import urllib.error

    url = f"{base_url or BASE_URL}/{list_name}.json"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError) as exc:
        raise ConnectionError(f"Failed to fetch {url}: {exc}") from exc

    # Normalise response — API may return a list or a dict with an "entries" key
    if isinstance(data, dict):
        entries = data.get("entries", data.get("codes", data.get("items", [])))
        version_date = data.get("versionDate", data.get("version_date"))
        spec_uri = data.get("specificationUri", data.get("specification_uri", ""))
    elif isinstance(data, list):
        entries = data
        version_date = None
        spec_uri = ""
    else:
        raise ValueError(f"Unexpected response format from {url}")

    results = []
    for entry in entries:
        results.append({
            "code": str(entry.get("code", entry.get("id", ""))),
            "label": entry.get("label", entry.get("name", "")),
            "label_fr": entry.get("label_fr", entry.get("labelFr", "")),
            "description": entry.get("description", ""),
        })

    return results, version_date, spec_uri


class Command(BaseCommand):
    help = "Import CIDS code lists from Common Approach (codelist.commonapproach.org)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would change without writing to the database.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Re-import even if version_date matches.",
        )
        parser.add_argument(
            "--lists",
            nargs="+",
            help="Only import specific code lists (by name).",
        )
        parser.add_argument(
            "--base-url",
            default=BASE_URL,
            help=f"Override the API base URL (default: {BASE_URL}).",
        )

    def handle(self, *args, **options):
        from apps.admin_settings.models import CidsCodeList

        dry_run = options["dry_run"]
        force = options["force"]
        filter_lists = options.get("lists")
        base_url = options["base_url"]

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes will be written.\n"))

        lists_to_import = CODE_LIST_REGISTRY
        if filter_lists:
            filter_set = set(filter_lists)
            lists_to_import = [
                entry for entry in CODE_LIST_REGISTRY
                if entry[0] in filter_set
            ]
            unknown = filter_set - {e[0] for e in lists_to_import}
            if unknown:
                self.stderr.write(self.style.WARNING(
                    f"Unknown code lists: {', '.join(sorted(unknown))}"
                ))

        total_created = 0
        total_updated = 0
        total_skipped = 0
        errors = []

        for list_name, desc, defined_by_name, defined_by_uri in lists_to_import:
            self.stdout.write(f"\n  Importing {list_name}...")
            try:
                entries, version_date, spec_uri = fetch_code_list(list_name, base_url)
            except (ConnectionError, ValueError) as exc:
                errors.append((list_name, str(exc)))
                self.stderr.write(self.style.ERROR(f"    FAILED: {exc}"))
                continue

            if not entries:
                self.stdout.write(self.style.WARNING(f"    No entries found."))
                continue

            # Parse version_date
            parsed_version = None
            if version_date:
                try:
                    parsed_version = date.fromisoformat(str(version_date)[:10])
                except (ValueError, TypeError):
                    pass

            # Check staleness
            if not force and parsed_version:
                existing_date = (
                    CidsCodeList.objects.filter(list_name=list_name)
                    .values_list("version_date", flat=True)
                    .first()
                )
                if existing_date and existing_date >= parsed_version:
                    self.stdout.write(f"    Up to date (local: {existing_date}, remote: {parsed_version}). Use --force to reimport.")
                    total_skipped += len(entries)
                    continue

            created = 0
            updated = 0

            for entry in entries:
                code = entry["code"]
                if not code:
                    continue

                defaults = {
                    "label": entry["label"],
                    "label_fr": entry.get("label_fr", ""),
                    "description": entry.get("description", ""),
                    "specification_uri": spec_uri or "",
                    "defined_by_name": defined_by_name,
                    "defined_by_uri": defined_by_uri,
                    "source_url": f"https://codelist.commonapproach.org/{list_name}",
                }
                if parsed_version:
                    defaults["version_date"] = parsed_version

                if dry_run:
                    exists = CidsCodeList.objects.filter(
                        list_name=list_name, code=code,
                    ).exists()
                    if exists:
                        updated += 1
                    else:
                        created += 1
                else:
                    _obj, was_created = CidsCodeList.objects.update_or_create(
                        list_name=list_name,
                        code=code,
                        defaults=defaults,
                    )
                    if was_created:
                        created += 1
                    else:
                        updated += 1

            total_created += created
            total_updated += updated
            action = "Would create" if dry_run else "Created"
            self.stdout.write(
                f"    {action} {created}, updated {updated} entries."
            )

        # Summary
        self.stdout.write("")
        if errors:
            self.stderr.write(self.style.ERROR(
                f"  {len(errors)} list(s) failed: {', '.join(e[0] for e in errors)}"
            ))
        summary = (
            f"  Total: {total_created} created, {total_updated} updated, "
            f"{total_skipped} skipped."
        )
        if dry_run:
            self.stdout.write(self.style.WARNING(summary + " (DRY RUN)"))
        else:
            self.stdout.write(self.style.SUCCESS(summary))
