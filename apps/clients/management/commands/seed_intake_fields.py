"""
Seed default intake custom fields for Canadian nonprofit community services.

These fields represent what most Canadian nonprofits would expect on a client
intake form, based on:
- PIPEDA privacy requirements (consent, purpose limitation)
- AODA accessibility requirements (accommodation needs)
- Common funder demographics (community foundations, Trillium, municipal funders)
- Practical service delivery needs (contact, emergency, baseline status)

Field groups are organized for two use cases:
1. Clinical/counselling services (groups 10-70) — active by default
2. Youth/recreation programs (groups 80-90) — archived by default (reactivate if needed)

All demographic fields are optional with "Prefer not to answer" options.
Agencies can customize, archive, or add fields after seeding.

Run with: python manage.py seed_intake_fields
"""
from django.core.management.base import BaseCommand

from apps.clients.models import CustomFieldDefinition, CustomFieldGroup


# Field groups and their fields
# Format: (group_title, sort_order, fields_list)
# Each field: (name, input_type, is_required, is_sensitive, front_desk_access, placeholder, options)
#             or (name, input_type, is_required, is_sensitive, front_desk_access, placeholder, options, validation_type)
# validation_type is optional — if omitted, auto-detection in model.save() handles it.
#
# front_desk_access values (controls front desk visibility):
#   "edit" — front desk can view and edit (contact info, emergency, admin fields)
#   "view" — front desk can view but not edit (clinical context)
#   "none" — hidden from front desk staff (demographics, baseline, consent)
#
# Workflow guidance (from expert panel):
# - Stage 1 (first contact): Contact + Emergency + Referral Source — anyone can enter
# - Stage 2 (intake appointment): Reason for services + Consent — staff with client
# - Stage 3 (as trust builds): Demographics + Baseline — staff with client, optional
#
# For self-service registration (youth/recreation):
# - Participant or parent fills out: Contact, Emergency, Guardian, Health, Consents
# - Staff reviews and approves submission

# Field groups that should be archived by default (youth/recreation programs)
# Agencies that need these can reactivate them in the admin interface.
ARCHIVED_BY_DEFAULT = {
    "Parent/Guardian Information",
    "Health & Safety",
    "Program Consents",
}

