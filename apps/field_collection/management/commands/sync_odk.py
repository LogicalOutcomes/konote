"""Sync data between KoNote and ODK Central.

Push: participant/group Entity lists from KoNote → ODK Central
Pull: form submissions from ODK Central → KoNote records

Usage:
    python manage.py sync_odk                    # Both directions
    python manage.py sync_odk --direction=push   # Push only
    python manage.py sync_odk --direction=pull   # Pull only
    python manage.py sync_odk --program=5        # Single program
    python manage.py sync_odk --dry-run          # Preview without changes
"""

import logging
import os
from datetime import date, datetime

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Sync data between KoNote and ODK Central"

    @staticmethod
    def _get_sync_user():
        """Get or create a system user for ODK sync imports."""
        from apps.auth_app.models import User
        user, _ = User.objects.get_or_create(
            username="odk_sync",
            defaults={"is_active": False, "is_admin": False},
        )
        return user

    def add_arguments(self, parser):
        parser.add_argument(
            "--direction",
            choices=["push", "pull", "both"],
            default="both",
            help="Sync direction: push (KoNote→ODK), pull (ODK→KoNote), or both.",
        )
        parser.add_argument(
            "--program",
            type=int,
            help="Sync only this program ID. Default: all enabled programs.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview what would be synced without making changes.",
        )

    def handle(self, *args, **options):
        from apps.field_collection.models import ProgramFieldConfig, SyncRun
        from apps.field_collection.odk_client import ODKCentralClient, ODKCentralError

        direction = options["direction"]
        program_id = options.get("program")
        dry_run = options["dry_run"]

        # Read ODK Central credentials from environment at sync time
        odk_url = os.environ.get("ODK_CENTRAL_URL", "")
        odk_email = os.environ.get("ODK_CENTRAL_EMAIL", "")
        odk_password = os.environ.get("ODK_CENTRAL_PASSWORD", "")

        if not all([odk_url, odk_email, odk_password]):
            raise CommandError(
                "ODK Central is not configured. Set ODK_CENTRAL_URL, "
                "ODK_CENTRAL_EMAIL, and ODK_CENTRAL_PASSWORD in your environment."
            )

        # Get enabled program configs
        configs = ProgramFieldConfig.objects.filter(enabled=True).select_related("program")
        if program_id:
            configs = configs.filter(program_id=program_id)

        if not configs.exists():
            self.stdout.write(self.style.WARNING("No programs have field collection enabled."))
            return

        # Create sync run record
        sync_run = SyncRun(
            direction=direction,
            programs_synced=",".join(str(c.program_id) for c in configs),
        )
        if not dry_run:
            sync_run.save()

        if dry_run:
            self.stdout.write(self.style.NOTICE("=== DRY RUN — no changes will be made ===\n"))

        try:
            client = ODKCentralClient(odk_url, odk_email, odk_password)
            # Test connection
            client.list_projects()
            self.stdout.write(f"Connected to ODK Central at {odk_url}")
        except ODKCentralError as e:
            msg = f"Cannot connect to ODK Central: {e}"
            self.stderr.write(self.style.ERROR(msg))
            if not dry_run:
                sync_run.status = "failed"
                sync_run.error_details = msg
                sync_run.finished_at = timezone.now()
                sync_run.save()
            return

        errors = []

        for config in configs:
            program = config.program
            self.stdout.write(f"\n--- {program.name} (tier: {config.data_tier}) ---")

            try:
                # Ensure ODK project exists
                if not dry_run:
                    config = self._ensure_odk_project(client, config)

                if direction in ("push", "both"):
                    self._push_entities(client, config, sync_run, dry_run)

                if direction in ("pull", "both"):
                    self._pull_submissions(client, config, sync_run, dry_run)

            except ODKCentralError as e:
                msg = f"Error syncing {program.name}: {e}"
                errors.append(msg)
                self.stderr.write(self.style.ERROR(msg))
                logger.error(msg, exc_info=True)

        # Finalise sync run
        if not dry_run:
            sync_run.error_count = len(errors)
            sync_run.error_details = "\n".join(errors)
            sync_run.status = "failed" if len(errors) == len(configs) else (
                "partial" if errors else "success"
            )
            sync_run.finished_at = timezone.now()
            sync_run.save()

        # Summary
        self.stdout.write("")
        self._print_summary(sync_run, dry_run)

    def _ensure_odk_project(self, client, config):
        """Create or verify the ODK Central project for this program."""
        from apps.field_collection.odk_client import ODKCentralError

        if config.odk_project_id:
            try:
                client.get_project(config.odk_project_id)
                return config
            except ODKCentralError:
                self.stdout.write(
                    self.style.WARNING(f"  ODK project {config.odk_project_id} not found, creating new one...")
                )

        # Create new project with a generic name (never reveals program type)
        project = client.create_project(f"Field Collection — {config.program.name}")
        config.odk_project_id = project["id"]
        config.save(update_fields=["odk_project_id"])
        self.stdout.write(self.style.SUCCESS(f"  Created ODK project #{project['id']}"))
        return config

    def _push_entities(self, client, config, sync_run, dry_run):
        """Push participant/group Entity lists to ODK Central."""
        from apps.clients.models import ClientFile
        from apps.programs.models import UserProgramRole

        program = config.program
        project_id = config.odk_project_id
        tier_fields = config.entity_fields_for_tier

        # --- Push participants ---
        if "visit_note" in config.enabled_forms or "circle_observation" in config.enabled_forms:
            participants = self._get_participants_for_push(config)
            self.stdout.write(f"  Participants to push: {len(participants)} (tier: {config.data_tier})")

            if not dry_run and participants:
                self._sync_participant_entities(client, project_id, participants, tier_fields)
                sync_run.participants_pushed += len(participants)

        # --- Push groups ---
        if "session_attendance" in config.enabled_forms:
            groups = self._get_groups_for_push(program)
            self.stdout.write(f"  Groups to push: {len(groups)}")

            if not dry_run and groups:
                self._sync_group_entities(client, project_id, groups, tier_fields)
                sync_run.groups_pushed += len(groups)

        # --- Sync app users ---
        staff_roles = UserProgramRole.objects.filter(
            program=program,
            status="active",
            role__in=["staff", "program_manager"],
        ).select_related("user")
        self.stdout.write(f"  Staff to sync as app users: {staff_roles.count()}")

        if not dry_run:
            self._sync_app_users(client, project_id, config, staff_roles)
            sync_run.app_users_synced += staff_roles.count()

    def _get_participants_for_push(self, config):
        """Get participant data to push, filtered by tier and scope."""
        from apps.clients.models import ClientFile

        # Get participants enrolled in this program
        participants = ClientFile.objects.filter(
            enrolments__program=config.program,
            enrolments__status="active",
            status="active",
        ).distinct()

        result = []
        for client in participants:
            entity = {"konote_id": str(client.pk)}

            if config.data_tier in ("standard", "field", "field_contact"):
                entity["first_name"] = client.first_name or ""

            if config.data_tier in ("field", "field_contact"):
                last = client.last_name or ""
                entity["last_initial"] = last[0].upper() if last else ""

            if config.data_tier == "field_contact":
                entity["phone"] = client.phone or ""

            result.append({
                "label": entity.get("first_name", f"ID-{client.pk}"),
                "data": entity,
                "uuid": f"konote-participant-{client.pk}",
            })
        return result

    def _get_groups_for_push(self, program):
        """Get groups and their members for this program."""
        from apps.groups.models import Group

        groups = Group.objects.filter(
            program=program,
            status="active",
            group_type="group",
        ).prefetch_related("memberships__client_file")

        result = []
        for group in groups:
            members = []
            for m in group.memberships.filter(status="active"):
                member_data = {"konote_membership_id": str(m.pk)}
                if m.client_file:
                    member_data["konote_id"] = str(m.client_file.pk)
                    member_data["name"] = m.client_file.first_name or m.display_name
                else:
                    member_data["name"] = m.member_name or "Unknown"
                members.append(member_data)

            result.append({
                "group_id": group.pk,
                "name": group.name,
                "members": members,
            })
        return result

    def _sync_participant_entities(self, client, project_id, participants, tier_fields):
        """Create or update participant entities in ODK Central."""
        dataset_name = "Participants"

        # Check if entity list exists
        datasets = client.list_entity_lists(project_id)
        dataset_names = [d["name"] for d in datasets]

        if dataset_name not in dataset_names:
            # Build property list from tier
            properties = [{"name": "konote_id"}]
            for field in tier_fields:
                if field != "id":
                    properties.append({"name": field})
            client.create_entity_list(project_id, dataset_name, properties)
            self.stdout.write(self.style.SUCCESS(f"  Created entity list: {dataset_name}"))

        # Get existing entities to determine create vs update
        existing = client.list_entities(project_id, dataset_name)
        existing_uuids = {e["uuid"] for e in existing}

        created, updated = 0, 0
        for p in participants:
            if p["uuid"] in existing_uuids:
                client.update_entity(project_id, dataset_name, p["uuid"], p["data"], label=p["label"])
                updated += 1
            else:
                client.create_entity(project_id, dataset_name, p["label"], p["data"], uuid=p["uuid"])
                created += 1

        self.stdout.write(f"  Participants: {created} created, {updated} updated")

    def _sync_group_entities(self, client, project_id, groups, tier_fields):
        """Create or update group entities in ODK Central."""
        from apps.field_collection.odk_client import ODKCentralError

        dataset_name = "Groups"

        datasets = client.list_entity_lists(project_id)
        if dataset_name not in [d["name"] for d in datasets]:
            client.create_entity_list(
                project_id, dataset_name,
                properties=[{"name": "konote_group_id"}, {"name": "member_count"}],
            )
            self.stdout.write(self.style.SUCCESS(f"  Created entity list: {dataset_name}"))

        for group_data in groups:
            uuid = f"konote-group-{group_data['group_id']}"
            entity_data = {
                "konote_group_id": str(group_data["group_id"]),
                "member_count": str(len(group_data["members"])),
            }
            try:
                client.create_entity(
                    project_id, dataset_name,
                    label=group_data["name"],
                    data=entity_data,
                    uuid=uuid,
                )
            except ODKCentralError:
                # Entity may already exist — try update
                client.update_entity(
                    project_id, dataset_name, uuid,
                    data=entity_data,
                    label=group_data["name"],
                )

    def _sync_app_users(self, client, project_id, config, staff_roles):
        """Create ODK app users from KoNote staff roles."""
        from apps.field_collection.odk_client import ODKCentralError

        existing_users = client.list_app_users(project_id)
        existing_names = {u["displayName"] for u in existing_users}

        for role in staff_roles:
            display_name = f"{role.user.get_full_name()} (KN-{role.user.pk})"
            if display_name not in existing_names:
                app_user = client.create_app_user(project_id, display_name)
                # Assign to all enabled forms
                for form_id in config.enabled_forms:
                    try:
                        client.assign_app_user_to_form(project_id, form_id, app_user["id"])
                    except ODKCentralError as e:
                        logger.warning("Could not assign app user to form %s: %s", form_id, e)

    def _pull_submissions(self, client, config, sync_run, dry_run):
        """Pull new submissions from ODK Central and create KoNote records."""
        from apps.field_collection.models import SyncRun as SyncRunModel
        from apps.field_collection.odk_client import ODKCentralError

        project_id = config.odk_project_id
        if not project_id:
            self.stdout.write("  No ODK project ID — skipping pull")
            return

        # Determine "since" filter from last successful sync
        last_sync = SyncRunModel.objects.filter(
            status__in=["success", "partial"],
            direction__in=["pull", "both"],
        ).order_by("-started_at").first()

        since = last_sync.started_at.isoformat() if last_sync else None

        # Pull attendance submissions
        if "session_attendance" in config.enabled_forms:
            try:
                submissions = client.get_submissions(project_id, "session_attendance", since=since)
                self.stdout.write(f"  Attendance submissions to process: {len(submissions)}")
                if not dry_run:
                    created, skipped = self._import_attendance(submissions, config)
                    sync_run.attendance_records_created += created
                    sync_run.submissions_skipped += skipped
            except ODKCentralError as e:
                self.stderr.write(f"  Error pulling attendance: {e}")
                logger.error("Error pulling attendance for %s: %s", config.program.name, e)
                sync_run.error_count += 1

        # Pull visit note submissions
        if "visit_note" in config.enabled_forms:
            try:
                submissions = client.get_submissions(project_id, "visit_note", since=since)
                self.stdout.write(f"  Visit note submissions to process: {len(submissions)}")
                if not dry_run:
                    created, skipped = self._import_visit_notes(submissions, config)
                    sync_run.notes_created += created
                    sync_run.submissions_skipped += skipped
            except ODKCentralError as e:
                self.stderr.write(f"  Error pulling visit notes: {e}")
                logger.error("Error pulling visit notes for %s: %s", config.program.name, e)
                sync_run.error_count += 1

    def _import_attendance(self, submissions, config):
        """Import attendance submissions as GroupSession + GroupSessionAttendance records."""
        from apps.groups.models import Group, GroupMembership, GroupSession, GroupSessionAttendance

        created = 0
        skipped = 0

        for sub in submissions:
            try:
                group_id = int(sub.get("group_konote_id", 0))
                session_date_str = sub.get("session_date", "")
                if not group_id or not session_date_str:
                    skipped += 1
                    continue

                session_date = date.fromisoformat(session_date_str)

                # Dedup: skip if session already exists for this group + date
                if GroupSession.objects.filter(group_id=group_id, session_date=session_date).exists():
                    self.stdout.write(f"    Skipped: session already exists for group {group_id} on {session_date}")
                    skipped += 1
                    continue

                # Create session
                session = GroupSession.objects.create(
                    group_id=group_id,
                    session_date=session_date,
                )
                session_notes = sub.get("session_notes", "")
                if session_notes:
                    session.notes = session_notes
                    session.save()

                # Create attendance records
                members_present = sub.get("members_present", "").split()
                all_memberships = GroupMembership.objects.filter(
                    group_id=group_id, status="active"
                )
                for membership in all_memberships:
                    present = str(membership.pk) in members_present
                    GroupSessionAttendance.objects.create(
                        group_session=session,
                        membership=membership,
                        present=present,
                    )

                created += 1
                self.stdout.write(f"    Created session for group {group_id} on {session_date}")

            except Exception as e:
                self.stderr.write(f"    Error importing attendance: {e}")
                logger.error("Error importing attendance submission: %s", e, exc_info=True)
                skipped += 1

        return created, skipped

    def _import_visit_notes(self, submissions, config):
        """Import visit note submissions as ProgressNote records."""
        from apps.clients.models import ClientFile
        from apps.notes.models import ProgressNote

        created = 0
        skipped = 0

        for sub in submissions:
            try:
                participant_id = int(sub.get("participant_konote_id", 0))
                if not participant_id:
                    skipped += 1
                    continue

                # Verify participant exists
                if not ClientFile.objects.filter(pk=participant_id).exists():
                    self.stderr.write(f"    Unknown participant ID: {participant_id}")
                    skipped += 1
                    continue

                visit_date_str = sub.get("visit_date", "")
                visit_date = date.fromisoformat(visit_date_str) if visit_date_str else None

                observations = sub.get("observations", "")
                if not observations:
                    skipped += 1
                    continue

                # Map interaction type from ODK to KoNote
                visit_type_map = {
                    "home_visit": "home_visit",
                    "community": "other",
                    "phone": "phone",
                    "virtual": "other",
                }
                interaction_type = visit_type_map.get(
                    sub.get("visit_type", ""), "home_visit"
                )

                note = ProgressNote(
                    client_file_id=participant_id,
                    note_type="quick",
                    interaction_type=interaction_type,
                    author=self._get_sync_user(),
                    author_program=config.program,
                )
                note.notes_text = observations

                if visit_date:
                    note.backdate = timezone.make_aware(
                        datetime.combine(visit_date, datetime.min.time())
                    )

                # Engagement observation (scales match between ODK and KoNote)
                engagement = sub.get("engagement", "")
                if engagement and hasattr(note, "engagement_observation"):
                    note.engagement_observation = engagement

                # Alliance rating
                alliance = sub.get("alliance_rating", "")
                if alliance and hasattr(note, "alliance_rating"):
                    try:
                        note.alliance_rating = int(alliance)
                    except (ValueError, TypeError):
                        pass

                note.save()
                created += 1

            except Exception as e:
                self.stderr.write(f"    Error importing visit note: {e}")
                logger.error("Error importing visit note: %s", e, exc_info=True)
                skipped += 1

        return created, skipped

    def _print_summary(self, sync_run, dry_run):
        """Print a summary of the sync results."""
        prefix = "[DRY RUN] " if dry_run else ""
        self.stdout.write(self.style.SUCCESS(f"\n{prefix}Sync Summary"))
        self.stdout.write(f"  Direction: {sync_run.direction}")
        self.stdout.write(f"  Programs: {sync_run.programs_synced}")
        self.stdout.write(f"  Participants pushed: {sync_run.participants_pushed}")
        self.stdout.write(f"  Groups pushed: {sync_run.groups_pushed}")
        self.stdout.write(f"  App users synced: {sync_run.app_users_synced}")
        self.stdout.write(f"  Attendance records created: {sync_run.attendance_records_created}")
        self.stdout.write(f"  Notes created: {sync_run.notes_created}")
        self.stdout.write(f"  Submissions skipped: {sync_run.submissions_skipped}")
        if sync_run.error_count:
            self.stdout.write(self.style.ERROR(f"  Errors: {sync_run.error_count}"))