INTAKE_FIELD_GROUPS = [
    # =========================================================================
    # CORE INTAKE FIELDS (Clinical and General Services)
    # =========================================================================

    # -------------------------------------------------------------------------
    # Contact Information — FRONT DESK: EDIT
    # Stage 1: First contact (front desk, client online, or self-service)
    # -------------------------------------------------------------------------
    (
        "Contact Information",
        10,
        [
            ("Preferred Name", "text", False, False, "edit", "What name do you prefer to be called?", []),
            # Pronouns — per HL7 Personal Pronouns ValueSet v2.0.0 + common combinations
            # from Trevor Project 2024 National Survey. Agencies can customise options.
            ("Pronouns", "select_other", False, True, "view", "", [
                "He/him",
                "He/they",
                "She/her",
                "She/they",
                "They/them",
                "Prefer not to answer",
            ]),
            ("Primary Phone", "text", True, True, "edit", "(416) 555-0123", [], "phone"),
            ("Secondary Phone", "text", False, True, "edit", "", [], "phone"),
            ("Email", "text", False, True, "edit", "email@example.com", []),
            ("Mailing Address", "textarea", False, True, "edit", "Street address, city", []),
            ("Postal Code", "text", False, False, "edit", "A1A 1A1", [], "postal_code"),
            ("Province or Territory", "select", False, False, "edit", "", [
                "Alberta",
                "British Columbia",
                "Manitoba",
                "New Brunswick",
                "Newfoundland and Labrador",
                "Northwest Territories",
                "Nova Scotia",
                "Nunavut",
                "Ontario",
                "Prince Edward Island",
                "Quebec",
                "Saskatchewan",
                "Yukon",
            ]),
            ("Preferred Contact Method", "select", False, False, "edit", "", [
                "Phone call",
                "Text message",
                "Email",
                "In person",
            ]),
            ("Best Time to Contact", "select", False, False, "edit", "", [
                "Morning (9am-12pm)",
                "Afternoon (12pm-5pm)",
                "Evening (5pm-8pm)",
                "Any time",
            ]),
            ("Preferred Language of Service", "select", False, False, "edit", "", [
                "English",
                "French",
                "Other",
            ]),
        ],
    ),
    # -------------------------------------------------------------------------
    # Emergency Contact — FRONT DESK: EDIT
    # Stage 1: First contact (critical for safety)
    # -------------------------------------------------------------------------
    (
        "Emergency Contact",
        20,
        [
            ("Emergency Contact Name", "text", True, True, "edit", "Full name", []),
            ("Emergency Contact Relationship", "select", False, False, "edit", "", [
                "Parent/Guardian",
                "Spouse/Partner",
                "Sibling",
                "Other family member",
                "Friend",
                "Case worker",
                "Other",
            ]),
            ("Emergency Contact Phone", "text", True, True, "edit", "(416) 555-0123", [], "phone"),
        ],
    ),
    # -------------------------------------------------------------------------
    # Referral & Service Information — PARTIAL ACCESS
    # Referral source/agency: front desk can edit (administrative)
    # Reason for services, barriers, goals: view only (clinical context)
    # -------------------------------------------------------------------------
    (
        "Referral & Service Information",
        30,
        [
            # Administrative fields — front desk can edit
            ("Referral Source", "select", False, False, "edit", "", [
                "Self-referral",
                "Family/Friend",
                "Community agency",
                "Hospital/Health provider",
                "School/Education",
                "Social services (OW/ODSP)",
                "Justice system",
                "Shelter/Housing provider",
                "Online search",
                "Other",
            ]),
            ("Referring Agency Name", "text", False, False, "edit", "If referred by an agency", []),
            # Clinical fields — front desk can view but not edit
            ("Primary Reason for Seeking Services", "textarea", False, False, "view", "What brings you to our program?", []),
            ("Barriers to Accessing Services", "select", False, False, "view", "", [
                "Transportation",
                "Childcare",
                "Work schedule",
                "Language",
                "Physical accessibility",
                "Technology access",
                "None identified",
                "Prefer not to answer",
            ]),
            ("Goals or Desired Outcomes", "textarea", False, False, "view", "What are you hoping to achieve?", []),
        ],
    ),
    # -------------------------------------------------------------------------
    # Accessibility & Accommodation (AODA) — FRONT DESK: EDIT
    # Stage 1: First contact (so staff can prepare accessible space)
    # -------------------------------------------------------------------------
    (
        "Accessibility & Accommodation",
        40,
        [
            ("Accommodation Needs", "textarea", False, False, "edit", "Any accommodations we should be aware of", []),
            ("Preferred Communication Format", "select", False, False, "edit", "", [
                "Standard print",
                "Large print",
                "Audio",
                "Electronic/Digital",
                "Sign language interpreter",
                "Other",
            ]),
        ],
    ),
    # -------------------------------------------------------------------------
    # Demographics (for equity reporting) — FRONT DESK: NONE
    # Stage 3: As trust builds (optional, staff explains equity purpose)
    # All fields optional with "Prefer not to answer"
    # -------------------------------------------------------------------------
    (
        "Demographics",
        50,
        [
            ("Gender Identity", "select_other", False, False, "none", "", [
                "Woman",
                "Man",
                "Non-binary",
                "Two-Spirit",
                "Gender diverse",
                "Prefer to self-describe",
                "Prefer not to answer",
            ]),
            ("Indigenous Identity", "select", False, False, "none", "", [
                "First Nations",
                "Métis",
                "Inuit",
                "Non-Indigenous",
                "Prefer not to answer",
            ]),
            ("Racial/Ethnic Background", "select", False, False, "none", "", [
                "Black",
                "East Asian",
                "South Asian",
                "Southeast Asian",
                "Middle Eastern/North African",
                "Latin American",
                "White",
                "Mixed/Multiple backgrounds",
                "Prefer to self-describe",
                "Prefer not to answer",
            ]),
            ("Immigration/Citizenship Status", "select", False, False, "none", "", [
                "Canadian citizen (born in Canada)",
                "Canadian citizen (naturalized)",
                "Permanent resident",
                "Refugee/Protected person",
                "Temporary resident (work/study permit)",
                "No status",
                "Prefer not to answer",
            ]),
            ("Primary Language Spoken at Home", "text", False, False, "none", "", []),
            ("Disability Status", "select", False, False, "none", "", [
                "Yes - physical",
                "Yes - sensory (vision, hearing)",
                "Yes - cognitive/developmental",
                "Yes - learning disability",
                "Yes - mental health condition",
                "Yes - chronic illness/pain",
                "Yes - multiple",
                "No",
                "Prefer not to answer",
            ]),
        ],
    ),
    # -------------------------------------------------------------------------
    # Baseline Status (for outcome measurement) — FRONT DESK: NONE
    # Stage 3: As trust builds (staff collects during early sessions)
    # -------------------------------------------------------------------------
    (
        "Baseline Status",
        60,
        [
            ("Employment Status", "select", False, False, "none", "", [
                "Employed full-time",
                "Employed part-time",
                "Self-employed",
                "Unemployed - looking for work",
                "Unemployed - not looking",
                "Student",
                "Retired",
                "Not currently able to work",
                "Prefer not to answer",
            ]),
            ("Highest Education Completed", "select", False, False, "none", "", [
                "Less than high school",
                "Some high school",
                "High school diploma/GED",
                "Some college/university",
                "Apprenticeship/Trades certificate",
                "College diploma/certificate",
                "Bachelor's degree",
                "Graduate degree",
                "Prefer not to answer",
            ]),
            ("Primary Income Source", "select", False, False, "none", "", [
                "Employment",
                "Ontario Works (OW)",
                "Ontario Disability Support Program (ODSP)",
                "Employment Insurance (EI)",
                "Canada Pension Plan (CPP)",
                "Old Age Security (OAS)",
                "Family/Partner support",
                "No income",
                "Other",
                "Prefer not to answer",
            ]),
            ("Household Income Range", "select", False, False, "none", "", [
                "Under $20,000",
                "$20,000 - $39,999",
                "$40,000 - $59,999",
                "$60,000 - $79,999",
                "$80,000 - $99,999",
                "$100,000 or more",
                "Don't know",
                "Prefer not to answer",
            ]),
            ("Housing Situation", "select", False, False, "none", "", [
                "Own home",
                "Rent - market rate",
                "Rent - subsidized housing",
                "Living with family/friends",
                "Rooming house",
                "Shelter/Transitional housing",
                "Experiencing homelessness/No fixed address",
                "Other",
                "Prefer not to answer",
            ]),
            ("Household Composition", "select", False, False, "none", "", [
                "Living alone",
                "With spouse/partner",
                "With spouse/partner and children",
                "Single parent with children",
                "With parents/family",
                "With roommates",
                "Group living/Shared housing",
                "Prefer not to answer",
            ]),
        ],
    ),
    # -------------------------------------------------------------------------
    # Consent & Permissions — FRONT DESK: NONE (requires explanation)
    # Stage 2: Intake appointment
    # -------------------------------------------------------------------------
    (
        "Consent & Permissions",
        70,
        [
            ("Information Sharing Consent", "select", False, False, "none", "", [
                "Yes - may share with partner agencies",
                "No - do not share",
                "Case-by-case basis",
            ]),
            ("Consent for Follow-up Contact", "select", False, False, "none", "", [
                "Yes - may contact for follow-up surveys",
                "No - do not contact after discharge",
            ]),
            ("Secondary Contact for Follow-up", "text", False, True, "none", "Name and phone if client unreachable", []),
        ],
    ),

    # =========================================================================
    # YOUTH/RECREATION PROGRAM FIELDS (Optional — archive if not needed)
    # For sports, after-school, camps, enrichment programs
    # Designed for self-service registration by parents/guardians
    # =========================================================================

    # -------------------------------------------------------------------------
    # Parent/Guardian Information — FRONT DESK: EDIT
    # For youth programs: primary contact is usually the parent, not the child
    # -------------------------------------------------------------------------
    (
        "Parent/Guardian Information",
        80,
        [
            ("Parent/Guardian Name", "text", False, True, "edit", "Full name of primary parent/guardian", []),
            ("Relationship to Participant", "select", False, False, "edit", "", [
                "Parent",
                "Mother",
                "Father",
                "Stepparent",
                "Grandparent",
                "Foster parent",
                "Kinship caregiver",
                "Legal guardian",
                "Other family member",
                "Other",
            ]),
            ("Parent/Guardian Phone", "text", False, True, "edit", "(416) 555-0123", [], "phone"),
            ("Parent/Guardian Email", "text", False, True, "edit", "email@example.com", []),
            ("Secondary Parent/Guardian Name", "text", False, True, "edit", "", []),
            ("Secondary Parent/Guardian Phone", "text", False, True, "edit", "", [], "phone"),
            ("Custody/Access Notes", "textarea", False, True, "view", "Any custody arrangements staff should know about", []),
        ],
    ),
    # -------------------------------------------------------------------------
    # Health & Safety — FRONT DESK: EDIT (for emergencies)
    # Medical info staff need to keep participants safe
    # -------------------------------------------------------------------------
    (
        "Health & Safety",
        85,
        [
            ("Allergies", "textarea", False, True, "edit", "Food, medication, environmental allergies", []),
            ("Medical Conditions", "textarea", False, True, "edit", "Conditions that may affect participation", []),
            ("Medications", "textarea", False, True, "view", "Current medications (staff use only)", []),
            ("Dietary Restrictions", "select", False, False, "edit", "", [
                "None",
                "Vegetarian",
                "Vegan",
                "Halal",
                "Kosher",
                "Gluten-free",
                "Nut-free environment required",
                "Other",
            ]),
            ("Health Card Number", "text", False, True, "view", "Ontario Health Card (for emergencies)", []),
            ("Family Doctor/Clinic", "text", False, True, "edit", "Name and phone number", []),
            ("Special Instructions", "textarea", False, False, "edit", "Anything else staff should know", []),
        ],
    ),
    # -------------------------------------------------------------------------
    # Program Consents — FRONT DESK: EDIT
    # Waivers and permissions for youth/recreation programs
    # -------------------------------------------------------------------------
    (
        "Program Consents",
        90,
        [
            ("Photo/Video Consent", "select", False, False, "edit", "", [
                "Yes - may use photos/videos for promotion",
                "Yes - internal use only (not social media)",
                "No - do not photograph or record",
            ]),
            ("Participation Waiver", "select", False, False, "edit", "", [
                "I acknowledge the risks and agree to participate",
                "Not yet agreed",
            ]),
            ("Pickup Authorization", "textarea", False, True, "edit", "Names of people authorized to pick up (besides parent/guardian)", []),
            ("Transportation Consent", "select", False, False, "edit", "", [
                "May travel independently (walk, bike, transit)",
                "Must be picked up by authorized person",
                "May travel in program vehicles",
            ]),
            ("Field Trip Consent", "select", False, False, "edit", "", [
                "Yes - may participate in off-site activities",
                "No - on-site activities only",
                "Contact me for each trip",
            ]),
            ("Sunscreen/Bug Spray Consent", "select", False, False, "edit", "", [
                "Yes - staff may apply provided products",
                "Will provide own products",
                "No - do not apply",
            ]),
        ],
    ),
]


class Command(BaseCommand):
    help = "Seed default intake custom fields for Canadian nonprofit community services."

    def handle(self, *args, **options):
        # No early-return guard — get_or_create handles idempotency.
        # A guard here caused a production outage when the DB had groups but
        # no field definitions. Every startup must ensure all fields exist.

        groups_created = 0
        fields_created = 0

        for group_title, group_sort_order, fields in INTAKE_FIELD_GROUPS:
            # Create or get the group
            # Youth/recreation groups are archived by default — agencies can reactivate if needed
            initial_status = "archived" if group_title in ARCHIVED_BY_DEFAULT else "active"
            group, was_group_created = CustomFieldGroup.objects.get_or_create(
                title=group_title,
                defaults={"sort_order": group_sort_order, "status": initial_status},
            )
            if was_group_created:
                groups_created += 1

            # Create fields within the group
            for field_idx, field_data in enumerate(fields):
                # Unpack with optional validation_type (8th element)
                name = field_data[0]
                input_type = field_data[1]
                is_required = field_data[2]
                is_sensitive = field_data[3]
                front_desk_access = field_data[4]
                placeholder = field_data[5]
                options = field_data[6]
                validation_type = field_data[7] if len(field_data) > 7 else "none"

                defaults = {
                    "input_type": input_type,
                    "is_required": is_required,
                    "is_sensitive": is_sensitive,
                    "front_desk_access": front_desk_access,
                    "placeholder": placeholder,
                    "options_json": options if options else [],
                    "sort_order": field_idx * 10,
                    "status": "active",
                }
                # Only set validation_type if explicitly specified,
                # otherwise let model.save() auto-detect it.
                if validation_type != "none":
                    defaults["validation_type"] = validation_type

                _, was_field_created = CustomFieldDefinition.objects.get_or_create(
                    group=group,
                    name=name,
                    defaults=defaults,
                )
                if was_field_created:
                    fields_created += 1

        # Fix stale data from earlier seeds
        fixups = 0

        # Preferred Name: remove "client" language
        fixups += CustomFieldDefinition.objects.filter(
            group__title="Contact Information",
            name="Preferred Name",
            placeholder="Name the client prefers to be called",
        ).update(placeholder="What name do you prefer to be called?")

        # Mailing Address: remove "postal code" (has its own field)
        fixups += CustomFieldDefinition.objects.filter(
            group__title="Contact Information",
            name="Mailing Address",
            placeholder="Street address, city, postal code",
        ).update(placeholder="Street address, city")

        # Remove "Prefer not to answer" from operational fields (not demographics)
        # These are service delivery fields where staff need an actual answer.
        operational_fields = [
            ("Contact Information", "Preferred Language of Service"),
            ("Contact Information", "Preferred Contact Method"),
            ("Contact Information", "Best Time to Contact"),
            ("Accessibility & Accommodation", "Preferred Communication Format"),
        ]
        for group_title, field_name in operational_fields:
            for field in CustomFieldDefinition.objects.filter(
                group__title=group_title, name=field_name,
            ):
                opts = field.options_json if isinstance(field.options_json, list) else []
                if "Prefer not to answer" in opts:
                    opts.remove("Prefer not to answer")
                    field.options_json = opts
                    field.save(update_fields=["options_json"])
                    fixups += 1

        # Inclusive language updates (2026-02-07 review)
        # These update option lists for fields that already exist with old values.
        OPTION_FIXUPS = [
            # Housing: person-first language
            ("Baseline Status", "Housing Situation",
             "Homeless/No fixed address", "Experiencing homelessness/No fixed address"),
            # Employment: less defining
            ("Baseline Status", "Employment Status",
             "Unable to work", "Not currently able to work"),
            # Disability: clearer label
            ("Demographics", "Disability Status",
             "Yes - mental health", "Yes - mental health condition"),
            # Racial/ethnic: include North Africa
            ("Demographics", "Racial/Ethnic Background",
             "Middle Eastern", "Middle Eastern/North African"),
            # Income: split old top bracket
            ("Baseline Status", "Household Income Range",
             "$80,000 or more", "$80,000 - $99,999"),
        ]
        for group_title, field_name, old_val, new_val in OPTION_FIXUPS:
            for field in CustomFieldDefinition.objects.filter(
                group__title=group_title, name=field_name,
            ):
                opts = field.options_json if isinstance(field.options_json, list) else []
                if old_val in opts:
                    opts[opts.index(old_val)] = new_val
                    field.options_json = opts
                    field.save(update_fields=["options_json"])
                    fixups += 1

        # Income: add $100,000+ bracket if missing (after splitting $80k+)
        for field in CustomFieldDefinition.objects.filter(
            group__title="Baseline Status", name="Household Income Range",
        ):
            opts = field.options_json if isinstance(field.options_json, list) else []
            if "$100,000 or more" not in opts:
                # Insert before "Don't know" if present, otherwise append
                insert_pos = opts.index("Don't know") if "Don't know" in opts else len(opts)
                opts.insert(insert_pos, "$100,000 or more")
                field.options_json = opts
                field.save(update_fields=["options_json"])
                fixups += 1

        # Disability: add new categories if missing
        for field in CustomFieldDefinition.objects.filter(
            group__title="Demographics", name="Disability Status",
        ):
            opts = field.options_json if isinstance(field.options_json, list) else []
            new_opts = ["Yes - learning disability", "Yes - chronic illness/pain"]
            for opt in new_opts:
                if opt not in opts:
                    # Insert before "Yes - multiple"
                    insert_pos = opts.index("Yes - multiple") if "Yes - multiple" in opts else len(opts)
                    opts.insert(insert_pos, opt)
                    fixups += 1
            field.options_json = opts
            field.save(update_fields=["options_json"])

        # Education: add trades/apprenticeship if missing
        for field in CustomFieldDefinition.objects.filter(
            group__title="Baseline Status", name="Highest Education Completed",
        ):
            opts = field.options_json if isinstance(field.options_json, list) else []
            if "Apprenticeship/Trades certificate" not in opts:
                insert_pos = opts.index("College diploma/certificate") if "College diploma/certificate" in opts else len(opts)
                opts.insert(insert_pos, "Apprenticeship/Trades certificate")
                field.options_json = opts
                field.save(update_fields=["options_json"])
                fixups += 1

        # Parent/Guardian: add inclusive options if missing
        for field in CustomFieldDefinition.objects.filter(
            group__title="Parent/Guardian Information", name="Relationship to Participant",
        ):
            opts = field.options_json if isinstance(field.options_json, list) else []
            if "Parent" not in opts:
                opts.insert(0, "Parent")
                fixups += 1
            if "Kinship caregiver" not in opts:
                insert_pos = opts.index("Legal guardian") if "Legal guardian" in opts else len(opts)
                opts.insert(insert_pos, "Kinship caregiver")
                fixups += 1
            field.options_json = opts
            field.save(update_fields=["options_json"])

        # Gender Identity: change field type to select_other so self-describe has a text box
        fixups += CustomFieldDefinition.objects.filter(
            group__title="Demographics",
            name="Gender Identity",
            input_type="select",
        ).update(input_type="select_other")

        if fixups:
            self.stdout.write(f"  Updated {fixups} stale field(s) from earlier seeds.")

        self.stdout.write(
            self.style.SUCCESS(
                f"  Intake fields: {groups_created} groups and {fields_created} fields created."
            )
        )
        self.stdout.write("  Note: Youth/recreation field groups (Parent/Guardian, Health & Safety, Program Consents)")
        self.stdout.write("        are archived by default. Reactivate them in Admin > Custom Fields if needed.")
