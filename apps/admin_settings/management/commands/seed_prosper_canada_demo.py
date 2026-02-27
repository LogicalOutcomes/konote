"""
Seed demo data for a Prosper Canada financial coaching instance.

Creates a complete demonstration dataset with:
- 5 staff accounts (receptionist, coaches, program manager, executive)
- 1 program: Prosper Canada Financial Coaching
- 12 participants (PC-001 through PC-012) with full intake profiles
- 55 custom fields across 9 groups (demographics, immigration, household, etc.)
- Surveys with pre/post financial capability responses
- Plans with financial coaching goals and targets
- Progress notes with metric recordings
- Metric trends showing realistic coaching outcomes

All data reflects realistic Canadian financial empowerment coaching scenarios
including diverse demographics, immigration backgrounds, and financial situations.

Run with:  python manage.py seed_prosper_canada_demo
Reset:     python manage.py seed_prosper_canada_demo --reset

Idempotent: safe to run multiple times (uses get_or_create throughout).
"""

import os
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.clients.models import (
    ClientDetailValue,
    ClientFile,
    ClientProgramEnrolment,
    CustomFieldDefinition,
    CustomFieldGroup,
)
from apps.notes.models import (
    MetricValue,
    ProgressNote,
    ProgressNoteTarget,
    ProgressNoteTemplate,
    ProgressNoteTemplateSection,
    SuggestionLink,
    SuggestionTheme,
)
from apps.plans.models import MetricDefinition, PlanSection, PlanTarget, PlanTargetMetric
from apps.programs.models import Program, UserProgramRole
from apps.surveys.models import (
    Survey,
    SurveyAnswer,
    SurveyQuestion,
    SurveyResponse,
    SurveySection,
)

User = get_user_model()


# ---------------------------------------------------------------------------
# Staff accounts
# ---------------------------------------------------------------------------

STAFF = [
    {
        "username": "fatima@demo.konote.ca",
        "display_name": "Fatima Front Desk",
        "role": "receptionist",
        "is_admin": False,
        "preferred_language": "en",
    },
    {
        "username": "marcus@demo.konote.ca",
        "display_name": "Marcus Worker",
        "role": "staff",
        "is_admin": False,
        "preferred_language": "en",
    },
    {
        "username": "aminata@demo.konote.ca",
        "display_name": "Aminata Worker",
        "role": "staff",
        "is_admin": False,
        "preferred_language": "fr",
    },
    {
        "username": "sara@demo.konote.ca",
        "display_name": "Sara Manager",
        "role": "program_manager",
        "is_admin": True,
        "preferred_language": "en",
    },
    {
        "username": "david@demo.konote.ca",
        "display_name": "David Executive",
        "role": "executive",
        "is_admin": False,
        "preferred_language": "en",
    },
]

STAFF_USERNAMES = [s["username"] for s in STAFF]


# ---------------------------------------------------------------------------
# Program-specific participant suggestions for financial coaching
# Maps record_id -> list of (note_index, suggestion_text, priority)
# note_index is 0-based within that participant's note list
# ---------------------------------------------------------------------------

PARTICIPANT_SUGGESTIONS = {
    "PC-001": [
        (1, "It would help to have budget worksheets available in Arabic so I "
            "can work on them at home more easily.", "worth_exploring"),
        (3, "Group sessions with other newcomer women could help us share "
            "tips and feel less alone in learning about finances.", "important"),
    ],
    "PC-002": [
        (1, "Des horaires de rendez-vous en soiree seraient utiles car mon "
            "fils a besoin de moi apres l'ecole pour le transport.", "worth_exploring"),
        (3, "Un atelier sur la gestion des dettes serait tres utile pour "
            "les gens dans ma situation.", "important"),
    ],
    "PC-003": [
        (2, "An online portal where I can track my credit score progress "
            "between sessions would be really motivating.", "noted"),
        (3, "A workshop on Canadian workplace benefits and RRSP matching "
            "would help newcomers like me make better decisions.", "important"),
    ],
    "PC-004": [
        (1, "Information sessions about trade certification pathways in "
            "different languages would help newcomers navigate the process.", "worth_exploring"),
        (2, "A mentorship program pairing newcomers with established "
            "tradespeople in Canada would be incredibly helpful.", "important"),
    ],
    "PC-005": [
        (1, "Materials in simplified Chinese would help me understand "
            "without always relying on my daughter to translate.", "important"),
    ],
    "PC-006": [
        (1, "Childcare during coaching sessions would make it much easier "
            "to attend and focus on the conversation.", "urgent"),
        (2, "A guide about financial safety planning for women leaving "
            "abusive situations would help people like me feel prepared.", "important"),
    ],
    "PC-007": [
        (1, "Evening or Saturday appointments would help since I work "
            "during the day and cannot easily take time off.", "worth_exploring"),
    ],
    "PC-008": [
        (2, "A short guide comparing debt repayment strategies like "
            "snowball vs avalanche would help me choose the best approach.", "noted"),
    ],
    "PC-009": [
        (1, "Having a Tagalog-speaking coach or interpreter available "
            "would make sessions more comfortable for participants like me.", "worth_exploring"),
    ],
    "PC-010": [
        (2, "A checklist of all the benefits and credits available to "
            "families with children would be very useful to have.", "noted"),
    ],
}

# ---------------------------------------------------------------------------
# Suggestion themes for the Prosper Canada financial coaching program
# Each theme: (name, description, keywords, priority)
# Keywords are used for matching against suggestion text — no blind fallback.
# ---------------------------------------------------------------------------

SUGGESTION_THEMES = [
    (
        "Multilingual resources and interpretation",
        "Participants request coaching materials and support in languages "
        "other than English and French — Arabic, Chinese, Tagalog, etc.",
        "arabic,chinese,tagalog,language,translate,interpretation,interpreter,"
        "multilingual,simplified chinese,materials in",
        "important",
    ),
    (
        "Evening and weekend appointment availability",
        "Several participants have requested coaching sessions outside of "
        "standard business hours to accommodate work and family schedules.",
        "evening,saturday,weekend,soiree,hours,time off,horaires,appointment",
        "worth_exploring",
    ),
    (
        "Childcare during coaching sessions",
        "Parents — especially single mothers — report difficulty attending "
        "sessions due to lack of childcare.",
        "childcare,child care,children,kids,daycare",
        "urgent",
    ),
    (
        "Group workshops and peer learning",
        "Participants express interest in learning alongside peers in "
        "similar financial situations — debt management, newcomer finances, etc.",
        "group,workshop,atelier,peer,together,share tips,mentorship,pairing",
        "important",
    ),
    (
        "Digital tools for tracking progress",
        "Participants want online or app-based tools to monitor their "
        "financial progress between coaching sessions.",
        "online,portal,app,track,digital,progress,website",
        "noted",
    ),
    (
        "Financial safety planning resources",
        "Resources specifically designed for participants leaving abusive "
        "situations — financial safety plans, rights information.",
        "safety,abusive,abuse,leaving,women,financial safety,prepared",
        "important",
    ),
    (
        "Trade certification and career pathway guidance",
        "Newcomers with international credentials need clearer guidance on "
        "Canadian certification and bridging pathways.",
        "trade,certification,credential,bridging,trades,career,pathway",
        "worth_exploring",
    ),
    (
        "Debt management education",
        "Participants request structured resources comparing debt repayment "
        "strategies and negotiation approaches.",
        "debt,repayment,snowball,avalanche,consolidation,gestion des dettes",
        "noted",
    ),
    (
        "Benefits and credits awareness",
        "Participants want comprehensive information about government "
        "benefits and tax credits available to them.",
        "benefits,credits,checklist,CCB,GST,trillium,credits available",
        "noted",
    ),
]


# ---------------------------------------------------------------------------
# Participants — 12 financial coaching clients
# ---------------------------------------------------------------------------

PARTICIPANTS = [
    {
        "record_id": "PC-001",
        "first_name": "Amira",
        "last_name": "Al-Rashid",
        "coach": "marcus@demo.konote.ca",
        "intake_date": date(2025, 9, 15),
    },
    {
        "record_id": "PC-002",
        "first_name": "Jean-Pierre",
        "last_name": "Bouchard",
        "coach": "aminata@demo.konote.ca",
        "intake_date": date(2025, 9, 22),
    },
    {
        "record_id": "PC-003",
        "first_name": "Priya",
        "last_name": "Sharma",
        "coach": "marcus@demo.konote.ca",
        "intake_date": date(2025, 10, 1),
    },
    {
        "record_id": "PC-004",
        "first_name": "Kwame",
        "last_name": "Asante",
        "coach": "aminata@demo.konote.ca",
        "intake_date": date(2025, 10, 10),
    },
    {
        "record_id": "PC-005",
        "first_name": "Lin",
        "last_name": "Wei",
        "coach": "marcus@demo.konote.ca",
        "intake_date": date(2025, 10, 20),
    },
    {
        "record_id": "PC-006",
        "first_name": "Sofia",
        "last_name": "Rodriguez",
        "coach": "aminata@demo.konote.ca",
        "intake_date": date(2025, 11, 1),
    },
    {
        "record_id": "PC-007",
        "first_name": "Tyler",
        "last_name": "Whiteduck",
        "coach": "marcus@demo.konote.ca",
        "intake_date": date(2025, 11, 10),
    },
    {
        "record_id": "PC-008",
        "first_name": "Olga",
        "last_name": "Petrov",
        "coach": "aminata@demo.konote.ca",
        "intake_date": date(2025, 11, 15),
    },
    {
        "record_id": "PC-009",
        "first_name": "Daniel",
        "last_name": "Thompson",
        "coach": "marcus@demo.konote.ca",
        "intake_date": date(2025, 12, 1),
    },
    {
        "record_id": "PC-010",
        "first_name": "Hana",
        "last_name": "Yilmaz",
        "coach": "aminata@demo.konote.ca",
        "intake_date": date(2025, 12, 10),
    },
    {
        "record_id": "PC-011",
        "first_name": "James",
        "last_name": "Osei",
        "coach": "marcus@demo.konote.ca",
        "intake_date": date(2026, 1, 5),
    },
    {
        "record_id": "PC-012",
        "first_name": "Marie-Claire",
        "last_name": "Dubois",
        "coach": "aminata@demo.konote.ca",
        "intake_date": date(2026, 1, 15),
    },
]


# ---------------------------------------------------------------------------
# Custom field definitions — 9 groups, ~55 fields
# ---------------------------------------------------------------------------

CUSTOM_FIELD_GROUPS = [
    {
        "title": "Demographics",
        "sort_order": 1,
        "fields": [
            {"name": "Preferred Name", "input_type": "text", "sort_order": 1},
            {
                "name": "Pronouns",
                "input_type": "select_other",
                "sort_order": 2,
                "options_json": ["She/Her", "He/Him", "They/Them", "Ze/Zir"],
            },
            {
                "name": "Gender Identity",
                "input_type": "select_other",
                "sort_order": 3,
                "options_json": ["Woman", "Man", "Non-binary", "Two-Spirit", "Prefer not to say"],
            },
            {"name": "Date of Birth", "input_type": "date", "sort_order": 4, "is_sensitive": True},
            {
                "name": "Marital Status",
                "input_type": "select",
                "sort_order": 5,
                "options_json": [
                    "Single", "Married", "Common-law", "Separated",
                    "Divorced", "Widowed", "Prefer not to say",
                ],
            },
            {
                "name": "Indigenous Identity",
                "input_type": "select",
                "sort_order": 6,
                "options_json": [
                    "First Nations", "Metis", "Inuit",
                    "Non-Indigenous", "Prefer not to say",
                ],
            },
            {
                "name": "Racial Identity",
                "input_type": "select_other",
                "sort_order": 7,
                "options_json": [
                    "Arab", "Black", "Chinese", "Filipino", "Japanese",
                    "Korean", "Latin American", "South Asian", "Southeast Asian",
                    "West Asian", "White", "Prefer not to say",
                ],
            },
            {"name": "Ethnicity", "input_type": "text", "sort_order": 8},
            {
                "name": "Disability Status",
                "input_type": "select",
                "sort_order": 9,
                "options_json": [
                    "No disability", "Physical disability",
                    "Mental health disability", "Learning disability",
                    "Sensory disability", "Multiple disabilities",
                    "Prefer not to say",
                ],
            },
            {
                "name": "Education Level",
                "input_type": "select",
                "sort_order": 10,
                "options_json": [
                    "No formal education", "Some high school", "High school diploma/GED",
                    "Some college/CEGEP", "College diploma/Certificate",
                    "Bachelor's degree", "Master's degree",
                    "Doctorate/Professional degree",
                ],
            },
            {
                "name": "Primary Language",
                "input_type": "select_other",
                "sort_order": 11,
                "options_json": [
                    "English", "French", "Arabic", "Mandarin", "Cantonese",
                    "Punjabi", "Spanish", "Tagalog", "Tamil", "Urdu",
                ],
            },
            {"name": "Other Language", "input_type": "text", "sort_order": 12},
            {
                "name": "English Proficiency",
                "input_type": "select",
                "sort_order": 13,
                "options_json": ["Native/Fluent", "Advanced", "Intermediate", "Beginner", "None"],
            },
            {
                "name": "French Proficiency",
                "input_type": "select",
                "sort_order": 14,
                "options_json": ["Native/Fluent", "Advanced", "Intermediate", "Beginner", "None"],
            },
        ],
    },
    {
        "title": "Immigration & Residency",
        "sort_order": 2,
        "fields": [
            {
                "name": "Immigration Status",
                "input_type": "select",
                "sort_order": 1,
                "options_json": [
                    "Canadian Citizen", "Permanent Resident",
                    "Convention Refugee/Protected Person",
                    "Temporary Resident (Work Permit)",
                    "Temporary Resident (Study Permit)",
                    "Refugee Claimant", "No Status",
                ],
            },
            {
                "name": "Born in Canada",
                "input_type": "select",
                "sort_order": 2,
                "options_json": ["Yes", "No"],
            },
            {
                "name": "Country of Birth",
                "input_type": "text",
                "sort_order": 3,
            },
            {
                "name": "Time in Canada",
                "input_type": "select",
                "sort_order": 4,
                "options_json": [
                    "Less than 1 year", "1-3 years", "3-5 years",
                    "5-10 years", "More than 10 years", "Born in Canada",
                ],
            },
            {
                "name": "Has Indian Status Card",
                "input_type": "select",
                "sort_order": 5,
                "options_json": ["Yes", "No"],
            },
        ],
    },
    {
        "title": "Household",
        "sort_order": 3,
        "fields": [
            {
                "name": "Household Type",
                "input_type": "select",
                "sort_order": 1,
                "options_json": [
                    "Single person", "Couple without children",
                    "Couple with children", "Single parent",
                    "Extended family", "Roommates/Shared housing",
                ],
            },
            {
                "name": "Household Composition",
                "input_type": "select_other",
                "sort_order": 2,
                "options_json": [
                    "Living alone", "With spouse/partner", "With spouse/partner and children",
                    "With children only", "With parents/family", "With roommates",
                ],
            },
            {
                "name": "Living Arrangement",
                "input_type": "select",
                "sort_order": 3,
                "options_json": [
                    "Own home (with mortgage)", "Own home (no mortgage)",
                    "Renting - market rate", "Renting - subsidised",
                    "Living with family (no rent)", "Shelter/Transitional housing",
                    "Homeless/No fixed address",
                ],
            },
            {
                "name": "Number of Household Members",
                "input_type": "number",
                "sort_order": 4,
            },
            {
                "name": "Number of Dependent Children",
                "input_type": "number",
                "sort_order": 5,
            },
        ],
    },
    {
        "title": "Financial Profile",
        "sort_order": 4,
        "fields": [
            {
                "name": "Household Income Bracket",
                "input_type": "select",
                "sort_order": 1,
                "options_json": [
                    "Under $15,000", "$15,000-$24,999", "$25,000-$34,999",
                    "$35,000-$49,999", "$50,000-$74,999", "$75,000-$99,999",
                    "$100,000 or more", "Prefer not to say",
                ],
            },
            {
                "name": "Employment Status at Intake",
                "input_type": "select",
                "sort_order": 2,
                "options_json": [
                    "Full-time employed", "Part-time employed",
                    "Self-employed", "Unemployed - seeking work",
                    "Unemployed - not seeking work",
                    "Student", "Retired", "On disability/Leave",
                ],
            },
            {
                "name": "Housing Status",
                "input_type": "select",
                "sort_order": 3,
                "options_json": [
                    "Stable housing", "At risk of homelessness",
                    "Transitional housing", "Homeless/Shelter",
                ],
            },
            {
                "name": "Has Bank Account",
                "input_type": "select",
                "sort_order": 4,
                "options_json": ["Yes", "No"],
            },
            {
                "name": "Number of Dependents",
                "input_type": "number",
                "sort_order": 5,
            },
            {
                "name": "Credit Score Monitoring",
                "input_type": "select",
                "sort_order": 6,
                "options_json": [
                    "Regularly monitors credit score",
                    "Checked once or twice",
                    "Never checked",
                    "Does not know what a credit score is",
                ],
            },
            {
                "name": "Tax Filing Status",
                "input_type": "select",
                "sort_order": 7,
                "options_json": [
                    "Filed current year",
                    "Filed but not current year",
                    "Never filed in Canada",
                    "Not required to file",
                ],
            },
            {
                "name": "Unfiled Tax Years",
                "input_type": "text",
                "sort_order": 8,
            },
            {
                "name": "Islamic Finance Practice",
                "input_type": "select",
                "sort_order": 9,
                "options_json": [
                    "Yes - strictly observant",
                    "Yes - partially observant",
                    "No",
                    "Not applicable",
                ],
            },
            {
                "name": "Side Hustle or Gig Work",
                "input_type": "select",
                "sort_order": 10,
                "options_json": [
                    "Yes - regular gig income",
                    "Yes - occasional side work",
                    "No",
                    "Interested in starting",
                ],
            },
        ],
    },
    {
        "title": "Technology Access",
        "sort_order": 5,
        "fields": [
            {
                "name": "Laptop or Computer with Internet",
                "input_type": "select",
                "sort_order": 1,
                "options_json": ["Yes", "No", "Shared access only"],
            },
            {
                "name": "Smart Phone with Data",
                "input_type": "select",
                "sort_order": 2,
                "options_json": ["Yes", "No", "Wi-Fi only"],
            },
            {
                "name": "Tablet with Internet",
                "input_type": "select",
                "sort_order": 3,
                "options_json": ["Yes", "No", "Shared access only"],
            },
        ],
    },
    {
        "title": "Contact Preferences",
        "sort_order": 6,
        "fields": [
            {
                "name": "Preferred Contact Method",
                "input_type": "select",
                "sort_order": 1,
                "options_json": [
                    "Phone call", "Text message", "Email",
                    "WhatsApp", "In person only",
                ],
            },
            {
                "name": "Accessibility Needs",
                "input_type": "textarea",
                "sort_order": 2,
            },
        ],
    },
    {
        "title": "Consent",
        "sort_order": 7,
        "fields": [
            {
                "name": "Consent to Collect and Share Information",
                "input_type": "select",
                "sort_order": 1,
                "options_json": ["Yes", "No"],
            },
            {
                "name": "Consent to Service",
                "input_type": "select",
                "sort_order": 2,
                "options_json": ["Yes", "No"],
            },
            {
                "name": "Consent to Share Data with Funder",
                "input_type": "select",
                "sort_order": 3,
                "options_json": ["Yes", "No"],
            },
        ],
    },
    {
        "title": "Referral & Funding",
        "sort_order": 8,
        "fields": [
            {
                "name": "Referral Source",
                "input_type": "select_other",
                "sort_order": 1,
                "options_json": [
                    "Self-referral", "Community agency", "Settlement agency",
                    "Government program", "Word of mouth", "Social media",
                    "Health care provider", "School/College",
                ],
            },
            {
                "name": "How Did You Hear About Us",
                "input_type": "select_other",
                "sort_order": 2,
                "options_json": [
                    "Friend or family", "Community flyer/poster",
                    "Website search", "Social media", "Referral from agency",
                    "Event or workshop", "Other",
                ],
            },
            {
                "name": "Funding Stream",
                "input_type": "select",
                "sort_order": 3,
                "options_json": [
                    "Prosper Canada - Financial Empowerment",
                    "United Way",
                    "Provincial grant",
                    "Municipal funding",
                    "Core agency funding",
                ],
            },
            {
                "name": "Type of Service Plan",
                "input_type": "select",
                "sort_order": 4,
                "options_json": [
                    "Full coaching (6+ sessions)",
                    "Brief intervention (1-3 sessions)",
                    "Tax clinic only",
                    "Benefits screening only",
                    "Group workshop series",
                ],
            },
        ],
    },
    {
        "title": "Intake Notes",
        "sort_order": 9,
        "fields": [
            {"name": "Budget at Present", "input_type": "textarea", "sort_order": 1},
            {"name": "Intake Notes", "input_type": "textarea", "sort_order": 2},
        ],
    },
]


# ---------------------------------------------------------------------------
# Custom field values for all 12 participants
#
# Keys are record IDs (PC-001 through PC-012). Values are dicts mapping
# field name to the stored value string. Every field across all 9 groups
# is represented, and every select option is covered at least once across
# the 12 participants.
# ---------------------------------------------------------------------------

CUSTOM_FIELD_VALUES = {
    # ------------------------------------------------------------------
    # PC-001  Amira Al-Rashid — Syrian refugee, Arabic-speaking
    # ------------------------------------------------------------------
    "PC-001": {
        # Demographics
        "Preferred Name": "Amira",
        "Pronouns": "She/Her",
        "Gender Identity": "Woman",
        "Date of Birth": "1988-03-14",
        "Marital Status": "Married",
        "Indigenous Identity": "Non-Indigenous",
        "Racial Identity": "Arab",
        "Ethnicity": "Syrian",
        "Disability Status": "No disability",
        "Education Level": "Bachelor's degree",
        "Primary Language": "Arabic",
        "Other Language": "English (learning)",
        "English Proficiency": "Intermediate",
        "French Proficiency": "None",
        # Immigration & Residency
        "Immigration Status": "Convention Refugee/Protected Person",
        "Born in Canada": "No",
        "Country of Birth": "Syria",
        "Time in Canada": "3-5 years",
        "Has Indian Status Card": "No",
        # Household
        "Household Type": "Couple with children",
        "Household Composition": "With spouse/partner and children",
        "Living Arrangement": "Renting - subsidised",
        "Number of Household Members": "5",
        "Number of Dependent Children": "3",
        # Financial Profile
        "Household Income Bracket": "$25,000-$34,999",
        "Employment Status at Intake": "Unemployed - seeking work",
        "Housing Status": "Stable housing",
        "Has Bank Account": "Yes",
        "Number of Dependents": "3",
        "Credit Score Monitoring": "Never checked",
        "Tax Filing Status": "Filed but not current year",
        "Unfiled Tax Years": "2023, 2024",
        "Islamic Finance Practice": "Yes - strictly observant",
        "Side Hustle or Gig Work": "No",
        # Technology Access
        "Laptop or Computer with Internet": "Shared access only",
        "Smart Phone with Data": "Yes",
        "Tablet with Internet": "No",
        # Contact Preferences
        "Preferred Contact Method": "WhatsApp",
        "Accessibility Needs": "",
        # Consent
        "Consent to Collect and Share Information": "Yes",
        "Consent to Service": "Yes",
        "Consent to Share Data with Funder": "Yes",
        # Referral & Funding
        "Referral Source": "Settlement agency",
        "How Did You Hear About Us": "Referral from agency",
        "Funding Stream": "Prosper Canada - Financial Empowerment",
        "Type of Service Plan": "Full coaching (6+ sessions)",
        # Intake Notes
        "Budget at Present": (
            "Monthly income: ~$2,800 (spouse part-time + child benefits). "
            "Rent: $1,200 subsidised. Food: $600. Transportation: $150. "
            "Remittances to family in Lebanon: $200. Minimal savings."
        ),
        "Intake Notes": (
            "Amira arrived in Canada in 2021 as a government-assisted refugee "
            "with her husband and three children. She holds a pharmacy degree "
            "from Damascus University but is not yet licensed in Ontario. "
            "Primary goals: file outstanding taxes, build credit history, "
            "and open a halal-compliant savings vehicle. Very motivated but "
            "limited English literacy makes forms challenging."
        ),
    },
    # ------------------------------------------------------------------
    # PC-002  Jean-Pierre Bouchard — Francophone, Quebecois background
    # ------------------------------------------------------------------
    "PC-002": {
        # Demographics
        "Preferred Name": "J-P",
        "Pronouns": "He/Him",
        "Gender Identity": "Man",
        "Date of Birth": "1975-11-02",
        "Marital Status": "Divorced",
        "Indigenous Identity": "Metis",
        "Racial Identity": "White",
        "Ethnicity": "French-Canadian (Metis heritage)",
        "Disability Status": "Mental health disability",
        "Education Level": "Some college/CEGEP",
        "Primary Language": "French",
        "Other Language": "English",
        "English Proficiency": "Advanced",
        "French Proficiency": "Native/Fluent",
        # Immigration & Residency
        "Immigration Status": "Canadian Citizen",
        "Born in Canada": "Yes",
        "Country of Birth": "Canada",
        "Time in Canada": "Born in Canada",
        "Has Indian Status Card": "No",
        # Household
        "Household Type": "Single person",
        "Household Composition": "Living alone",
        "Living Arrangement": "Renting - market rate",
        "Number of Household Members": "1",
        "Number of Dependent Children": "0",
        # Financial Profile
        "Household Income Bracket": "$15,000-$24,999",
        "Employment Status at Intake": "On disability/Leave",
        "Housing Status": "At risk of homelessness",
        "Has Bank Account": "Yes",
        "Number of Dependents": "0",
        "Credit Score Monitoring": "Checked once or twice",
        "Tax Filing Status": "Filed but not current year",
        "Unfiled Tax Years": "2022, 2023, 2024",
        "Islamic Finance Practice": "Not applicable",
        "Side Hustle or Gig Work": "No",
        # Technology Access
        "Laptop or Computer with Internet": "No",
        "Smart Phone with Data": "Wi-Fi only",
        "Tablet with Internet": "No",
        # Contact Preferences
        "Preferred Contact Method": "Phone call",
        "Accessibility Needs": "Prefers French-language materials and communication.",
        # Consent
        "Consent to Collect and Share Information": "Yes",
        "Consent to Service": "Yes",
        "Consent to Share Data with Funder": "No",
        # Referral & Funding
        "Referral Source": "Community agency",
        "How Did You Hear About Us": "Friend or family",
        "Funding Stream": "United Way",
        "Type of Service Plan": "Full coaching (6+ sessions)",
        # Intake Notes
        "Budget at Present": (
            "Monthly income: ~$1,400 (ODSP). Rent: $950. "
            "Food: $250. Phone: $40. Cigarettes: $120. "
            "Frequently overdrawn by end of month."
        ),
        "Intake Notes": (
            "Jean-Pierre relocated from Montreal after his divorce and is "
            "on ODSP for depression. He has significant consumer debt (~$18,000 "
            "across two credit cards and a line of credit) and has not filed "
            "taxes for three years, potentially missing GST/HST credits and "
            "Ontario Trillium benefits. Priority: tax filing, debt management "
            "plan, and connecting to free mental health supports."
        ),
    },
    # ------------------------------------------------------------------
    # PC-003  Priya Sharma — South Asian, young professional, non-binary
    # ------------------------------------------------------------------
    "PC-003": {
        # Demographics
        "Preferred Name": "",
        "Pronouns": "She/Her",
        "Gender Identity": "Non-binary",
        "Date of Birth": "1996-07-20",
        "Marital Status": "Single",
        "Indigenous Identity": "Non-Indigenous",
        "Racial Identity": "South Asian",
        "Ethnicity": "Indian (Gujarati)",
        "Disability Status": "No disability",
        "Education Level": "Master's degree",
        "Primary Language": "English",
        "Other Language": "Gujarati, Hindi",
        "English Proficiency": "Native/Fluent",
        "French Proficiency": "Advanced",
        # Immigration & Residency
        "Immigration Status": "Permanent Resident",
        "Born in Canada": "No",
        "Country of Birth": "India",
        "Time in Canada": "1-3 years",
        "Has Indian Status Card": "No",
        # Household
        "Household Type": "Roommates/Shared housing",
        "Household Composition": "With roommates",
        "Living Arrangement": "Renting - market rate",
        "Number of Household Members": "3",
        "Number of Dependent Children": "0",
        # Financial Profile
        "Household Income Bracket": "$35,000-$49,999",
        "Employment Status at Intake": "Part-time employed",
        "Housing Status": "Stable housing",
        "Has Bank Account": "Yes",
        "Number of Dependents": "0",
        "Credit Score Monitoring": "Does not know what a credit score is",
        "Tax Filing Status": "Filed current year",
        "Unfiled Tax Years": "",
        "Islamic Finance Practice": "No",
        "Side Hustle or Gig Work": "Yes - occasional side work",
        # Technology Access
        "Laptop or Computer with Internet": "Yes",
        "Smart Phone with Data": "Yes",
        "Tablet with Internet": "No",
        # Contact Preferences
        "Preferred Contact Method": "Email",
        "Accessibility Needs": "",
        # Consent
        "Consent to Collect and Share Information": "Yes",
        "Consent to Service": "Yes",
        "Consent to Share Data with Funder": "Yes",
        # Referral & Funding
        "Referral Source": "Social media",
        "How Did You Hear About Us": "Website search",
        "Funding Stream": "Prosper Canada - Financial Empowerment",
        "Type of Service Plan": "Benefits screening only",
        # Intake Notes
        "Budget at Present": (
            "Monthly income: ~$3,200 (part-time data analyst + freelance). "
            "Rent: $900 (shared). Food: $400. Student loan: $350. "
            "Savings: ~$50/month. No credit card."
        ),
        "Intake Notes": (
            "Priya completed an MSc in Data Science from U of T and is "
            "working part-time while seeking full-time employment. She has "
            "a student loan from her studies in India ($12,000 remaining) "
            "but no Canadian credit history. Goals: build Canadian credit, "
            "understand RRSP vs TFSA, and create a savings plan for "
            "sponsoring her parents' immigration."
        ),
    },
    # ------------------------------------------------------------------
    # PC-004  Kwame Asante — Ghanaian-Canadian, trades worker
    # ------------------------------------------------------------------
    "PC-004": {
        # Demographics
        "Preferred Name": "",
        "Pronouns": "He/Him",
        "Gender Identity": "Man",
        "Date of Birth": "1982-01-30",
        "Marital Status": "Common-law",
        "Indigenous Identity": "Non-Indigenous",
        "Racial Identity": "Black",
        "Ethnicity": "Ghanaian-Canadian",
        "Disability Status": "Physical disability",
        "Education Level": "College diploma/Certificate",
        "Primary Language": "English",
        "Other Language": "Twi",
        "English Proficiency": "Native/Fluent",
        "French Proficiency": "None",
        # Immigration & Residency
        "Immigration Status": "Canadian Citizen",
        "Born in Canada": "No",
        "Country of Birth": "Ghana",
        "Time in Canada": "More than 10 years",
        "Has Indian Status Card": "No",
        # Household
        "Household Type": "Couple with children",
        "Household Composition": "With spouse/partner and children",
        "Living Arrangement": "Renting - market rate",
        "Number of Household Members": "4",
        "Number of Dependent Children": "2",
        # Financial Profile
        "Household Income Bracket": "$75,000-$99,999",
        "Employment Status at Intake": "Full-time employed",
        "Housing Status": "Stable housing",
        "Has Bank Account": "Yes",
        "Number of Dependents": "2",
        "Credit Score Monitoring": "Regularly monitors credit score",
        "Tax Filing Status": "Filed current year",
        "Unfiled Tax Years": "",
        "Islamic Finance Practice": "Not applicable",
        "Side Hustle or Gig Work": "Yes - regular gig income",
        # Technology Access
        "Laptop or Computer with Internet": "Yes",
        "Smart Phone with Data": "Yes",
        "Tablet with Internet": "Yes",
        # Contact Preferences
        "Preferred Contact Method": "Text message",
        "Accessibility Needs": "Has a back injury; prefers meetings on main floor (no stairs).",
        # Consent
        "Consent to Collect and Share Information": "Yes",
        "Consent to Service": "Yes",
        "Consent to Share Data with Funder": "Yes",
        # Referral & Funding
        "Referral Source": "Word of mouth",
        "How Did You Hear About Us": "Friend or family",
        "Funding Stream": "Prosper Canada - Financial Empowerment",
        "Type of Service Plan": "Full coaching (6+ sessions)",
        # Intake Notes
        "Budget at Present": (
            "Monthly income: ~$4,600 (electrician full-time + weekend gig). "
            "Rent: $1,800. Car: $450. Food: $700. Childcare: $600. "
            "Remittances: $300. Debt payments: $250. Savings: minimal."
        ),
        "Intake Notes": (
            "Kwame works as a licensed electrician and does weekend handyman "
            "jobs. He and his partner want to buy a home but have a combined "
            "$15,000 in consumer debt and limited savings. Back injury from "
            "a workplace accident limits some physical work. Goals: create "
            "a debt repayment strategy, understand First-Time Home Buyer "
            "Incentive, and set up an automatic savings plan."
        ),
    },
    # ------------------------------------------------------------------
    # PC-005  Lin Wei — Chinese, senior, limited English
    # ------------------------------------------------------------------
    "PC-005": {
        # Demographics
        "Preferred Name": "",
        "Pronouns": "She/Her",
        "Gender Identity": "Prefer not to say",
        "Date of Birth": "1956-09-08",
        "Marital Status": "Widowed",
        "Indigenous Identity": "Non-Indigenous",
        "Racial Identity": "Chinese",
        "Ethnicity": "Chinese (Cantonese)",
        "Disability Status": "Sensory disability",
        "Education Level": "Some high school",
        "Primary Language": "Cantonese",
        "Other Language": "Mandarin",
        "English Proficiency": "None",
        "French Proficiency": "None",
        # Immigration & Residency
        "Immigration Status": "Canadian Citizen",
        "Born in Canada": "No",
        "Country of Birth": "China",
        "Time in Canada": "More than 10 years",
        "Has Indian Status Card": "No",
        # Household
        "Household Type": "Extended family",
        "Household Composition": "With parents/family",
        "Living Arrangement": "Living with family (no rent)",
        "Number of Household Members": "6",
        "Number of Dependent Children": "0",
        # Financial Profile
        "Household Income Bracket": "Under $15,000",
        "Employment Status at Intake": "Retired",
        "Housing Status": "Stable housing",
        "Has Bank Account": "Yes",
        "Number of Dependents": "0",
        "Credit Score Monitoring": "Never checked",
        "Tax Filing Status": "Never filed in Canada",
        "Unfiled Tax Years": "Multiple years (son handled previously)",
        "Islamic Finance Practice": "Not applicable",
        "Side Hustle or Gig Work": "No",
        # Technology Access
        "Laptop or Computer with Internet": "No",
        "Smart Phone with Data": "Yes",
        "Tablet with Internet": "Shared access only",
        # Contact Preferences
        "Preferred Contact Method": "Phone call",
        "Accessibility Needs": "Hard of hearing; needs interpreter (Cantonese). Prefers large print.",
        # Consent
        "Consent to Collect and Share Information": "Yes",
        "Consent to Service": "Yes",
        "Consent to Share Data with Funder": "Yes",
        # Referral & Funding
        "Referral Source": "Community agency",
        "How Did You Hear About Us": "Community flyer/poster",
        "Funding Stream": "Provincial grant",
        "Type of Service Plan": "Tax clinic only",
        # Intake Notes
        "Budget at Present": (
            "Monthly income: ~$1,100 (OAS + GIS). No rent (lives with son). "
            "Food contribution: $200. Medication: $80. Savings: ~$3,000 "
            "in savings account."
        ),
        "Intake Notes": (
            "Lin is 69 years old and lives with her son's family. Her "
            "husband passed away in 2019. She has never filed her own "
            "taxes in Canada - her son did it sometimes but inconsistently. "
            "She may be missing GIS top-up and GST credits. Hearing "
            "impairment requires phone calls to be loud and slow. "
            "Cantonese interpreter needed for all sessions. Goal: file "
            "back taxes, access all entitled benefits, review GIS amount."
        ),
    },
    # ------------------------------------------------------------------
    # PC-006  Sofia Rodriguez — Latin American, single parent
    # ------------------------------------------------------------------
    "PC-006": {
        # Demographics
        "Preferred Name": "Sofi",
        "Pronouns": "She/Her",
        "Gender Identity": "Woman",
        "Date of Birth": "1990-04-17",
        "Marital Status": "Separated",
        "Indigenous Identity": "Non-Indigenous",
        "Racial Identity": "Latin American",
        "Ethnicity": "Colombian-Canadian",
        "Disability Status": "No disability",
        "Education Level": "High school diploma/GED",
        "Primary Language": "Spanish",
        "Other Language": "English",
        "English Proficiency": "Advanced",
        "French Proficiency": "None",
        # Immigration & Residency
        "Immigration Status": "Permanent Resident",
        "Born in Canada": "No",
        "Country of Birth": "Colombia",
        "Time in Canada": "5-10 years",
        "Has Indian Status Card": "No",
        # Household
        "Household Type": "Single parent",
        "Household Composition": "With children only",
        "Living Arrangement": "Renting - subsidised",
        "Number of Household Members": "3",
        "Number of Dependent Children": "2",
        # Financial Profile
        "Household Income Bracket": "$25,000-$34,999",
        "Employment Status at Intake": "Part-time employed",
        "Housing Status": "Stable housing",
        "Has Bank Account": "Yes",
        "Number of Dependents": "2",
        "Credit Score Monitoring": "Checked once or twice",
        "Tax Filing Status": "Filed current year",
        "Unfiled Tax Years": "",
        "Islamic Finance Practice": "No",
        "Side Hustle or Gig Work": "Interested in starting",
        # Technology Access
        "Laptop or Computer with Internet": "Yes",
        "Smart Phone with Data": "Yes",
        "Tablet with Internet": "No",
        # Contact Preferences
        "Preferred Contact Method": "Text message",
        "Accessibility Needs": "",
        # Consent
        "Consent to Collect and Share Information": "Yes",
        "Consent to Service": "Yes",
        "Consent to Share Data with Funder": "Yes",
        # Referral & Funding
        "Referral Source": "Government program",
        "How Did You Hear About Us": "Event or workshop",
        "Funding Stream": "Municipal funding",
        "Type of Service Plan": "Full coaching (6+ sessions)",
        # Intake Notes
        "Budget at Present": (
            "Monthly income: ~$2,500 (part-time cashier + Canada Child Benefit). "
            "Rent: $850 subsidised. Food: $500. Childcare: $200 (subsidised). "
            "Phone: $50. Transportation: $130. Small debts: $3,200 total."
        ),
        "Intake Notes": (
            "Sofia separated from her husband 18 months ago and is raising "
            "two children (ages 5 and 8) on her own. She works part-time at "
            "a grocery store and receives CCB. She wants to start a small "
            "catering business from home but does not know where to start. "
            "Goals: clear small debts, build an emergency fund, explore "
            "micro-enterprise options and Futurpreneur program eligibility."
        ),
    },
    # ------------------------------------------------------------------
    # PC-007  Tyler Whiteduck — Indigenous, Two-Spirit
    # ------------------------------------------------------------------
    "PC-007": {
        # Demographics
        "Preferred Name": "Ty",
        "Pronouns": "They/Them",
        "Gender Identity": "Two-Spirit",
        "Date of Birth": "1999-12-05",
        "Marital Status": "Single",
        "Indigenous Identity": "First Nations",
        "Racial Identity": "Prefer not to say",
        "Ethnicity": "Algonquin Anishinaabe",
        "Disability Status": "Learning disability",
        "Education Level": "Some high school",
        "Primary Language": "English",
        "Other Language": "Algonquin (some)",
        "English Proficiency": "Native/Fluent",
        "French Proficiency": "Beginner",
        # Immigration & Residency
        "Immigration Status": "Canadian Citizen",
        "Born in Canada": "Yes",
        "Country of Birth": "Canada",
        "Time in Canada": "Born in Canada",
        "Has Indian Status Card": "Yes",
        # Household
        "Household Type": "Roommates/Shared housing",
        "Household Composition": "With roommates",
        "Living Arrangement": "Homeless/No fixed address",
        "Number of Household Members": "2",
        "Number of Dependent Children": "0",
        # Financial Profile
        "Household Income Bracket": "Under $15,000",
        "Employment Status at Intake": "Unemployed - seeking work",
        "Housing Status": "Homeless/Shelter",
        "Has Bank Account": "No",
        "Number of Dependents": "0",
        "Credit Score Monitoring": "Does not know what a credit score is",
        "Tax Filing Status": "Never filed in Canada",
        "Unfiled Tax Years": "2021, 2022, 2023, 2024",
        "Islamic Finance Practice": "Not applicable",
        "Side Hustle or Gig Work": "Yes - occasional side work",
        # Technology Access
        "Laptop or Computer with Internet": "No",
        "Smart Phone with Data": "Wi-Fi only",
        "Tablet with Internet": "No",
        # Contact Preferences
        "Preferred Contact Method": "Text message",
        "Accessibility Needs": "Dyslexia; prefers verbal explanations and simple visuals over text-heavy documents.",
        # Consent
        "Consent to Collect and Share Information": "Yes",
        "Consent to Service": "Yes",
        "Consent to Share Data with Funder": "No",
        # Referral & Funding
        "Referral Source": "Community agency",
        "How Did You Hear About Us": "Friend or family",
        "Funding Stream": "Core agency funding",
        "Type of Service Plan": "Full coaching (6+ sessions)",
        # Intake Notes
        "Budget at Present": (
            "Monthly income: ~$750 (Ontario Works). Rent: $550 (roommate share). "
            "Food: $150 (food bank + shared meals). Phone: $0 (no plan). "
            "Transit: $0 (walks or borrows bike). No bank account - cashes "
            "cheques at Money Mart."
        ),
        "Intake Notes": (
            "Tyler grew up on Pikwakanagan First Nation and moved to Ottawa "
            "at 17. They have been couch-surfing and in shared housing since. "
            "No bank account; uses cheque-cashing services which take fees. "
            "Has never filed taxes and may be owed significant refunds. "
            "Learning disability (dyslexia) means written forms are a barrier. "
            "Goals: open a no-fee bank account, file back taxes, apply for "
            "Post-Secondary Student Support Program. Very engaged when "
            "information is presented verbally or visually."
        ),
    },
    # ------------------------------------------------------------------
    # PC-008  Olga Petrov — Eastern European, older worker
    # ------------------------------------------------------------------
    "PC-008": {
        # Demographics
        "Preferred Name": "",
        "Pronouns": "Ze/Zir",
        "Gender Identity": "Woman",
        "Date of Birth": "1968-06-22",
        "Marital Status": "Married",
        "Indigenous Identity": "Non-Indigenous",
        "Racial Identity": "White",
        "Ethnicity": "Ukrainian-Canadian",
        "Disability Status": "No disability",
        "Education Level": "Doctorate/Professional degree",
        "Primary Language": "English",
        "Other Language": "Ukrainian, Russian",
        "English Proficiency": "Advanced",
        "French Proficiency": "Intermediate",
        # Immigration & Residency
        "Immigration Status": "Canadian Citizen",
        "Born in Canada": "No",
        "Country of Birth": "Ukraine",
        "Time in Canada": "More than 10 years",
        "Has Indian Status Card": "No",
        # Household
        "Household Type": "Couple without children",
        "Household Composition": "With spouse/partner",
        "Living Arrangement": "Own home (with mortgage)",
        "Number of Household Members": "2",
        "Number of Dependent Children": "0",
        # Financial Profile
        "Household Income Bracket": "$100,000 or more",
        "Employment Status at Intake": "Full-time employed",
        "Housing Status": "Stable housing",
        "Has Bank Account": "Yes",
        "Number of Dependents": "0",
        "Credit Score Monitoring": "Regularly monitors credit score",
        "Tax Filing Status": "Filed current year",
        "Unfiled Tax Years": "",
        "Islamic Finance Practice": "Not applicable",
        "Side Hustle or Gig Work": "No",
        # Technology Access
        "Laptop or Computer with Internet": "Yes",
        "Smart Phone with Data": "Yes",
        "Tablet with Internet": "Yes",
        # Contact Preferences
        "Preferred Contact Method": "Email",
        "Accessibility Needs": "",
        # Consent
        "Consent to Collect and Share Information": "Yes",
        "Consent to Service": "Yes",
        "Consent to Share Data with Funder": "Yes",
        # Referral & Funding
        "Referral Source": "Self-referral",
        "How Did You Hear About Us": "Website search",
        "Funding Stream": "Prosper Canada - Financial Empowerment",
        "Type of Service Plan": "Brief intervention (1-3 sessions)",
        # Intake Notes
        "Budget at Present": (
            "Monthly income: ~$6,500 (both working). Mortgage: $1,900. "
            "Property tax escrow: $350. Car: $400. Insurance: $300. "
            "Food: $600. Sending money to mother in Kyiv: $500. "
            "Savings: $200/month. RRSP contributions lapsed."
        ),
        "Intake Notes": (
            "Olga is a research scientist who immigrated from Kyiv in 2003. "
            "She and her husband own a home with a mortgage renewal coming "
            "in 6 months and are worried about rate increases. They stopped "
            "RRSP contributions to send money to family in Ukraine after "
            "the war began. Goals: mortgage renewal strategy, restart RRSP "
            "contributions, review whether TFSA catch-up makes sense. "
            "Comfortable with financial concepts; needs help with Canadian "
            "product comparison."
        ),
    },
    # ------------------------------------------------------------------
    # PC-009  Daniel Thompson — Canadian-born, construction worker
    # ------------------------------------------------------------------
    "PC-009": {
        # Demographics
        "Preferred Name": "Dan",
        "Pronouns": "He/Him",
        "Gender Identity": "Man",
        "Date of Birth": "1985-08-11",
        "Marital Status": "Married",
        "Indigenous Identity": "Inuit",
        "Racial Identity": "Prefer not to say",
        "Ethnicity": "Inuk (Nunavut)",
        "Disability Status": "No disability",
        "Education Level": "High school diploma/GED",
        "Primary Language": "English",
        "Other Language": "",
        "English Proficiency": "Native/Fluent",
        "French Proficiency": "None",
        # Immigration & Residency
        "Immigration Status": "Canadian Citizen",
        "Born in Canada": "Yes",
        "Country of Birth": "Canada",
        "Time in Canada": "Born in Canada",
        "Has Indian Status Card": "No",
        # Household
        "Household Type": "Couple with children",
        "Household Composition": "With spouse/partner and children",
        "Living Arrangement": "Renting - market rate",
        "Number of Household Members": "5",
        "Number of Dependent Children": "3",
        # Financial Profile
        "Household Income Bracket": "$50,000-$74,999",
        "Employment Status at Intake": "Self-employed",
        "Housing Status": "Stable housing",
        "Has Bank Account": "Yes",
        "Number of Dependents": "3",
        "Credit Score Monitoring": "Checked once or twice",
        "Tax Filing Status": "Filed but not current year",
        "Unfiled Tax Years": "2024",
        "Islamic Finance Practice": "Not applicable",
        "Side Hustle or Gig Work": "Yes - regular gig income",
        # Technology Access
        "Laptop or Computer with Internet": "Shared access only",
        "Smart Phone with Data": "Yes",
        "Tablet with Internet": "No",
        # Contact Preferences
        "Preferred Contact Method": "Phone call",
        "Accessibility Needs": "",
        # Consent
        "Consent to Collect and Share Information": "Yes",
        "Consent to Service": "Yes",
        "Consent to Share Data with Funder": "Yes",
        # Referral & Funding
        "Referral Source": "Word of mouth",
        "How Did You Hear About Us": "Friend or family",
        "Funding Stream": "Prosper Canada - Financial Empowerment",
        "Type of Service Plan": "Full coaching (6+ sessions)",
        # Intake Notes
        "Budget at Present": (
            "Monthly income: ~$4,200 (variable; construction contracts). "
            "Rent: $1,650. Truck payment: $550. Insurance: $250. "
            "Food: $800. Kids activities: $200. Tools/supplies: variable. "
            "Income fluctuates seasonally — winter months are very tight."
        ),
        "Intake Notes": (
            "Daniel is a self-employed general contractor (sole proprietor). "
            "He grew up in Iqaluit and moved south for work. Income is "
            "seasonal with strong summers and lean winters. He has not been "
            "setting aside money for taxes and owes ~$8,000 to CRA. His "
            "wife works part-time. They want to save for a down payment "
            "but cannot seem to get ahead. Goals: set up a tax instalment "
            "plan with CRA, create a seasonal budget, explore FHSA "
            "eligibility."
        ),
    },
    # ------------------------------------------------------------------
    # PC-010  Hana Yilmaz — Turkish, newcomer on work permit
    # ------------------------------------------------------------------
    "PC-010": {
        # Demographics
        "Preferred Name": "",
        "Pronouns": "She/Her",
        "Gender Identity": "Woman",
        "Date of Birth": "1993-02-28",
        "Marital Status": "Prefer not to say",
        "Indigenous Identity": "Non-Indigenous",
        "Racial Identity": "West Asian",
        "Ethnicity": "Turkish",
        "Disability Status": "No disability",
        "Education Level": "Bachelor's degree",
        "Primary Language": "English",
        "Other Language": "Turkish",
        "English Proficiency": "Advanced",
        "French Proficiency": "Intermediate",
        # Immigration & Residency
        "Immigration Status": "Temporary Resident (Work Permit)",
        "Born in Canada": "No",
        "Country of Birth": "Turkey",
        "Time in Canada": "Less than 1 year",
        "Has Indian Status Card": "No",
        # Household
        "Household Type": "Single person",
        "Household Composition": "Living alone",
        "Living Arrangement": "Renting - market rate",
        "Number of Household Members": "1",
        "Number of Dependent Children": "0",
        # Financial Profile
        "Household Income Bracket": "$35,000-$49,999",
        "Employment Status at Intake": "Full-time employed",
        "Housing Status": "Stable housing",
        "Has Bank Account": "Yes",
        "Number of Dependents": "0",
        "Credit Score Monitoring": "Never checked",
        "Tax Filing Status": "Never filed in Canada",
        "Unfiled Tax Years": "",
        "Islamic Finance Practice": "Yes - partially observant",
        "Side Hustle or Gig Work": "No",
        # Technology Access
        "Laptop or Computer with Internet": "Yes",
        "Smart Phone with Data": "Yes",
        "Tablet with Internet": "No",
        # Contact Preferences
        "Preferred Contact Method": "Email",
        "Accessibility Needs": "",
        # Consent
        "Consent to Collect and Share Information": "Yes",
        "Consent to Service": "Yes",
        "Consent to Share Data with Funder": "Yes",
        # Referral & Funding
        "Referral Source": "Settlement agency",
        "How Did You Hear About Us": "Social media",
        "Funding Stream": "Prosper Canada - Financial Empowerment",
        "Type of Service Plan": "Brief intervention (1-3 sessions)",
        # Intake Notes
        "Budget at Present": (
            "Monthly income: ~$3,400 (marketing coordinator). "
            "Rent: $1,500 (studio). Food: $350. Phone: $55. "
            "Transportation: $120. Sending money home: $200. "
            "Trying to save for PR application fees."
        ),
        "Intake Notes": (
            "Hana arrived in Canada 8 months ago on an employer-sponsored "
            "work permit. She has a Canadian bank account but no credit "
            "history and was denied a credit card. She is interested in "
            "halal-compliant savings options but is not strictly observant. "
            "Goals: build credit history, understand Canadian tax obligations "
            "as a temporary resident, and save for permanent residence "
            "application fees (~$2,500)."
        ),
    },
    # ------------------------------------------------------------------
    # PC-011  James Osei — Ghanaian-Canadian, student
    # ------------------------------------------------------------------
    "PC-011": {
        # Demographics
        "Preferred Name": "",
        "Pronouns": "He/Him",
        "Gender Identity": "Man",
        "Date of Birth": "2001-05-15",
        "Marital Status": "Single",
        "Indigenous Identity": "Prefer not to say",
        "Racial Identity": "Black",
        "Ethnicity": "Ghanaian-Canadian",
        "Disability Status": "Prefer not to say",
        "Education Level": "Some college/CEGEP",
        "Primary Language": "English",
        "Other Language": "Twi",
        "English Proficiency": "Native/Fluent",
        "French Proficiency": "Beginner",
        # Immigration & Residency
        "Immigration Status": "Temporary Resident (Study Permit)",
        "Born in Canada": "No",
        "Country of Birth": "Ghana",
        "Time in Canada": "1-3 years",
        "Has Indian Status Card": "No",
        # Household
        "Household Type": "Roommates/Shared housing",
        "Household Composition": "With roommates",
        "Living Arrangement": "Renting - market rate",
        "Number of Household Members": "3",
        "Number of Dependent Children": "0",
        # Financial Profile
        "Household Income Bracket": "Prefer not to say",
        "Employment Status at Intake": "Student",
        "Housing Status": "Stable housing",
        "Has Bank Account": "Yes",
        "Number of Dependents": "0",
        "Credit Score Monitoring": "Never checked",
        "Tax Filing Status": "Filed current year",
        "Unfiled Tax Years": "",
        "Islamic Finance Practice": "Not applicable",
        "Side Hustle or Gig Work": "Yes - occasional side work",
        # Technology Access
        "Laptop or Computer with Internet": "Yes",
        "Smart Phone with Data": "Yes",
        "Tablet with Internet": "Yes",
        # Contact Preferences
        "Preferred Contact Method": "Text message",
        "Accessibility Needs": "",
        # Consent
        "Consent to Collect and Share Information": "No",
        "Consent to Service": "No",
        "Consent to Share Data with Funder": "Yes",
        # Referral & Funding
        "Referral Source": "Health care provider",
        "How Did You Hear About Us": "Other",
        "Funding Stream": "United Way",
        "Type of Service Plan": "Group workshop series",
        # Intake Notes
        "Budget at Present": (
            "Monthly income: ~$1,200 (part-time campus job). "
            "Rent: $700 (shared). Tuition: paid by family in Ghana. "
            "Transportation: $128 (student pass). Food: $250. Phone: $45. "
            "Entertainment: $80. No savings. Uses Buy Now Pay Later for "
            "clothes and electronics."
        ),
        "Intake Notes": (
            "James is a second-year Business Administration international "
            "student at Algonquin College on a study permit, living with "
            "roommates. He works part-time on campus (20 hrs/week as "
            "allowed by his permit). He has started using Buy Now Pay "
            "Later services for purchases and is struggling with the high "
            "cost of living. Referred by the college's financial wellness "
            "centre. Goals: understand tax filing as an international "
            "student, stop BNPL cycle, create a student budget, and learn "
            "about sending money home affordably. Interested in the group "
            "workshop format."
        ),
    },
    # ------------------------------------------------------------------
    # PC-012  Marie-Claire Dubois — Francophone, newcomer from DRC
    # ------------------------------------------------------------------
    "PC-012": {
        # Demographics
        "Preferred Name": "Marie",
        "Pronouns": "She/Her",
        "Gender Identity": "Woman",
        "Date of Birth": "1987-10-09",
        "Marital Status": "Married",
        "Indigenous Identity": "Non-Indigenous",
        "Racial Identity": "Black",
        "Ethnicity": "Congolese",
        "Disability Status": "Multiple disabilities",
        "Education Level": "No formal education",
        "Primary Language": "French",
        "Other Language": "Lingala, Swahili",
        "English Proficiency": "Beginner",
        "French Proficiency": "Native/Fluent",
        # Immigration & Residency
        "Immigration Status": "Refugee Claimant",
        "Born in Canada": "No",
        "Country of Birth": "Democratic Republic of Congo",
        "Time in Canada": "Less than 1 year",
        "Has Indian Status Card": "No",
        # Household
        "Household Type": "Couple with children",
        "Household Composition": "With spouse/partner and children",
        "Living Arrangement": "Shelter/Transitional housing",
        "Number of Household Members": "6",
        "Number of Dependent Children": "4",
        # Financial Profile
        "Household Income Bracket": "Under $15,000",
        "Employment Status at Intake": "Unemployed - not seeking work",
        "Housing Status": "Transitional housing",
        "Has Bank Account": "No",
        "Number of Dependents": "4",
        "Credit Score Monitoring": "Does not know what a credit score is",
        "Tax Filing Status": "Not required to file",
        "Unfiled Tax Years": "",
        "Islamic Finance Practice": "No",
        "Side Hustle or Gig Work": "No",
        # Technology Access
        "Laptop or Computer with Internet": "No",
        "Smart Phone with Data": "No",
        "Tablet with Internet": "No",
        # Contact Preferences
        "Preferred Contact Method": "In person only",
        "Accessibility Needs": (
            "PTSD - needs quiet, private meeting space. "
            "French-only communication. Limited literacy in any language."
        ),
        # Consent
        "Consent to Collect and Share Information": "Yes",
        "Consent to Service": "Yes",
        "Consent to Share Data with Funder": "No",
        # Referral & Funding
        "Referral Source": "Government program",
        "How Did You Hear About Us": "Referral from agency",
        "Funding Stream": "Core agency funding",
        "Type of Service Plan": "Full coaching (6+ sessions)",
        # Intake Notes
        "Budget at Present": (
            "Monthly income: ~$1,800 (interim federal health + provincial "
            "social assistance). Shelter provides housing and some meals. "
            "Diapers/formula: $150. Phone: $0 (no phone). "
            "Everything else provided by shelter and community donations."
        ),
        "Intake Notes": (
            "Marie-Claire arrived in Canada 4 months ago with her husband "
            "and four children (ages 2, 4, 7, 10) as refugee claimants "
            "from DRC. They are currently in transitional shelter housing. "
            "She has no formal education and limited literacy. PTSD from "
            "conflict exposure. Husband is also not yet able to work "
            "(claim pending). No bank account, no ID documents yet. Goals: "
            "open a bank account, apply for all eligible benefits (CCB, "
            "GST credit), get ID documents. All sessions must be in French "
            "with trauma-informed approach. Very high needs; will require "
            "extended coaching."
        ),
    },
}


# ---------------------------------------------------------------------------
# Pre/post survey response data (for Financial Capability Survey)
# P1 = initial survey responses, P2 = follow-up survey responses
# These will be used by create_surveys() — defined here so all data
# constants live together at the top of the file.
# ---------------------------------------------------------------------------

P1_RESPONSES = {
    "PC-001": {
        "I feel confident managing my money day-to-day": 2,
        "I know where to get help with financial problems": 1,
        "I have a plan for paying off my debts": 1,
        "I can cover an unexpected expense of $500": 1,
        "I feel in control of my financial situation": 2,
    },
    "PC-002": {
        "I feel confident managing my money day-to-day": 2,
        "I know where to get help with financial problems": 2,
        "I have a plan for paying off my debts": 1,
        "I can cover an unexpected expense of $500": 1,
        "I feel in control of my financial situation": 1,
    },
    "PC-003": {
        "I feel confident managing my money day-to-day": 3,
        "I know where to get help with financial problems": 2,
        "I have a plan for paying off my debts": 3,
        "I can cover an unexpected expense of $500": 2,
        "I feel in control of my financial situation": 3,
    },
    "PC-004": {
        "I feel confident managing my money day-to-day": 3,
        "I know where to get help with financial problems": 3,
        "I have a plan for paying off my debts": 2,
        "I can cover an unexpected expense of $500": 3,
        "I feel in control of my financial situation": 3,
    },
    "PC-005": {
        "I feel confident managing my money day-to-day": 1,
        "I know where to get help with financial problems": 1,
        "I have a plan for paying off my debts": 4,
        "I can cover an unexpected expense of $500": 2,
        "I feel in control of my financial situation": 1,
    },
    "PC-006": {
        "I feel confident managing my money day-to-day": 2,
        "I know where to get help with financial problems": 2,
        "I have a plan for paying off my debts": 2,
        "I can cover an unexpected expense of $500": 1,
        "I feel in control of my financial situation": 2,
    },
    "PC-007": {
        "I feel confident managing my money day-to-day": 1,
        "I know where to get help with financial problems": 1,
        "I have a plan for paying off my debts": 1,
        "I can cover an unexpected expense of $500": 1,
        "I feel in control of my financial situation": 1,
    },
    "PC-008": {
        "I feel confident managing my money day-to-day": 4,
        "I know where to get help with financial problems": 3,
        "I have a plan for paying off my debts": 4,
        "I can cover an unexpected expense of $500": 4,
        "I feel in control of my financial situation": 3,
    },
    "PC-009": {
        "I feel confident managing my money day-to-day": 2,
        "I know where to get help with financial problems": 2,
        "I have a plan for paying off my debts": 1,
        "I can cover an unexpected expense of $500": 2,
        "I feel in control of my financial situation": 2,
    },
    "PC-010": {
        "I feel confident managing my money day-to-day": 3,
        "I know where to get help with financial problems": 1,
        "I have a plan for paying off my debts": 3,
        "I can cover an unexpected expense of $500": 2,
        "I feel in control of my financial situation": 2,
    },
    "PC-011": {
        "I feel confident managing my money day-to-day": 2,
        "I know where to get help with financial problems": 1,
        "I have a plan for paying off my debts": 2,
        "I can cover an unexpected expense of $500": 1,
        "I feel in control of my financial situation": 2,
    },
    "PC-012": {
        "I feel confident managing my money day-to-day": 1,
        "I know where to get help with financial problems": 1,
        "I have a plan for paying off my debts": 1,
        "I can cover an unexpected expense of $500": 1,
        "I feel in control of my financial situation": 1,
    },
}

P2_RESPONSES = {
    "PC-001": {
        "I feel confident managing my money day-to-day": 4,
        "I know where to get help with financial problems": 3,
        "I have a plan for paying off my debts": 3,
        "I can cover an unexpected expense of $500": 2,
        "I feel in control of my financial situation": 3,
    },
    "PC-002": {
        "I feel confident managing my money day-to-day": 3,
        "I know where to get help with financial problems": 4,
        "I have a plan for paying off my debts": 3,
        "I can cover an unexpected expense of $500": 2,
        "I feel in control of my financial situation": 3,
    },
    "PC-003": {
        "I feel confident managing my money day-to-day": 4,
        "I know where to get help with financial problems": 4,
        "I have a plan for paying off my debts": 4,
        "I can cover an unexpected expense of $500": 3,
        "I feel in control of my financial situation": 4,
    },
    "PC-004": {
        "I feel confident managing my money day-to-day": 4,
        "I know where to get help with financial problems": 4,
        "I have a plan for paying off my debts": 4,
        "I can cover an unexpected expense of $500": 4,
        "I feel in control of my financial situation": 4,
    },
    "PC-005": {
        "I feel confident managing my money day-to-day": 2,
        "I know where to get help with financial problems": 3,
        "I have a plan for paying off my debts": 4,
        "I can cover an unexpected expense of $500": 3,
        "I feel in control of my financial situation": 2,
    },
    "PC-006": {
        "I feel confident managing my money day-to-day": 3,
        "I know where to get help with financial problems": 4,
        "I have a plan for paying off my debts": 3,
        "I can cover an unexpected expense of $500": 2,
        "I feel in control of my financial situation": 3,
    },
    "PC-007": {
        "I feel confident managing my money day-to-day": 3,
        "I know where to get help with financial problems": 3,
        "I have a plan for paying off my debts": 2,
        "I can cover an unexpected expense of $500": 2,
        "I feel in control of my financial situation": 2,
    },
    "PC-008": {
        "I feel confident managing my money day-to-day": 5,
        "I know where to get help with financial problems": 4,
        "I have a plan for paying off my debts": 5,
        "I can cover an unexpected expense of $500": 5,
        "I feel in control of my financial situation": 5,
    },
    "PC-009": {
        "I feel confident managing my money day-to-day": 3,
        "I know where to get help with financial problems": 4,
        "I have a plan for paying off my debts": 3,
        "I can cover an unexpected expense of $500": 3,
        "I feel in control of my financial situation": 3,
    },
    "PC-010": {
        "I feel confident managing my money day-to-day": 4,
        "I know where to get help with financial problems": 3,
        "I have a plan for paying off my debts": 4,
        "I can cover an unexpected expense of $500": 3,
        "I feel in control of my financial situation": 4,
    },
    "PC-011": {
        "I feel confident managing my money day-to-day": 3,
        "I know where to get help with financial problems": 3,
        "I have a plan for paying off my debts": 3,
        "I can cover an unexpected expense of $500": 2,
        "I feel in control of my financial situation": 3,
    },
    "PC-012": {
        "I feel confident managing my money day-to-day": 2,
        "I know where to get help with financial problems": 2,
        "I have a plan for paying off my debts": 1,
        "I can cover an unexpected expense of $500": 1,
        "I feel in control of my financial situation": 2,
    },
}


# ============================================================================
# Management command
# ============================================================================

PROGRAM_NAME = "Prosper Canada Financial Coaching"
PROGRAM_NAME_FR = "Coaching financier de Prospere Canada"
DEMO_PASSWORD = "DemoPass2025!"


class Command(BaseCommand):
    help = "Seed demo data for a Prosper Canada financial coaching instance."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete all Prosper Canada demo data before re-seeding.",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            self._reset()

        staff = self.create_staff()
        program = self.create_program()
        participants = self.create_participants(staff, program)
        self.create_custom_fields(participants)
        self.create_surveys(staff, program, participants)
        self.create_plans(staff, program, participants)
        self.create_notes(staff, program, participants)
        self.create_suggestion_themes(staff, program)
        self.create_metrics(staff, program, participants)
        self.create_portal_participant(program)

        self.stdout.write(
            self.style.SUCCESS("Prosper Canada demo data seeded successfully.")
        )

    # ------------------------------------------------------------------
    # Portal participant — DEMO-001 (Jordan)
    # ------------------------------------------------------------------

    def create_portal_participant(self, program):
        """Create DEMO-001 (Jordan) and a ParticipantUser so the portal demo button works.

        Uses get_or_create so it is safe to run after the base seed (which may
        have already created DEMO-001 as a different persona) or standalone
        (creates a minimal Prosper Canada participant named Jordan).
        """
        from apps.portal.models import ParticipantUser

        # Get or create the demo client file
        client, created = ClientFile.objects.get_or_create(
            record_id="DEMO-001",
            defaults={
                "status": "active",
                "is_demo": True,
            },
        )
        if created:
            client.first_name = "Jordan"
            client.last_name = "Rivera"
            client.save()
            # Enrol in the Prosper Canada program
            from apps.clients.models import ClientProgramEnrolment
            ClientProgramEnrolment.objects.get_or_create(
                client_file=client,
                program=program,
                defaults={"status": "enrolled"},
            )
            self.stdout.write("  Created portal demo client: Jordan Rivera (DEMO-001)")
        else:
            self.stdout.write("  Portal demo client DEMO-001 already exists — using it.")

        # Build email the same way the base seed does
        email_base = os.environ.get("DEMO_EMAIL_BASE", "")
        if email_base and "@" in email_base:
            local, domain = email_base.split("@", 1)
            portal_email = f"{local}+demo-portal@{domain}"
        else:
            portal_email = "demo-portal@example.com"

        if not ParticipantUser.objects.filter(client_file=client).exists():
            participant = ParticipantUser.objects.create_participant(
                email=portal_email,
                client_file=client,
                display_name="Jordan",
                password=DEMO_PASSWORD,
            )
            participant.mfa_method = "exempt"
            participant.journal_disclosure_shown = True
            participant.save(update_fields=["mfa_method", "journal_disclosure_shown"])
            self.stdout.write("  Demo portal participant: Jordan (DEMO-001) created.")
        else:
            self.stdout.write("  Demo portal participant: Jordan (DEMO-001) already exists.")

    # ------------------------------------------------------------------
    # Reset — remove all Prosper Canada demo data
    # ------------------------------------------------------------------

    def _reset(self):
        """Delete all Prosper Canada demo data for a clean re-seed."""
        pc_clients = ClientFile.objects.filter(record_id__startswith="PC-")
        client_pks = list(pc_clients.values_list("pk", flat=True))

        if client_pks:
            # Cascade-aware deletion: plans, notes, surveys linked to PC- clients
            PlanSection.objects.filter(client_file_id__in=client_pks).delete()
            ProgressNote.objects.filter(client_file_id__in=client_pks).delete()
            SurveyResponse.objects.filter(client_file_id__in=client_pks).delete()

        # Delete suggestion themes (SuggestionLinks cascade from theme deletion)
        pc_program = Program.objects.filter(name=PROGRAM_NAME).first()
        if pc_program:
            SuggestionTheme.objects.filter(program=pc_program).delete()

        deleted_clients, _ = pc_clients.delete()
        deleted_users, _ = User.objects.filter(username__in=STAFF_USERNAMES).delete()
        deleted_program, _ = Program.objects.filter(name=PROGRAM_NAME).delete()

        self.stdout.write(
            f"Reset: deleted {deleted_clients} clients, "
            f"{deleted_users} users, {deleted_program} programs."
        )

    # ------------------------------------------------------------------
    # Create staff accounts
    # ------------------------------------------------------------------

    def create_staff(self):
        """Create or update the 5 staff accounts. Returns {username: User}."""
        staff_map = {}
        for s in STAFF:
            user, created = User.objects.get_or_create(
                username=s["username"],
                defaults={
                    "display_name": s["display_name"],
                    "is_admin": s["is_admin"],
                    "is_active": True,
                    "is_staff": s["is_admin"],
                    "is_demo": True,
                    "preferred_language": s["preferred_language"],
                },
            )
            if created:
                user.set_password(DEMO_PASSWORD)
                user.email = s["username"]
                user.save()
                self.stdout.write(f"  Created staff: {s['display_name']}")
            else:
                # Always sync is_demo and display_name, even on existing users
                update_fields = []
                if not user.is_demo:
                    user.is_demo = True
                    update_fields.append("is_demo")
                if user.display_name != s["display_name"]:
                    user.display_name = s["display_name"]
                    update_fields.append("display_name")
                if update_fields:
                    user.save(update_fields=update_fields)
                self.stdout.write(f"  Staff exists: {s['display_name']}")
            staff_map[s["username"]] = user
        return staff_map

    # ------------------------------------------------------------------
    # Create program
    # ------------------------------------------------------------------

    def create_program(self):
        """Create the Prosper Canada Financial Coaching program."""
        program, created = Program.objects.get_or_create(
            name=PROGRAM_NAME,
            defaults={
                "name_fr": PROGRAM_NAME_FR,
                "description": (
                    "One-on-one financial coaching for low-income Canadians. "
                    "Covers budgeting, debt management, tax filing, credit "
                    "building, benefits access, and savings strategies."
                ),
                "colour_hex": "#10B981",
                "service_model": "both",
                "status": "active",
            },
        )
        if created:
            self.stdout.write(f"  Created program: {PROGRAM_NAME}")
        else:
            self.stdout.write(f"  Program exists: {PROGRAM_NAME}")
        return program

    # ------------------------------------------------------------------
    # Create participants and enrolments
    # ------------------------------------------------------------------

    def create_participants(self, staff, program):
        """Create 12 participant ClientFiles and enrol them in the program.

        Also assigns staff to the program via UserProgramRole.
        Returns {record_id: ClientFile}.
        """
        # Ensure all staff have roles on this program
        for s in STAFF:
            user = staff[s["username"]]
            UserProgramRole.objects.get_or_create(
                user=user,
                program=program,
                defaults={"role": s["role"], "status": "active"},
            )

        participants = {}
        for p in PARTICIPANTS:
            # Try to find existing client by record_id
            try:
                client = ClientFile.objects.get(record_id=p["record_id"])
                self.stdout.write(f"  Participant exists: {p['first_name']} {p['last_name']}")
            except ClientFile.DoesNotExist:
                client = ClientFile(
                    record_id=p["record_id"],
                    status="active",
                    is_demo=True,
                )
                client.first_name = p["first_name"]
                client.last_name = p["last_name"]
                client.save()
                self.stdout.write(
                    f"  Created participant: {p['first_name']} {p['last_name']} ({p['record_id']})"
                )

            # Enrol in program
            ClientProgramEnrolment.objects.get_or_create(
                client_file=client,
                program=program,
                defaults={"status": "enrolled"},
            )

            participants[p["record_id"]] = client

        return participants

    # ------------------------------------------------------------------
    # Create custom field groups, definitions, and values
    # ------------------------------------------------------------------

    def create_custom_fields(self, participants):
        """Create all 9 custom field groups, ~55 field definitions,
        and populate values for every participant.
        """
        # Build a lookup: field_name -> CustomFieldDefinition
        field_defs = {}

        for group_spec in CUSTOM_FIELD_GROUPS:
            group, _ = CustomFieldGroup.objects.get_or_create(
                title=group_spec["title"],
                defaults={
                    "sort_order": group_spec["sort_order"],
                    "status": "active",
                },
            )

            for field_spec in group_spec["fields"]:
                defaults = {
                    "input_type": field_spec["input_type"],
                    "sort_order": field_spec["sort_order"],
                    "status": "active",
                    "is_required": False,
                    "is_sensitive": field_spec.get("is_sensitive", False),
                }
                if "options_json" in field_spec:
                    defaults["options_json"] = field_spec["options_json"]

                field_def, _ = CustomFieldDefinition.objects.get_or_create(
                    group=group,
                    name=field_spec["name"],
                    defaults=defaults,
                )
                field_defs[field_spec["name"]] = field_def

        # Populate values for each participant
        values_created = 0
        values_existing = 0

        for record_id, client in participants.items():
            field_values = CUSTOM_FIELD_VALUES.get(record_id, {})
            for field_name, value in field_values.items():
                field_def = field_defs.get(field_name)
                if field_def is None:
                    self.stderr.write(
                        self.style.WARNING(
                            f"  Unknown field '{field_name}' for {record_id} — skipping."
                        )
                    )
                    continue

                cdv, created = ClientDetailValue.objects.get_or_create(
                    client_file=client,
                    field_def=field_def,
                )
                if created or cdv.get_value() != str(value):
                    cdv.set_value(str(value))
                    cdv.save()
                    if created:
                        values_created += 1
                else:
                    values_existing += 1

        self.stdout.write(
            f"  Custom fields: {values_created} created, "
            f"{values_existing} already existed."
        )

    # ------------------------------------------------------------------
    # Stub methods — to be implemented later
    # ------------------------------------------------------------------

    def create_surveys(self, staff, program, participants):
        """Create 5 surveys with sections, questions, and realistic responses.

        Surveys:
          P1 — Quality of Life & Financial Wellbeing Assessment (portal)
          P2 — Financial Coaching Needs Assessment (portal)
          S1 — Financial Progress Check-in (staff)
          S2 — Tax & Benefits Review (staff)
          S3 — Employment & Skills Review (staff)
        """
        sara = staff["sara@demo.konote.ca"]

        # Participant shortcuts by index (1-based to match PC-00N)
        p = {i: participants[f"PC-{i:03d}"] for i in range(1, 13)}

        # Intake dates by participant index
        intake = {}
        for pdata in PARTICIPANTS:
            idx = int(pdata["record_id"].split("-")[1])
            intake[idx] = pdata["intake_date"]

        # Helper: get or create a full survey with sections and questions.
        # Returns (survey, {section_sort: {q_sort: SurveyQuestion}})
        def build_survey(spec):
            survey, _ = Survey.objects.get_or_create(
                name=spec["name"],
                defaults={
                    "name_fr": spec.get("name_fr", ""),
                    "description": spec.get("description", ""),
                    "description_fr": spec.get("description_fr", ""),
                    "status": "active",
                    "is_anonymous": spec.get("is_anonymous", False),
                    "portal_visible": spec.get("portal_visible", True),
                    "created_by": sara,
                },
            )
            q_map = {}  # {section_sort: {q_sort: question}}
            for sec_spec in spec["sections"]:
                section, _ = SurveySection.objects.get_or_create(
                    survey=survey,
                    sort_order=sec_spec["sort_order"],
                    defaults={
                        "title": sec_spec["title"],
                        "title_fr": sec_spec.get("title_fr", ""),
                        "scoring_method": sec_spec.get("scoring_method", "none"),
                        "is_active": True,
                    },
                )
                q_map[sec_spec["sort_order"]] = {}
                for q_spec in sec_spec["questions"]:
                    question, _ = SurveyQuestion.objects.get_or_create(
                        section=section,
                        sort_order=q_spec["sort_order"],
                        defaults={
                            "question_text": q_spec["text"],
                            "question_text_fr": q_spec.get("text_fr", ""),
                            "question_type": q_spec["type"],
                            "required": q_spec.get("required", False),
                            "options_json": q_spec.get("options", []),
                            "min_value": q_spec.get("min_value"),
                            "max_value": q_spec.get("max_value"),
                        },
                    )
                    q_map[sec_spec["sort_order"]][q_spec["sort_order"]] = question
            return survey, q_map

        # Helper: create a response with answers if it doesn't exist yet.
        # answers_data: list of (section_sort, q_sort, value_str, numeric_or_None)
        def create_response(survey, q_map, client_file, channel,
                            submitted_dt, answers_data):
            existing = SurveyResponse.objects.filter(
                survey=survey, client_file=client_file, channel=channel,
                submitted_at=submitted_dt,
            ).first()
            if existing:
                return existing
            resp = SurveyResponse.objects.create(
                survey=survey, client_file=client_file, channel=channel,
            )
            # Backdate
            SurveyResponse.objects.filter(pk=resp.pk).update(
                submitted_at=submitted_dt,
            )
            for sec_sort, q_sort, val, numeric in answers_data:
                q = q_map[sec_sort][q_sort]
                ans = SurveyAnswer(response=resp, question=q)
                ans.value = str(val)
                ans.numeric_value = numeric
                ans.save()
            return resp

        def dt(d, hour=10):
            """date -> timezone-aware datetime at given hour."""
            from datetime import datetime as _dt
            return timezone.make_aware(
                _dt(d.year, d.month, d.day, hour, 0, 0)
            )

        # ==================================================================
        # P1 — Quality of Life & Financial Wellbeing Assessment
        # ==================================================================
        cfpb_options_agree = [
            {"value": "0", "label": "Does not describe me at all",
             "label_fr": "Ne me decrit pas du tout", "score": 0},
            {"value": "1", "label": "Describes me very little",
             "label_fr": "Me decrit tres peu", "score": 1},
            {"value": "2", "label": "Describes me somewhat",
             "label_fr": "Me decrit un peu", "score": 2},
            {"value": "3", "label": "Describes me very well",
             "label_fr": "Me decrit tres bien", "score": 3},
            {"value": "4", "label": "Describes me completely",
             "label_fr": "Me decrit completement", "score": 4},
        ]
        cfpb_options_reverse = [
            {"value": "0", "label": "Describes me completely",
             "label_fr": "Me decrit completement", "score": 0},
            {"value": "1", "label": "Describes me very well",
             "label_fr": "Me decrit tres bien", "score": 1},
            {"value": "2", "label": "Describes me somewhat",
             "label_fr": "Me decrit un peu", "score": 2},
            {"value": "3", "label": "Describes me very little",
             "label_fr": "Me decrit tres peu", "score": 3},
            {"value": "4", "label": "Does not describe me at all",
             "label_fr": "Ne me decrit pas du tout", "score": 4},
        ]
        age_group_opts = [
            {"value": "A1", "label": "18-61", "label_fr": "18-61", "score": 0},
            {"value": "A2", "label": "62+", "label_fr": "62+", "score": 0},
        ]
        admin_mode_opts = [
            {"value": "A1", "label": "Self-administered",
             "label_fr": "Auto-administre", "score": 0},
            {"value": "A2", "label": "Interviewer-administered",
             "label_fr": "Administre par l'intervieweur", "score": 0},
        ]
        qol_5opts = lambda labels: [  # noqa: E731
            {"value": str(i), "label": labels[i],
             "label_fr": labels[i], "score": i}
            for i in range(len(labels))
        ]

        p1_spec = {
            "name": "Quality of Life & Financial Wellbeing Assessment",
            "name_fr": "Evaluation de la qualite de vie et du bien-etre financier",
            "description": "CFPB Financial Well-Being Scale + Quality of Life indicators",
            "description_fr": "Echelle de bien-etre financier du CFPB + indicateurs de qualite de vie",
            "portal_visible": True,
            "sections": [
                {
                    "sort_order": 1,
                    "title": "Financial Capability",
                    "title_fr": "Capacite financiere",
                    "scoring_method": "sum",
                    "questions": [
                        {"sort_order": 1, "text": "Date of birth (MM/DD/YYYY)",
                         "text_fr": "Date de naissance (JJ/MM/AAAA)",
                         "type": "short_text"},
                        {"sort_order": 2, "text": "Age group",
                         "text_fr": "Groupe d'age",
                         "type": "single_choice", "options": age_group_opts},
                        # CFPB 5-item scale
                        {"sort_order": 3,
                         "text": "I could handle a major unexpected expense",
                         "text_fr": "Je pourrais faire face a une depense imprevue majeure",
                         "type": "single_choice", "options": cfpb_options_agree,
                         "required": True},
                        {"sort_order": 4,
                         "text": "I am securing my financial future",
                         "text_fr": "J'assure mon avenir financier",
                         "type": "single_choice", "options": cfpb_options_agree,
                         "required": True},
                        {"sort_order": 5,
                         "text": "Because of my money situation, I feel like I will never have the things I want in life",
                         "text_fr": "A cause de ma situation financiere, j'ai l'impression que je n'aurai jamais ce que je veux dans la vie",
                         "type": "single_choice", "options": cfpb_options_reverse,
                         "required": True},
                        {"sort_order": 6,
                         "text": "I can enjoy life because of the way I'm managing my money",
                         "text_fr": "Je peux profiter de la vie grace a la facon dont je gere mon argent",
                         "type": "single_choice", "options": cfpb_options_agree,
                         "required": True},
                        {"sort_order": 7,
                         "text": "I am just getting by financially",
                         "text_fr": "Je m'en sors tout juste financierement",
                         "type": "single_choice", "options": cfpb_options_reverse,
                         "required": True},
                        {"sort_order": 8, "text": "Mode of administration",
                         "text_fr": "Mode d'administration",
                         "type": "single_choice", "options": admin_mode_opts},
                    ],
                },
                {
                    "sort_order": 2,
                    "title": "Quality of Life",
                    "title_fr": "Qualite de vie",
                    "scoring_method": "none",
                    "questions": [
                        {"sort_order": 1,
                         "text": "In general, how would you rate your mental health?",
                         "text_fr": "En general, comment evalueriez-vous votre sante mentale?",
                         "type": "single_choice",
                         "options": qol_5opts(["Poor", "Fair", "Good", "Very good", "Excellent"])},
                        {"sort_order": 2,
                         "text": "How would you describe your sense of belonging to your local community?",
                         "text_fr": "Comment decririez-vous votre sentiment d'appartenance a votre communaute locale?",
                         "type": "single_choice",
                         "options": qol_5opts(["Very weak", "Weak", "Somewhat strong", "Strong", "Very strong"])},
                        {"sort_order": 3,
                         "text": "How would you rate the social support available to you?",
                         "text_fr": "Comment evalueriez-vous le soutien social dont vous disposez?",
                         "type": "single_choice",
                         "options": qol_5opts(["Very poor", "Poor", "Adequate", "Good", "Very good"])},
                        {"sort_order": 4,
                         "text": "How would you rate your ability to handle unexpected stressful events?",
                         "text_fr": "Comment evalueriez-vous votre capacite a gerer des evenements stressants imprevus?",
                         "type": "single_choice",
                         "options": qol_5opts(["Very poor", "Poor", "Adequate", "Good", "Very good"])},
                        {"sort_order": 5,
                         "text": "Thinking about your financial needs, how well are they being met?",
                         "text_fr": "En pensant a vos besoins financiers, dans quelle mesure sont-ils satisfaits?",
                         "type": "single_choice",
                         "options": qol_5opts(["Not at all", "A little", "Somewhat", "Mostly", "Completely"])},
                        {"sort_order": 6,
                         "text": "How prepared do you feel for a financial emergency?",
                         "text_fr": "A quel point vous sentez-vous prepare(e) pour une urgence financiere?",
                         "type": "single_choice",
                         "options": qol_5opts(["Not at all", "A little", "Somewhat", "Mostly", "Completely"])},
                    ],
                },
                {
                    "sort_order": 3,
                    "title": "Financial Coaching Satisfaction",
                    "title_fr": "Satisfaction du coaching financier",
                    "scoring_method": "none",
                    "questions": [
                        {"sort_order": 1,
                         "text": "How satisfied are you with the financial coaching you received?",
                         "text_fr": "Dans quelle mesure etes-vous satisfait(e) du coaching financier que vous avez recu?",
                         "type": "single_choice",
                         "options": qol_5opts(["Very dissatisfied", "Dissatisfied", "Neutral", "Satisfied", "Very satisfied"])},
                        {"sort_order": 2,
                         "text": "What has been the biggest impact of financial coaching on your life?",
                         "text_fr": "Quel a ete le plus grand impact du coaching financier sur votre vie?",
                         "type": "long_text"},
                        {"sort_order": 3,
                         "text": "What suggestions do you have for improving the coaching program?",
                         "text_fr": "Quelles suggestions avez-vous pour ameliorer le programme de coaching?",
                         "type": "long_text"},
                    ],
                },
            ],
        }

        p1_survey, p1_q = build_survey(p1_spec)

        # CFPB scoring data per participant.
        # raw = SQ3 + SQ5 + SQ6 + (4 - SQ2) + SQ4
        # SQ3=sort3, SQ5=sort5(reverse), SQ6=sort6, SQ2=sort4(agree), SQ4=sort7(reverse)
        # Scaled scores are hardcoded; prod calculates dynamically via IRT lookup.
        # fmt: (dob, age_grp, SQ3, SQ4, SQ5_rev, SQ6, SQ7_rev, admin_mode, scaled)
        #   SQ3=q3, SQ4=q4, SQ5_rev=q5, SQ6=q6, SQ7_rev=q7
        p1_cfpb_intake = {
            #         dob          age  q3 q4 q5 q6 q7 mode scaled
            1:  ("03/15/1992", "A1", 1, 0, 3, 1, 3, "A1", 28),  # low
            2:  ("07/20/1985", "A1", 2, 1, 2, 1, 3, "A2", 33),  # low
            3:  ("11/05/1988", "A1", 2, 2, 1, 2, 1, "A1", 46),  # mid
            4:  ("04/12/1990", "A1", 3, 2, 1, 3, 1, "A1", 52),  # mid
            5:  ("09/30/1975", "A1", 1, 0, 3, 0, 4, "A1", 22),  # low
            6:  ("01/18/1995", "A1", 1, 1, 2, 1, 2, "A1", 31),  # low
            7:  ("06/22/2000", "A1", 0, 0, 4, 0, 4, "A1", 18),  # low
            8:  ("12/03/1960", "A1", 3, 3, 0, 3, 0, "A1", 63),  # high
            9:  ("08/14/1978", "A1", 2, 1, 2, 1, 2, "A1", 36),  # mid-low
            10: ("05/25/1993", "A1", 2, 1, 2, 2, 2, "A1", 39),  # mid-low
        }
        p1_cfpb_followup = {
            #         q3 q4 q5 q6 q7 scaled
            1:  (3, 2, 1, 3, 1, 50),  # +22 improvement (28->50)
            2:  (2, 2, 2, 2, 2, 40),  # +7
            3:  (3, 3, 0, 3, 0, 61),  # +15 improvement (46->61)
            4:  (3, 3, 0, 4, 0, 64),  # +12 high
            5:  (1, 1, 3, 0, 3, 24),  # +2 little/no change
            6:  (2, 2, 1, 2, 1, 44),  # +13
        }
        # QoL data: (mental, belonging, social, stress, financial_needs, preparedness)
        p1_qol_intake = {
            1: (1, 1, 1, 1, 0, 0), 2: (2, 1, 2, 1, 1, 0),
            3: (3, 2, 3, 2, 2, 1), 4: (3, 3, 3, 3, 2, 2),
            5: (1, 0, 1, 0, 0, 0), 6: (2, 1, 2, 1, 1, 0),
            7: (1, 0, 0, 0, 0, 0), 8: (3, 3, 4, 3, 3, 3),
            9: (2, 2, 2, 1, 1, 1), 10: (2, 1, 2, 1, 1, 0),
        }
        p1_qol_followup = {
            1: (3, 2, 3, 2, 2, 2), 2: (3, 2, 3, 2, 2, 1),
            3: (4, 3, 4, 3, 3, 3), 4: (4, 4, 4, 4, 3, 3),
            5: (1, 1, 1, 0, 0, 0), 6: (3, 2, 3, 2, 2, 1),
        }
        # Satisfaction data (follow-up only): (satisfaction, impact_text, suggestion_text)
        p1_satisfaction = {
            1: (4, "I now have a budget and know where my money goes. I feel more confident about the future.",
                "More group sessions with other newcomers would be helpful."),
            2: (3, "Understanding benefits I qualify for has helped my family.",
                "Would appreciate more evening appointment availability."),
            3: (4, "My credit score has improved significantly which lets me plan for housing.",
                "The program is excellent. Perhaps add online resources."),
            4: (4, "I opened my first bank account and am saving for my apprenticeship tools.",
                "No suggestions — Aminata has been wonderful."),
            5: (2, "I understand more about financial planning but still struggling.",
                "More materials in Mandarin would help."),
            6: (3, "I'm starting to feel more stable financially.",
                "Childcare during sessions would make attendance easier."),
        }

        # Create P1 intake responses (participants 1-10)
        for idx in range(1, 11):
            cfpb = p1_cfpb_intake[idx]
            qol = p1_qol_intake[idx]
            resp_date = intake[idx] + timedelta(days=1)
            answers = [
                # Section 1 (Financial Capability): dob, age_grp, SQ3-SQ7, admin_mode
                (1, 1, cfpb[0], None),
                (1, 2, cfpb[1], None),
                (1, 3, str(cfpb[2]), cfpb[2]),
                (1, 4, str(cfpb[3]), cfpb[3]),
                (1, 5, str(cfpb[4]), cfpb[4]),
                (1, 6, str(cfpb[5]), cfpb[5]),
                (1, 7, str(cfpb[6]), cfpb[6]),
                (1, 8, cfpb[7], None),
                # Section 2 (Quality of Life)
                (2, 1, str(qol[0]), qol[0]),
                (2, 2, str(qol[1]), qol[1]),
                (2, 3, str(qol[2]), qol[2]),
                (2, 4, str(qol[3]), qol[3]),
                (2, 5, str(qol[4]), qol[4]),
                (2, 6, str(qol[5]), qol[5]),
            ]
            create_response(
                p1_survey, p1_q, p[idx], "portal", dt(resp_date), answers,
            )

        # Create P1 follow-up responses (participants 1-6, enrolled 3+ months)
        for idx in range(1, 7):
            cfpb_fu = p1_cfpb_followup[idx]
            qol_fu = p1_qol_followup[idx]
            sat = p1_satisfaction[idx]
            resp_date = intake[idx] + timedelta(days=95)
            answers = [
                (1, 1, p1_cfpb_intake[idx][0], None),  # same dob
                (1, 2, p1_cfpb_intake[idx][1], None),   # same age group
                (1, 3, str(cfpb_fu[0]), cfpb_fu[0]),
                (1, 4, str(cfpb_fu[1]), cfpb_fu[1]),
                (1, 5, str(cfpb_fu[2]), cfpb_fu[2]),
                (1, 6, str(cfpb_fu[3]), cfpb_fu[3]),
                (1, 7, str(cfpb_fu[4]), cfpb_fu[4]),
                (1, 8, p1_cfpb_intake[idx][7], None),
                (2, 1, str(qol_fu[0]), qol_fu[0]),
                (2, 2, str(qol_fu[1]), qol_fu[1]),
                (2, 3, str(qol_fu[2]), qol_fu[2]),
                (2, 4, str(qol_fu[3]), qol_fu[3]),
                (2, 5, str(qol_fu[4]), qol_fu[4]),
                (2, 6, str(qol_fu[5]), qol_fu[5]),
                # Section 3 (Satisfaction) — follow-up only
                (3, 1, str(sat[0]), sat[0]),
                (3, 2, sat[1], None),
                (3, 3, sat[2], None),
            ]
            create_response(
                p1_survey, p1_q, p[idx], "portal", dt(resp_date), answers,
            )

        self.stdout.write("  P1 survey: 16 responses (10 intake + 6 follow-up)")

        # ==================================================================
        # P2 — Financial Coaching Needs Assessment
        # ==================================================================
        interest_yes_very = {"value": "yes_very", "label": "Yes, very interested",
                             "label_fr": "Oui, tres interesse(e)", "score": 2}
        interest_yes_some = {"value": "yes_some", "label": "Yes, somewhat interested",
                             "label_fr": "Oui, assez interesse(e)", "score": 1}
        interest_no = {"value": "no", "label": "No",
                       "label_fr": "Non", "score": 0}
        interest_na = {"value": "na", "label": "Not applicable",
                       "label_fr": "Sans objet", "score": 0}

        interest_opts_3 = [interest_yes_very, interest_yes_some, interest_no]
        interest_opts_4 = [interest_yes_very, interest_yes_some, interest_no, interest_na]

        p2_spec = {
            "name": "Financial Coaching Needs Assessment",
            "name_fr": "Evaluation des besoins en coaching financier",
            "description": "Identifies participant areas of interest for coaching.",
            "description_fr": "Identifie les domaines d'interet des participants pour le coaching.",
            "portal_visible": True,
            "sections": [
                {
                    "sort_order": 1,
                    "title": "Areas of Interest",
                    "title_fr": "Domaines d'interet",
                    "questions": [
                        {"sort_order": 1, "text": "Budgeting and managing expenses",
                         "text_fr": "Budgetisation et gestion des depenses",
                         "type": "single_choice", "options": interest_opts_3},
                        {"sort_order": 2, "text": "Reducing or managing debt",
                         "text_fr": "Reduire ou gerer les dettes",
                         "type": "single_choice", "options": interest_opts_4},
                        {"sort_order": 3, "text": "Building savings",
                         "text_fr": "Constituer une epargne",
                         "type": "single_choice", "options": interest_opts_3},
                        {"sort_order": 4, "text": "Improving credit score",
                         "text_fr": "Ameliorer la cote de credit",
                         "type": "single_choice", "options": interest_opts_4},
                        {"sort_order": 5, "text": "Filing taxes or accessing tax benefits",
                         "text_fr": "Produire des declarations de revenus ou acceder aux avantages fiscaux",
                         "type": "single_choice", "options": interest_opts_3},
                        {"sort_order": 6, "text": "Accessing government benefits",
                         "text_fr": "Acceder aux prestations gouvernementales",
                         "type": "single_choice", "options": interest_opts_3},
                        {"sort_order": 7, "text": "Opening or managing a bank account",
                         "text_fr": "Ouvrir ou gerer un compte bancaire",
                         "type": "single_choice", "options": interest_opts_4},
                        {"sort_order": 8, "text": "Employment or income support",
                         "text_fr": "Emploi ou soutien au revenu",
                         "type": "single_choice", "options": interest_opts_4},
                        {"sort_order": 9, "text": "Housing affordability",
                         "text_fr": "Accessibilite au logement",
                         "type": "single_choice", "options": interest_opts_3},
                        {"sort_order": 10, "text": "Financial planning for the future",
                         "text_fr": "Planification financiere pour l'avenir",
                         "type": "single_choice", "options": interest_opts_3},
                    ],
                },
                {
                    "sort_order": 2,
                    "title": "Other Needs",
                    "title_fr": "Autres besoins",
                    "questions": [
                        {"sort_order": 1,
                         "text": "Are there other areas of financial support you need that were not listed above?",
                         "text_fr": "Y a-t-il d'autres domaines de soutien financier dont vous avez besoin qui n'etaient pas enumeres ci-dessus?",
                         "type": "long_text"},
                        {"sort_order": 2,
                         "text": "None of the above apply to me",
                         "text_fr": "Aucun des elements ci-dessus ne s'applique a moi",
                         "type": "single_choice",
                         "options": [
                             {"value": "yes", "label": "Yes", "label_fr": "Oui", "score": 0},
                             {"value": "no", "label": "No", "label_fr": "Non", "score": 0},
                         ]},
                    ],
                },
            ],
        }

        p2_survey, p2_q = build_survey(p2_spec)

        # P2 response data: 12 participants at intake.
        # Each tuple: (budget, debt, savings, credit, tax, benefits, bank,
        #              employment, housing, planning, other_text, none_above)
        p2_data = {
            1:  ("yes_very", "yes_very", "yes_very", "na", "yes_very", "yes_very",
                 "yes_very", "yes_some", "yes_very", "yes_some",
                 "Help understanding the Canadian banking system.", "no"),
            2:  ("yes_some", "yes_very", "yes_some", "yes_some", "yes_very", "yes_very",
                 "no", "no", "yes_some", "yes_some",
                 "", "no"),
            3:  ("yes_some", "yes_some", "yes_very", "yes_very", "yes_some", "yes_some",
                 "no", "yes_some", "yes_very", "yes_very",
                 "Planning for professional recertification costs.", "no"),
            4:  ("yes_very", "na", "yes_some", "na", "yes_very", "yes_very",
                 "yes_very", "yes_very", "yes_some", "yes_some",
                 "Need help getting trade certification recognized.", "no"),
            5:  ("yes_very", "yes_some", "yes_very", "yes_some", "yes_very", "yes_very",
                 "no", "no", "yes_some", "yes_very",
                 "", "no"),
            6:  ("yes_very", "yes_some", "yes_some", "yes_some", "yes_some", "yes_very",
                 "no", "yes_some", "yes_very", "yes_some",
                 "Childcare subsidies and housing support.", "no"),
            7:  ("yes_very", "yes_very", "yes_some", "na", "yes_very", "yes_very",
                 "yes_very", "yes_very", "yes_some", "no",
                 "ID documents and getting status card renewed.", "no"),
            8:  ("no", "no", "yes_some", "no", "yes_very", "yes_very",
                 "no", "no", "no", "yes_some",
                 "Back tax filing for multiple years.", "no"),
            9:  ("yes_very", "yes_very", "yes_some", "yes_some", "yes_some", "no",
                 "no", "no", "yes_very", "yes_some",
                 "", "no"),
            10: ("yes_very", "yes_some", "yes_some", "na", "yes_very", "yes_very",
                 "yes_very", "yes_some", "yes_some", "yes_some",
                 "Need French-language financial literacy resources.", "no"),
            11: ("yes_some", "yes_some", "yes_very", "yes_some", "yes_some", "yes_some",
                 "no", "yes_some", "yes_very", "yes_very",
                 "", "no"),
            12: ("yes_very", "yes_very", "yes_some", "na", "yes_very", "yes_very",
                 "yes_very", "yes_some", "yes_very", "yes_some",
                 "Everything is overwhelming — need help knowing where to start.", "no"),
        }

        for idx in range(1, 13):
            d = p2_data[idx]
            resp_date = intake[idx] + timedelta(days=1)
            answers = []
            # 10 interest questions in section 1
            for qi in range(10):
                answers.append((1, qi + 1, d[qi], None))
            # Section 2: other text + none_above
            answers.append((2, 1, d[10], None))
            answers.append((2, 2, d[11], None))
            create_response(
                p2_survey, p2_q, p[idx], "portal", dt(resp_date, 11), answers,
            )

        self.stdout.write("  P2 survey: 12 responses (all participants at intake)")

        # ==================================================================
        # S1 — Financial Progress Check-in (staff-entered)
        # ==================================================================
        s1_spec = {
            "name": "Financial Progress Check-in",
            "name_fr": "Bilan de progres financier",
            "description": "Staff-entered financial tracking: income, debt, savings, credit, banking, budget.",
            "description_fr": "Suivi financier par le personnel: revenus, dettes, epargne, credit, services bancaires, budget.",
            "portal_visible": False,
            "sections": [
                {
                    "sort_order": 1, "title": "Assessment Context",
                    "title_fr": "Contexte de l'evaluation",
                    "questions": [
                        {"sort_order": 1, "text": "Assessment number",
                         "text_fr": "Numero d'evaluation", "type": "short_text"},
                        {"sort_order": 2, "text": "Date of assessment",
                         "text_fr": "Date de l'evaluation", "type": "short_text"},
                    ],
                },
                {
                    "sort_order": 2, "title": "Income",
                    "title_fr": "Revenus",
                    "questions": [
                        {"sort_order": 1, "text": "Primary monthly income ($)",
                         "text_fr": "Revenu mensuel principal ($)", "type": "short_text"},
                        {"sort_order": 2, "text": "Income source",
                         "text_fr": "Source de revenu", "type": "single_choice",
                         "options": [
                             {"value": "employment", "label": "Employment",
                              "label_fr": "Emploi", "score": 0},
                             {"value": "self_employment", "label": "Self-employment",
                              "label_fr": "Travail autonome", "score": 0},
                             {"value": "social_assistance", "label": "Social assistance",
                              "label_fr": "Aide sociale", "score": 0},
                             {"value": "disability", "label": "Disability benefits",
                              "label_fr": "Prestations d'invalidite", "score": 0},
                             {"value": "pension", "label": "Pension/retirement",
                              "label_fr": "Pension/retraite", "score": 0},
                             {"value": "ei", "label": "Employment Insurance",
                              "label_fr": "Assurance-emploi", "score": 0},
                             {"value": "other", "label": "Other",
                              "label_fr": "Autre", "score": 0},
                         ]},
                        {"sort_order": 3, "text": "Hourly wage (if applicable)",
                         "text_fr": "Salaire horaire (le cas echeant)", "type": "short_text"},
                    ],
                },
                {
                    "sort_order": 3, "title": "Debt",
                    "title_fr": "Dettes",
                    "questions": [
                        {"sort_order": 1, "text": "Total debt ($)",
                         "text_fr": "Total des dettes ($)", "type": "short_text"},
                        {"sort_order": 2, "text": "Monthly debt payments ($)",
                         "text_fr": "Paiements mensuels de dettes ($)", "type": "short_text"},
                        {"sort_order": 3, "text": "Debt types",
                         "text_fr": "Types de dettes", "type": "short_text"},
                    ],
                },
                {
                    "sort_order": 4, "title": "Savings",
                    "title_fr": "Epargne",
                    "questions": [
                        {"sort_order": 1, "text": "Total savings ($)",
                         "text_fr": "Total de l'epargne ($)", "type": "short_text"},
                        {"sort_order": 2, "text": "Monthly savings contribution ($)",
                         "text_fr": "Contribution mensuelle a l'epargne ($)",
                         "type": "short_text"},
                        {"sort_order": 3, "text": "Has emergency fund",
                         "text_fr": "A un fonds d'urgence", "type": "yes_no"},
                    ],
                },
                {
                    "sort_order": 5, "title": "Net Worth & Credit",
                    "title_fr": "Valeur nette et credit",
                    "questions": [
                        {"sort_order": 1, "text": "Estimated net worth ($)",
                         "text_fr": "Valeur nette estimee ($)", "type": "short_text"},
                        {"sort_order": 2, "text": "Credit score (if known)",
                         "text_fr": "Cote de credit (si connue)", "type": "short_text"},
                        {"sort_order": 3, "text": "Has credit report been reviewed?",
                         "text_fr": "Le rapport de credit a-t-il ete examine?",
                         "type": "yes_no"},
                    ],
                },
                {
                    "sort_order": 6, "title": "Banking",
                    "title_fr": "Services bancaires",
                    "questions": [
                        {"sort_order": 1, "text": "Has bank account",
                         "text_fr": "A un compte bancaire", "type": "yes_no"},
                        {"sort_order": 2, "text": "Monthly bank fees ($)",
                         "text_fr": "Frais bancaires mensuels ($)", "type": "short_text"},
                        {"sort_order": 3,
                         "text": "Estimated annual bank fees saved ($)",
                         "text_fr": "Economies annuelles estimees sur les frais bancaires ($)",
                         "type": "short_text"},
                    ],
                },
                {
                    "sort_order": 7, "title": "Budget & Financial Behaviours",
                    "title_fr": "Budget et comportements financiers",
                    "questions": [
                        {"sort_order": 1, "text": "Has a written budget",
                         "text_fr": "A un budget ecrit", "type": "yes_no"},
                        {"sort_order": 2, "text": "Follows budget regularly",
                         "text_fr": "Suit le budget regulierement", "type": "yes_no"},
                        {"sort_order": 3, "text": "Uses automatic bill payments",
                         "text_fr": "Utilise les paiements automatiques de factures",
                         "type": "yes_no"},
                    ],
                },
                {
                    "sort_order": 8, "title": "Coaching Notes",
                    "title_fr": "Notes de coaching",
                    "questions": [
                        {"sort_order": 1, "text": "Key observations and next steps",
                         "text_fr": "Observations cles et prochaines etapes",
                         "type": "long_text"},
                    ],
                },
            ],
        }

        s1_survey, s1_q = build_survey(s1_spec)

        # S1 response data — trajectories per participant.
        # Helper to build one assessment's answer list.
        def s1_row(assess_num, assess_date, income, income_src, hourly,
                   debt, debt_pmt, debt_types, savings, save_mo, emerg,
                   net_worth, credit, credit_rev,
                   bank_acct, bank_fees, fees_saved,
                   budget, follows, auto_pay, notes):
            return [
                (1, 1, assess_num, None), (1, 2, assess_date, None),
                (2, 1, income, None), (2, 2, income_src, None),
                (2, 3, hourly, None),
                (3, 1, debt, None), (3, 2, debt_pmt, None),
                (3, 3, debt_types, None),
                (4, 1, savings, None), (4, 2, save_mo, None),
                (4, 3, emerg, None),
                (5, 1, net_worth, None), (5, 2, credit, None),
                (5, 3, credit_rev, None),
                (6, 1, bank_acct, None), (6, 2, bank_fees, None),
                (6, 3, fees_saved, None),
                (7, 1, budget, None), (7, 2, follows, None),
                (7, 3, auto_pay, None),
                (8, 1, notes, None),
            ]

        s1_trajectories = {
            # Amira: income $1,100 -> $1,400 -> $2,200; debt decreasing
            1: [
                s1_row("1", "2025-09-20", "1100", "social_assistance", "",
                       "3200", "150", "Payday loan, phone plan",
                       "0", "0", "No",
                       "-3200", "", "No",
                       "Yes", "12.95", "0",
                       "No", "No", "No",
                       "Initial assessment. Amira receiving social assistance. "
                       "Payday loan is urgent — high interest."),
                s1_row("2", "2025-12-15", "1400", "employment", "16.00",
                       "1800", "100", "Phone plan",
                       "200", "50", "No",
                       "-1600", "620", "Yes",
                       "Yes", "4.95", "96",
                       "Yes", "Yes", "No",
                       "Amira found part-time work. Payday loan paid off. "
                       "Budget created. Switched to low-fee bank account."),
                s1_row("3", "2026-02-10", "2200", "employment", "17.50",
                       "800", "75", "Phone plan (almost done)",
                       "600", "100", "No",
                       "-200", "655", "Yes",
                       "Yes", "0", "180",
                       "Yes", "Yes", "Yes",
                       "Full-time employment secured. On track to be debt-free "
                       "by April. Emergency fund target: $1,000 by June."),
            ],
            # Jean-Pierre: income stable ~$2,800; savings growing
            2: [
                s1_row("1", "2025-09-28", "2800", "employment", "",
                       "8500", "350", "Credit card, car loan",
                       "500", "0", "No",
                       "-8000", "680", "Yes",
                       "Yes", "4.95", "0",
                       "No", "No", "No",
                       "Stable employment but not managing debt well. "
                       "No budget in place."),
                s1_row("2", "2025-12-20", "2850", "employment", "",
                       "6200", "350", "Car loan",
                       "1200", "200", "No",
                       "-5000", "695", "Yes",
                       "Yes", "0", "60",
                       "Yes", "Yes", "Yes",
                       "Credit card paid off. Automated savings of $200/month. "
                       "Switched to no-fee account."),
                s1_row("3", "2026-02-15", "2900", "employment", "",
                       "4800", "300", "Car loan (on schedule)",
                       "2400", "300", "Yes",
                       "-2400", "710", "Yes",
                       "Yes", "0", "60",
                       "Yes", "Yes", "Yes",
                       "Emergency fund of $1,000 reached. Increasing savings "
                       "rate. Car loan on track to finish in 16 months."),
            ],
            # Priya: credit score 520 -> 580 -> 640
            3: [
                s1_row("1", "2025-10-05", "2200", "employment", "",
                       "12000", "400", "Student loan, credit card",
                       "300", "0", "No",
                       "-11700", "520", "Yes",
                       "Yes", "9.95", "0",
                       "No", "No", "No",
                       "Canadian credentials not recognized. Working below "
                       "qualification. High debt from education costs."),
                s1_row("2", "2026-01-10", "2200", "employment", "",
                       "10000", "400", "Student loan, credit card (reducing)",
                       "800", "100", "No",
                       "-9200", "580", "Yes",
                       "Yes", "3.95", "72",
                       "Yes", "Yes", "No",
                       "Credit card minimum increased. Bridging program "
                       "application submitted. Credit score improving."),
                s1_row("3", "2026-02-18", "2400", "employment", "",
                       "8500", "400", "Student loan",
                       "1400", "150", "No",
                       "-7100", "640", "Yes",
                       "Yes", "0", "168",
                       "Yes", "Yes", "Yes",
                       "Credit card paid off! Credit score up 120 points. "
                       "Bridging program accepted — starts April."),
            ],
            # Kwame: hourly $16.55 -> $18 -> $21; opened first bank account
            4: [
                s1_row("1", "2025-10-15", "1450", "employment", "16.55",
                       "0", "0", "",
                       "0", "0", "No",
                       "0", "", "No",
                       "No", "0", "0",
                       "No", "No", "No",
                       "No bank account — receiving pay by cheque cashing "
                       "($15/cheque). No savings. Need to open account and "
                       "start building credit."),
                s1_row("2", "2026-01-10", "1580", "employment", "18.00",
                       "0", "0", "",
                       "400", "50", "No",
                       "400", "", "No",
                       "Yes", "0", "180",
                       "Yes", "No", "No",
                       "Bank account opened! No more cheque-cashing fees — "
                       "saving $180/year. Raise to $18/hr. Budget started."),
                s1_row("3", "2026-02-12", "1840", "employment", "21.00",
                       "0", "0", "",
                       "800", "100", "No",
                       "800", "640", "No",
                       "Yes", "0", "180",
                       "Yes", "Yes", "No",
                       "Apprenticeship wage increase to $21/hr. Secured credit "
                       "builder card. Credit score established at 640."),
            ],
            # Lin: income stable; benefits found $3,200/year
            5: [
                s1_row("1", "2025-10-25", "1800", "employment", "",
                       "4500", "200", "Credit card",
                       "200", "0", "No",
                       "-4300", "560", "No",
                       "Yes", "6.95", "0",
                       "No", "No", "No",
                       "Stable income but unaware of available benefits. "
                       "Not filing taxes regularly."),
                s1_row("2", "2026-01-15", "1800", "employment", "",
                       "3800", "200", "Credit card (paying down)",
                       "600", "75", "No",
                       "-3200", "585", "Yes",
                       "Yes", "3.95", "36",
                       "Yes", "Yes", "No",
                       "Filed 2023 and 2024 taxes. GST credit and CCB now "
                       "flowing — $3,200/year in new benefits. Budget in place."),
                s1_row("3", "2026-02-20", "1800", "employment", "",
                       "3200", "200", "Credit card (steady reduction)",
                       "1100", "100", "No",
                       "-2100", "610", "Yes",
                       "Yes", "0", "120",
                       "Yes", "Yes", "Yes",
                       "Benefits flowing. Moved to no-fee account. Setting up "
                       "RESP for daughter. Credit improving steadily."),
            ],
            # Sofia: limited progress at 3-month
            6: [
                s1_row("1", "2025-11-05", "1600", "employment", "16.00",
                       "2800", "150", "Credit card, medical",
                       "100", "0", "No",
                       "-2700", "580", "No",
                       "Yes", "4.95", "0",
                       "No", "No", "No",
                       "Single mother. Income barely covers expenses. "
                       "Medical debt from dental emergency."),
                s1_row("2", "2026-02-05", "1650", "employment", "16.50",
                       "2600", "150", "Credit card, medical",
                       "150", "25", "No",
                       "-2450", "585", "No",
                       "Yes", "4.95", "0",
                       "Yes", "No", "No",
                       "Limited progress due to childcare challenges. Budget "
                       "created but hard to follow. Applied for childcare subsidy."),
            ],
            # Tyler: filed taxes first time; opened bank account
            7: [
                s1_row("1", "2025-11-15", "1200", "social_assistance", "",
                       "1500", "0", "Informal loans",
                       "0", "0", "No",
                       "-1500", "", "No",
                       "No", "0", "0",
                       "No", "No", "No",
                       "Never filed taxes. No bank account. Receiving social "
                       "assistance. Informal debts to family/friends."),
                s1_row("2", "2026-02-10", "1200", "social_assistance", "",
                       "1500", "50", "Informal loans (repaying)",
                       "150", "25", "No",
                       "-1350", "", "No",
                       "Yes", "0", "0",
                       "Yes", "No", "No",
                       "Bank account opened. Filed first tax return — $800 "
                       "refund expected. Repaying family loans $50/month. "
                       "Applied for GST credit."),
            ],
            # Olga: back taxes filed; $4,800 benefits recovered
            8: [
                s1_row("1", "2025-11-20", "3200", "pension", "",
                       "0", "0", "",
                       "8000", "200", "Yes",
                       "8000", "740", "Yes",
                       "Yes", "3.95", "0",
                       "Yes", "Yes", "No",
                       "Financially stable but hasn't filed taxes since 2019. "
                       "Missing significant benefits."),
                s1_row("2", "2026-02-08", "3200", "pension", "",
                       "0", "0", "",
                       "12800", "400", "Yes",
                       "12800", "740", "Yes",
                       "Yes", "0", "48",
                       "Yes", "Yes", "Yes",
                       "Filed 2019-2024 taxes. $4,800 in benefits recovered "
                       "(GST credit + GIS supplement). Moved to no-fee account."),
            ],
            # Daniel: high debt $65,000; budget created
            9: [
                s1_row("1", "2025-12-05", "3800", "employment", "",
                       "65000", "800",
                       "Mortgage shortfall, credit cards, line of credit",
                       "500", "0", "No",
                       "-64500", "620", "Yes",
                       "Yes", "9.95", "0",
                       "No", "No", "No",
                       "Post-separation financial crisis. High debt from "
                       "mortgage responsibilities. Needs comprehensive "
                       "debt strategy."),
                s1_row("2", "2026-02-15", "3800", "employment", "",
                       "62000", "750",
                       "Credit cards (consolidated), line of credit",
                       "1000", "150", "No",
                       "-61000", "635", "Yes",
                       "Yes", "3.95", "72",
                       "Yes", "Yes", "No",
                       "Consolidated credit card debt at lower rate. Budget "
                       "in place — identified $400/month in reduced spending. "
                       "Separation agreement finalized."),
            ],
            # Hana: baseline only
            10: [
                s1_row("1", "2025-12-15", "1100", "social_assistance", "",
                       "0", "0", "",
                       "0", "0", "No",
                       "0", "", "No",
                       "No", "0", "0",
                       "No", "No", "No",
                       "Very recent arrival. No income beyond social assistance. "
                       "No bank account. Needs French-language support for "
                       "everything. Trauma-informed approach essential."),
            ],
        }

        s1_count = 0
        for idx, assessments in s1_trajectories.items():
            for i, answers in enumerate(assessments):
                days_offset = [5, 90, 150][i] if i < 3 else 5 + i * 60
                resp_date = intake[idx] + timedelta(days=days_offset)
                create_response(
                    s1_survey, s1_q, p[idx], "staff_entered",
                    dt(resp_date, 14), answers,
                )
                s1_count += 1

        self.stdout.write(f"  S1 survey: {s1_count} responses (financial progress)")

        # ==================================================================
        # S2 — Tax & Benefits Review (staff-entered)
        # ==================================================================
        yn_opts = [
            {"value": "yes", "label": "Yes", "label_fr": "Oui", "score": 1},
            {"value": "no", "label": "No", "label_fr": "Non", "score": 0},
            {"value": "in_progress", "label": "In progress",
             "label_fr": "En cours", "score": 0},
        ]
        filing_opts = [
            {"value": "filed_current", "label": "Filed (current year)",
             "label_fr": "Produite (annee en cours)", "score": 2},
            {"value": "filed_back", "label": "Filed (back years)",
             "label_fr": "Produite (annees anterieures)", "score": 1},
            {"value": "not_filed", "label": "Not filed",
             "label_fr": "Non produite", "score": 0},
            {"value": "na", "label": "Not applicable",
             "label_fr": "Sans objet", "score": 0},
        ]

        s2_spec = {
            "name": "Tax & Benefits Review",
            "name_fr": "Examen fiscal et des prestations",
            "description": "Staff review of participant tax filing status and benefits access.",
            "description_fr": "Examen par le personnel de la situation fiscale et de l'acces aux prestations.",
            "portal_visible": False,
            "sections": [
                {
                    "sort_order": 1, "title": "Tax Filing Status",
                    "title_fr": "Situation de la declaration de revenus",
                    "questions": [
                        {"sort_order": 1, "text": "Current year tax return status",
                         "text_fr": "Situation de la declaration de revenus de l'annee en cours",
                         "type": "single_choice", "options": filing_opts},
                        {"sort_order": 2, "text": "Back taxes filed (number of years)",
                         "text_fr": "Declarations anterieures produites (nombre d'annees)",
                         "type": "short_text"},
                        {"sort_order": 3, "text": "Tax refund amount received ($)",
                         "text_fr": "Montant du remboursement d'impot recu ($)",
                         "type": "short_text"},
                    ],
                },
                {
                    "sort_order": 2, "title": "Tax Income Secured",
                    "title_fr": "Revenus fiscaux garantis",
                    "questions": [
                        {"sort_order": 1, "text": "Annual tax-related income secured ($)",
                         "text_fr": "Revenu annuel lie a l'impot garanti ($)",
                         "type": "short_text"},
                        {"sort_order": 2, "text": "Income sources identified",
                         "text_fr": "Sources de revenus identifiees",
                         "type": "short_text"},
                    ],
                },
                {
                    "sort_order": 3, "title": "Benefits Access",
                    "title_fr": "Acces aux prestations",
                    "questions": [
                        {"sort_order": 1, "text": "GST/HST Credit",
                         "text_fr": "Credit TPS/TVH",
                         "type": "single_choice", "options": yn_opts},
                        {"sort_order": 2, "text": "Canada Child Benefit (CCB)",
                         "text_fr": "Allocation canadienne pour enfants (ACE)",
                         "type": "single_choice", "options": yn_opts},
                        {"sort_order": 3, "text": "Ontario Trillium Benefit",
                         "text_fr": "Prestation Trillium de l'Ontario",
                         "type": "single_choice", "options": yn_opts},
                        {"sort_order": 4, "text": "GIS / OAS supplement",
                         "text_fr": "SRG / supplement de la SV",
                         "type": "single_choice", "options": yn_opts},
                        {"sort_order": 5, "text": "Other benefits accessed",
                         "text_fr": "Autres prestations accedees",
                         "type": "short_text"},
                    ],
                },
                {
                    "sort_order": 4, "title": "CRA & Government Services",
                    "title_fr": "ARC et services gouvernementaux",
                    "questions": [
                        {"sort_order": 1, "text": "Has CRA My Account",
                         "text_fr": "A un compte Mon dossier de l'ARC",
                         "type": "single_choice", "options": yn_opts},
                        {"sort_order": 2, "text": "Has My Service Canada Account",
                         "text_fr": "A un compte Mon dossier Service Canada",
                         "type": "single_choice", "options": yn_opts},
                    ],
                },
                {
                    "sort_order": 5, "title": "Review Checkpoints",
                    "title_fr": "Points de controle de l'examen",
                    "questions": [
                        {"sort_order": 1, "text": "Review notes and next steps",
                         "text_fr": "Notes d'examen et prochaines etapes",
                         "type": "long_text"},
                    ],
                },
            ],
        }

        s2_survey, s2_q = build_survey(s2_spec)

        # S2 response data: 10 total
        # Each tuple: (filing_status, back_years, refund, annual_secured, sources,
        #   gst, ccb, trillium, gis, other_benefits, cra_acct, msca, notes)
        s2_data = {
            1: [("filed_current", "0", "420",
                 "1800", "GST credit, CCB",
                 "yes", "yes", "in_progress", "no", "IFHP coverage",
                 "yes", "in_progress",
                 "Tax return filed with VITA clinic. CCB now flowing for "
                 "two children. Trillium application in progress.")],
            2: [("filed_current", "0", "0",
                 "600", "GST credit",
                 "yes", "no", "yes", "no", "",
                 "yes", "yes",
                 "Already filing regularly. Confirmed receiving GST and "
                 "Trillium. No children — CCB n/a.")],
            4: [("filed_current", "1", "1200",
                 "1600", "GST credit, Ontario Trillium",
                 "yes", "no", "yes", "no", "Apprenticeship grant",
                 "in_progress", "no",
                 "Filed 2024 for first time + 2023 back taxes. $1,200 "
                 "refund received. CRA account being set up.")],
            5: [
                ("filed_back", "2", "1800",
                 "3200", "GST credit, CCB, Ontario Trillium",
                 "yes", "yes", "yes", "no", "",
                 "yes", "yes",
                 "Filed 2023 and 2024 taxes. Major benefit recovery: "
                 "$3,200/year now flowing."),
                ("filed_current", "0", "0",
                 "3200", "GST credit, CCB, Ontario Trillium",
                 "yes", "yes", "yes", "no", "RESP grant application",
                 "yes", "yes",
                 "All benefits stable. RESP application submitted for "
                 "CESG matching. Next: review RDSP eligibility."),
            ],
            7: [("not_filed", "0", "0",
                 "0", "",
                 "no", "no", "no", "no", "",
                 "no", "no",
                 "First tax return being prepared with VITA clinic. "
                 "Expect $800+ refund and GST credit activation.")],
            8: [
                ("filed_back", "5", "3200",
                 "4800", "GST credit (back), GIS supplement",
                 "yes", "no", "no", "yes", "Ontario Senior Dental",
                 "yes", "yes",
                 "Filed 2019-2024 — 5 years of back taxes. $3,200 lump "
                 "sum refund. GIS supplement now active."),
                ("filed_current", "0", "0",
                 "4800", "GST credit, GIS supplement",
                 "yes", "no", "no", "yes",
                 "Ontario Senior Dental, Guaranteed Annual Income System",
                 "yes", "yes",
                 "All benefits confirmed flowing. Added GAINS (Ontario). "
                 "Annual benefit total now $4,800."),
            ],
            9: [("filed_current", "0", "0",
                 "300", "GST credit",
                 "yes", "no", "no", "no", "",
                 "yes", "yes",
                 "Already filing but income too high for most benefits. "
                 "GST credit only. Focus is on debt management not "
                 "benefit access.")],
            10: [("not_filed", "0", "0",
                  "0", "",
                  "no", "no", "no", "no", "",
                  "no", "no",
                  "Cannot file yet — awaiting SIN. Once received: file "
                  "taxes, apply for CCB (2 children), GST, and Trillium.")],
        }

        s2_count = 0
        for idx, reviews in s2_data.items():
            for i, r in enumerate(reviews):
                days_offset = 30 + i * 75
                resp_date = intake[idx] + timedelta(days=days_offset)
                answers = [
                    (1, 1, r[0], None), (1, 2, r[1], None),
                    (1, 3, r[2], None),
                    (2, 1, r[3], None), (2, 2, r[4], None),
                    (3, 1, r[5], None), (3, 2, r[6], None),
                    (3, 3, r[7], None), (3, 4, r[8], None),
                    (3, 5, r[9], None),
                    (4, 1, r[10], None), (4, 2, r[11], None),
                    (5, 1, r[12], None),
                ]
                create_response(
                    s2_survey, s2_q, p[idx], "staff_entered",
                    dt(resp_date, 15), answers,
                )
                s2_count += 1

        self.stdout.write(f"  S2 survey: {s2_count} responses (tax & benefits)")

        # ==================================================================
        # S3 — Employment & Skills Review (staff-entered)
        # ==================================================================
        emp_status_opts = [
            {"value": "employed_ft", "label": "Employed full-time",
             "label_fr": "Emploi a temps plein", "score": 3},
            {"value": "employed_pt", "label": "Employed part-time",
             "label_fr": "Emploi a temps partiel", "score": 2},
            {"value": "self_employed", "label": "Self-employed",
             "label_fr": "Travail autonome", "score": 2},
            {"value": "seeking", "label": "Seeking employment",
             "label_fr": "A la recherche d'un emploi", "score": 1},
            {"value": "training", "label": "In training/education",
             "label_fr": "En formation/education", "score": 1},
            {"value": "not_seeking", "label": "Not seeking employment",
             "label_fr": "Ne cherche pas d'emploi", "score": 0},
        ]
        training_opts = [
            {"value": "apprenticeship", "label": "Apprenticeship",
             "label_fr": "Apprentissage", "score": 0},
            {"value": "certificate", "label": "Certificate program",
             "label_fr": "Programme de certificat", "score": 0},
            {"value": "bridging", "label": "Bridging program",
             "label_fr": "Programme passerelle", "score": 0},
            {"value": "workplace", "label": "Workplace training",
             "label_fr": "Formation en milieu de travail", "score": 0},
            {"value": "none", "label": "None currently",
             "label_fr": "Aucune actuellement", "score": 0},
        ]
        fin_knowledge_opts = [
            {"value": "1", "label": "Very low",
             "label_fr": "Tres faible", "score": 1},
            {"value": "2", "label": "Low",
             "label_fr": "Faible", "score": 2},
            {"value": "3", "label": "Moderate",
             "label_fr": "Moderee", "score": 3},
            {"value": "4", "label": "Good",
             "label_fr": "Bonne", "score": 4},
            {"value": "5", "label": "Very good",
             "label_fr": "Tres bonne", "score": 5},
        ]

        s3_spec = {
            "name": "Employment & Skills Review",
            "name_fr": "Examen de l'emploi et des competences",
            "description": "Staff assessment of employment status, training, "
                           "and financial knowledge.",
            "description_fr": "Evaluation par le personnel de la situation "
                              "d'emploi, de la formation et des connaissances "
                              "financieres.",
            "portal_visible": False,
            "sections": [
                {
                    "sort_order": 1, "title": "Employment Status",
                    "title_fr": "Situation d'emploi",
                    "questions": [
                        {"sort_order": 1, "text": "Current employment status",
                         "text_fr": "Situation d'emploi actuelle",
                         "type": "single_choice", "options": emp_status_opts},
                        {"sort_order": 2, "text": "Employer/Industry",
                         "text_fr": "Employeur/Industrie",
                         "type": "short_text"},
                        {"sort_order": 3, "text": "Employment goals",
                         "text_fr": "Objectifs d'emploi",
                         "type": "long_text"},
                    ],
                },
                {
                    "sort_order": 2, "title": "Apprenticeship & Training",
                    "title_fr": "Apprentissage et formation",
                    "questions": [
                        {"sort_order": 1, "text": "Current training type",
                         "text_fr": "Type de formation actuel",
                         "type": "single_choice", "options": training_opts},
                        {"sort_order": 2, "text": "Training details",
                         "text_fr": "Details de la formation",
                         "type": "long_text"},
                        {"sort_order": 3,
                         "text": "Credentials or certifications being pursued",
                         "text_fr": "Diplomes ou certifications recherches",
                         "type": "short_text"},
                    ],
                },
                {
                    "sort_order": 3, "title": "Financial Knowledge",
                    "title_fr": "Connaissances financieres",
                    "questions": [
                        {"sort_order": 1,
                         "text": "Self-rated financial knowledge",
                         "text_fr": "Connaissances financieres auto-evaluees",
                         "type": "single_choice",
                         "options": fin_knowledge_opts},
                        {"sort_order": 2, "text": "Areas of strength",
                         "text_fr": "Points forts",
                         "type": "short_text"},
                        {"sort_order": 3, "text": "Areas for development",
                         "text_fr": "Domaines a developper",
                         "type": "short_text"},
                    ],
                },
            ],
        }

        s3_survey, s3_q = build_survey(s3_spec)

        # S3 responses: 4 total (Kwame, Priya, Amira, Tyler)
        # (idx, emp_status, employer, goals, training_type, training_details,
        #  credentials, fin_knowledge, strengths, development)
        s3_responses = [
            (4, "employed_pt", "Construction / skilled trades",
             "Complete electrician apprenticeship and get licensed. "
             "Goal: journeyperson wage of $35+/hr.",
             "apprenticeship",
             "Level 2 apprentice electrician at George Brown. "
             "Employer sponsoring Level 3 in fall.",
             "309A Electrician (Construction & Maintenance)",
             "3", "Earning and practical money management",
             "Credit building, tax planning, retirement savings"),
            (3, "employed_ft", "Healthcare / pharmacy",
             "Get pharmacist credentials recognized in Canada. "
             "Currently working as pharmacy technician.",
             "bridging",
             "Pharmacy Examining Board of Canada (PEBC) preparation. "
             "Enrolled in U of T bridging program.",
             "Pharmacist (PEBC Qualifying Exam)",
             "4", "Budgeting, understanding financial products",
             "Canadian tax system, investment options, credit rebuilding"),
            (1, "employed_pt", "Retail / customer service",
             "Transition to full-time work, ideally in administrative "
             "or settlement services.",
             "workplace",
             "English workplace communication course through YMCA "
             "Employment Services.",
             "OSSD equivalency (in progress)",
             "2", "Learning quickly, motivated",
             "Banking basics, understanding Canadian credit, "
             "benefits navigation"),
            (7, "seeking", "Not currently employed",
             "Find stable employment. Interested in trades or "
             "outdoor work.",
             "none",
             "Exploring pre-apprenticeship programs. Interested in "
             "carpentry or landscaping.",
             "Considering Red Seal trades",
             "1", "Willing to learn, good physical condition",
             "All areas — starting from basics. Budgeting, banking, "
             "taxes."),
        ]

        s3_count = 0
        for (idx, emp, employer, goals, train, train_det, cred,
             fin_k, strengths, development) in s3_responses:
            resp_date = intake[idx] + timedelta(days=40)
            answers = [
                (1, 1, emp, None), (1, 2, employer, None),
                (1, 3, goals, None),
                (2, 1, train, None), (2, 2, train_det, None),
                (2, 3, cred, None),
                (3, 1, fin_k, int(fin_k)),
                (3, 2, strengths, None), (3, 3, development, None),
            ]
            create_response(
                s3_survey, s3_q, p[idx], "staff_entered",
                dt(resp_date, 15), answers,
            )
            s3_count += 1

        self.stdout.write(f"  S3 survey: {s3_count} responses (employment & skills)")
        total = 16 + 12 + s1_count + s2_count + s3_count
        self.stdout.write(
            f"  Surveys complete: 5 surveys, {total} total responses."
        )

    def create_plans(self, staff, program, participants):
        """Create financial coaching plans with sections and targets."""

        # ------------------------------------------------------------------
        # Metric definitions — get_or_create custom financial metrics
        # ------------------------------------------------------------------
        METRIC_DEFS = [
            {"name": "Monthly Income", "name_fr": "Revenu mensuel",
             "definition": "Total monthly income from all sources.",
             "definition_fr": "Revenu mensuel total de toutes les sources.",
             "category": "custom", "min_value": 0, "max_value": 50000,
             "unit": "$", "unit_fr": "$", "higher_is_better": True},
            {"name": "Total Debt", "name_fr": "Dette totale",
             "definition": "Total outstanding consumer and personal debt.",
             "definition_fr": "Total de la dette de consommation et personnelle.",
             "category": "custom", "min_value": 0, "max_value": 10000000,
             "unit": "$", "unit_fr": "$", "higher_is_better": False},
            {"name": "Monthly Savings", "name_fr": "Epargne mensuelle",
             "definition": "Net amount saved per month after expenses.",
             "definition_fr": "Montant net epargne par mois apres depenses.",
             "category": "custom", "min_value": -10000, "max_value": 1000000,
             "unit": "$", "unit_fr": "$", "higher_is_better": True},
            {"name": "Credit Score", "name_fr": "Cote de credit",
             "definition": "Participant credit score (Equifax/TransUnion).",
             "definition_fr": "Cote de credit du participant (Equifax/TransUnion).",
             "category": "custom", "min_value": 300, "max_value": 900,
             "unit": "score", "unit_fr": "pointage", "higher_is_better": True},
            {"name": "Net Worth", "name_fr": "Valeur nette",
             "definition": "Total assets minus total liabilities.",
             "definition_fr": "Total des actifs moins le total des passifs.",
             "category": "custom", "min_value": -10000000, "max_value": 10000000,
             "unit": "$", "unit_fr": "$", "higher_is_better": True},
            {"name": "Bank Fees Saved", "name_fr": "Frais bancaires economises",
             "definition": "Monthly bank fees avoided by switching to no-fee account.",
             "definition_fr": "Frais bancaires mensuels evites en passant a un compte sans frais.",
             "category": "custom", "min_value": 0, "max_value": 10000,
             "unit": "$", "unit_fr": "$", "higher_is_better": True},
            {"name": "CFPB Financial Wellbeing Scale",
             "name_fr": "Echelle de bien-etre financier CFPB",
             "definition": "Consumer Financial Protection Bureau financial wellbeing score.",
             "definition_fr": "Score de bien-etre financier du CFPB.",
             "category": "custom", "min_value": 0, "max_value": 100,
             "unit": "score", "unit_fr": "pointage", "higher_is_better": True},
            {"name": "Benefits Income Secured",
             "name_fr": "Revenus de prestations obtenus",
             "definition": "Annual value of government benefits secured through coaching.",
             "definition_fr": "Valeur annuelle des prestations gouvernementales obtenues.",
             "category": "custom", "min_value": 0, "max_value": 1000000,
             "unit": "$", "unit_fr": "$", "higher_is_better": True},
            {"name": "Tax Refund or Amount Owed",
             "name_fr": "Remboursement ou montant du",
             "definition": "Net tax refund (positive) or amount owed (negative) after filing.",
             "definition_fr": "Remboursement net (positif) ou montant du (negatif) apres production.",
             "category": "custom", "min_value": -50000, "max_value": 100000,
             "unit": "$", "unit_fr": "$", "higher_is_better": True},
            {"name": "Income Secured through Tax Filing",
             "name_fr": "Revenu obtenu par la production de declarations",
             "definition": "Total income secured via tax filing (refunds + benefit unlocks).",
             "definition_fr": "Revenu total obtenu par la production de declarations fiscales.",
             "category": "custom", "min_value": 0, "max_value": 500000,
             "unit": "$", "unit_fr": "$", "higher_is_better": True},
            {"name": "Credit Score Change",
             "name_fr": "Variation de la cote de credit",
             "definition": "Change in credit score since coaching began.",
             "definition_fr": "Variation de la cote de credit depuis le debut du coaching.",
             "category": "custom", "min_value": -600, "max_value": 600,
             "unit": "points", "unit_fr": "points", "higher_is_better": True},
            {"name": "Debt-to-Income Ratio",
             "name_fr": "Ratio dette/revenu",
             "definition": "Monthly debt payments as percentage of gross monthly income.",
             "definition_fr": "Paiements mensuels de la dette en pourcentage du revenu mensuel brut.",
             "category": "custom", "min_value": 0, "max_value": 100,
             "unit": "%", "unit_fr": "%", "higher_is_better": False},
            {"name": "Savings Rate", "name_fr": "Taux d'epargne",
             "definition": "Percentage of income saved each month.",
             "definition_fr": "Pourcentage du revenu epargne chaque mois.",
             "category": "custom", "min_value": -100, "max_value": 100,
             "unit": "%", "unit_fr": "%", "higher_is_better": True},
            {"name": "Income Change", "name_fr": "Variation du revenu",
             "definition": "Change in monthly income since coaching began.",
             "definition_fr": "Variation du revenu mensuel depuis le debut du coaching.",
             "category": "custom", "min_value": -100000, "max_value": 100000,
             "unit": "$", "unit_fr": "$", "higher_is_better": True},
        ]

        metrics = {}
        for md in METRIC_DEFS:
            obj, _ = MetricDefinition.objects.get_or_create(
                name=md["name"],
                defaults={
                    "name_fr": md["name_fr"],
                    "definition": md["definition"],
                    "definition_fr": md["definition_fr"],
                    "category": md["category"],
                    "is_library": False,
                    "is_enabled": True,
                    "min_value": md["min_value"],
                    "max_value": md["max_value"],
                    "unit": md["unit"],
                    "unit_fr": md["unit_fr"],
                    "metric_type": "scale",
                    "higher_is_better": md["higher_is_better"],
                },
            )
            metrics[md["name"]] = obj

        # ------------------------------------------------------------------
        # Financial Coaching plan — sections, targets, and per-participant data
        # ------------------------------------------------------------------

        # Section templates: key -> (name, sort_order, [(target_name, description, metrics)])
        FC_SECTIONS = {
            "A": ("Financial Stability", 1, [
                ("Create and maintain a budget",
                 "Develop a monthly budget that tracks income and expenses.",
                 ["Monthly Income", "Monthly Savings", "CFPB Financial Wellbeing Scale"]),
                ("Reduce debt",
                 "Develop a strategy to reduce consumer debt to a manageable level.",
                 ["Total Debt", "Debt-to-Income Ratio"]),
                ("Build emergency savings",
                 "Save at least $500 in an accessible emergency fund.",
                 ["Monthly Savings", "Savings Rate", "Net Worth"]),
            ]),
            "B": ("Income & Employment", 2, [
                ("Increase income",
                 "Increase household income through employment, training, or benefits.",
                 ["Monthly Income", "Income Change"]),
                ("Access government benefits",
                 "Apply for all eligible government benefits and tax credits.",
                 ["Benefits Income Secured"]),
            ]),
            "C": ("Housing & Basic Needs", 3, [
                ("Maintain stable housing",
                 "Ensure housing costs remain affordable and housing is secure.",
                 ["Monthly Income", "Net Worth"]),
                ("Achieve food security",
                 "Reduce reliance on food banks and ensure consistent access to food.",
                 ["Monthly Savings"]),
            ]),
            "D": ("Financial Knowledge & Skills", 4, [
                ("Improve credit score",
                 "Build or repair credit score through responsible credit use.",
                 ["Credit Score", "Credit Score Change"]),
                ("Build banking literacy",
                 "Understand banking products, fees, and how to use accounts effectively.",
                 ["Bank Fees Saved", "CFPB Financial Wellbeing Scale"]),
            ]),
        }

        # Per-participant section assignments and custom goal text
        FC_PARTICIPANTS = {
            "PC-001": {
                "sections": ["A", "B", "C"],
                "goals": {
                    ("A", 0): {"status": "default",
                               "client_goal": "I want to learn how to make a budget so I can pay my bills and save a little for my kids"},
                    ("A", 1): {"status": "default",
                               "client_goal": "I want to pay off my credit card so it stops growing"},
                    ("A", 2): {"status": "default",
                               "client_goal": "I want to save $500 for emergencies so I don't have to borrow from family"},
                    ("B", 0): {"status": "default",
                               "client_goal": "I want to find a job that uses my pharmacy degree"},
                    ("B", 1): {"status": "completed",
                               "client_goal": "I want to get all the tax credits my family is entitled to"},
                    ("C", 0): {"status": "default",
                               "client_goal": "I want to keep my subsidised apartment and not lose it"},
                    ("C", 1): {"status": "default",
                               "client_goal": "I want to feed my kids healthy food without always worrying about money"},
                },
            },
            "PC-002": {
                "sections": ["A", "B", "D"],
                "goals": {
                    ("A", 0): {"status": "default",
                               "client_goal": "I need to stop running out of money before the end of the month"},
                    ("A", 1): {"status": "default",
                               "client_goal": "I need a plan to pay down my $18,000 debt before it gets worse"},
                    ("A", 2): {"status": "default",
                               "client_goal": "I want to have at least a small cushion so I don't overdraft"},
                    ("B", 0): {"status": "default",
                               "client_goal": "I want to find out if I can do some part-time work while on ODSP"},
                    ("B", 1): {"status": "completed",
                               "client_goal": "I need to get my GST and Trillium credits — I've been missing them for years"},
                    ("D", 0): {"status": "default",
                               "client_goal": "I want to understand my credit report and fix any problems on it"},
                    ("D", 1): {"status": "default",
                               "client_goal": "I want to stop paying fees on my bank account"},
                },
            },
            "PC-003": {
                "sections": ["A", "D"],
                "goals": {
                    ("A", 0): {"status": "completed",
                               "client_goal": "I need a budget that accounts for my freelance income ups and downs"},
                    ("A", 1): {"status": "default",
                               "client_goal": "I want to pay off my Indian student loan faster"},
                    ("A", 2): {"status": "default",
                               "client_goal": "I want to save for sponsoring my parents' immigration"},
                    ("D", 0): {"status": "default",
                               "client_goal": "I need to build a Canadian credit history from scratch"},
                    ("D", 1): {"status": "default",
                               "client_goal": "I want to understand RRSP vs TFSA so I can choose the right one"},
                },
            },
            "PC-004": {
                "sections": ["A", "B", "D"],
                "goals": {
                    ("A", 0): {"status": "default",
                               "client_goal": "I need a budget that handles my seasonal income from construction gigs"},
                    ("A", 1): {"status": "default",
                               "client_goal": "I want to pay off $15,000 so we can qualify for a mortgage"},
                    ("A", 2): {"status": "default",
                               "client_goal": "I want to save for a down payment on a house for my family"},
                    ("B", 0): {"status": "default",
                               "client_goal": "I want to figure out if I should register my handyman work as a business"},
                    ("B", 1): {"status": "default",
                               "client_goal": "I want to make sure I'm getting the Canada Child Benefit and any disability credits"},
                    ("D", 0): {"status": "default",
                               "client_goal": "I want to get my credit score up to 700 so I can get a mortgage"},
                    ("D", 1): {"status": "default",
                               "client_goal": "I need to open a bank account and stop paying to cash my cheques"},
                },
            },
            "PC-006": {
                "sections": ["A", "C"],
                "goals": {
                    ("A", 0): {"status": "default",
                               "client_goal": "I want to track where my money goes every month so I can find room to save"},
                    ("A", 1): {"status": "default",
                               "client_goal": "I need to pay off my $3,200 in small debts"},
                    ("A", 2): {"status": "default",
                               "client_goal": "I want $1,000 in savings so one bad month doesn't ruin everything"},
                    ("C", 0): {"status": "default",
                               "client_goal": "I need to keep my subsidised housing and understand the rules"},
                    ("C", 1): {"status": "deactivated",
                               "client_goal": "I want to afford good food for my kids without the food bank",
                               "status_reason": "Paused — Sofia is focusing on debt repayment first. Will revisit after debts are cleared."},
                },
            },
            "PC-007": {
                "sections": ["A", "B", "D"],
                "goals": {
                    ("A", 0): {"status": "default",
                               "client_goal": "I want to know exactly how much I have to spend each week"},
                    ("A", 1): {"status": "default",
                               "client_goal": "I don't think I have debt but I want to make sure"},
                    ("A", 2): {"status": "default",
                               "client_goal": "I want to save enough to get my own place someday"},
                    ("B", 0): {"status": "default",
                               "client_goal": "I want to find a real job, not just gig stuff"},
                    ("B", 1): {"status": "default",
                               "client_goal": "I want to get the student support program my community has"},
                    ("D", 0): {"status": "default",
                               "client_goal": "I don't even know what a credit score is — I want to understand it and build one"},
                    ("D", 1): {"status": "default",
                               "client_goal": "I need a bank account so I stop paying Money Mart fees"},
                },
            },
            "PC-009": {
                "sections": ["A", "D"],
                "goals": {
                    ("A", 0): {"status": "default",
                               "client_goal": "I need a budget that works for months when construction is slow"},
                    ("A", 1): {"status": "default",
                               "client_goal": "I need to deal with the $8,000 I owe CRA before it gets worse"},
                    ("A", 2): {"status": "default",
                               "client_goal": "I want to save for a down payment — my kids need a real home"},
                    ("D", 0): {"status": "default",
                               "client_goal": "I want to understand my credit score and improve it"},
                    ("D", 1): {"status": "default",
                               "client_goal": "I need to learn about FHSA and how to use it for a house"},
                },
            },
            "PC-010": {
                "sections": ["A", "B", "C"],
                "goals": {
                    ("A", 0): {"status": "default",
                               "client_goal": "I want to budget carefully so I can save for my PR application"},
                    ("A", 1): {"status": "default",
                               "client_goal": "I don't have debt but I want to make sure I don't go into debt"},
                    ("A", 2): {"status": "completed",
                               "client_goal": "I need $2,500 saved for my permanent residence application fees"},
                    ("B", 0): {"status": "default",
                               "client_goal": "I want to negotiate a raise at work or find a better-paying job"},
                    ("B", 1): {"status": "default",
                               "client_goal": "I want to understand what tax benefits I qualify for as a temporary resident"},
                    ("C", 0): {"status": "default",
                               "client_goal": "I want to find a less expensive apartment without losing quality"},
                    ("C", 1): {"status": "default",
                               "client_goal": "I want to learn to cook more at home to save on food costs"},
                },
            },
        }

        # ------------------------------------------------------------------
        # Tax Filing Support plan — separate plan for tax-focused participants
        # ------------------------------------------------------------------

        TAX_SECTION = ("Tax Filing", 1, [
            ("File current-year taxes",
             "Complete and submit current tax year return.",
             ["Tax Refund or Amount Owed", "Income Secured through Tax Filing"]),
            ("File prior-year taxes",
             "File outstanding returns from previous tax years.",
             ["Tax Refund or Amount Owed", "Income Secured through Tax Filing"]),
            ("Access tax-related benefits",
             "Apply for and receive all eligible tax credits and benefits.",
             ["Benefits Income Secured", "Income Secured through Tax Filing"]),
        ])

        TAX_PARTICIPANTS = {
            "PC-007": {
                "goals": [
                    {"idx": 0, "status": "completed",
                     "client_goal": "I want to file my taxes this year so I can get money back",
                     "name": "File current-year taxes"},
                    {"idx": 2, "status": "default",
                     "client_goal": "I want to get my GST/HST credit — I heard I'm missing out",
                     "name": "Access GST/HST credit"},
                ],
            },
            "PC-008": {
                "goals": [
                    {"idx": 1, "status": "completed",
                     "client_goal": "I need to file my returns for 3 missed years to unlock benefits",
                     "name": "File 3 prior-year returns"},
                    {"idx": 2, "status": "completed",
                     "client_goal": "I need to recover the GIS back-payments we are owed",
                     "name": "Secure GIS back-payments",
                     "description": "Apply for retroactive GIS payments after filing prior returns."},
                    {"idx": 2, "status": "default",
                     "client_goal": "I want to make sure we receive the Ontario Trillium Benefit going forward",
                     "name": "Apply for Trillium Benefit",
                     "description": "Apply for Ontario Trillium Benefit after back-filing is complete."},
                ],
            },
            "PC-005": {
                "goals": [
                    {"idx": 0, "status": "completed",
                     "client_goal": "I want my son to help me file this year's taxes on time",
                     "name": "File current-year taxes"},
                    {"idx": 2, "status": "completed",
                     "client_goal": "I want to make sure my OAS and GIS amounts are correct",
                     "name": "Verify OAS/GIS entitlement",
                     "description": "Verify Old Age Security and Guaranteed Income Supplement amounts after filing."},
                ],
            },
            "PC-004": {
                "goals": [
                    {"idx": 0, "status": "default",
                     "client_goal": "I need help filing my self-employment income properly",
                     "name": "File self-employment taxes"},
                    {"idx": 2, "status": "default",
                     "client_goal": "I want to understand my HST obligations for my handyman business",
                     "name": "Understand HST obligations",
                     "description": "Determine if HST registration is required and how to comply."},
                ],
            },
        }

        # ------------------------------------------------------------------
        # Helper to create a target, set encrypted fields, and link metrics
        # ------------------------------------------------------------------
        def _create_target(section, client, sort, name, desc, status,
                           client_goal, metric_names, status_reason=""):
            """Create or retrieve a PlanTarget and link its metrics."""
            existing = PlanTarget.objects.filter(
                plan_section=section, client_file=client, sort_order=sort
            ).first()
            if existing:
                return existing
            target = PlanTarget(
                plan_section=section,
                client_file=client,
                status=status,
                sort_order=sort,
            )
            target.name = name
            target.description = desc
            target.client_goal = client_goal
            if status_reason:
                target.status_reason = status_reason
            target.save()

            for mi, mname in enumerate(metric_names):
                if mname in metrics:
                    PlanTargetMetric.objects.get_or_create(
                        plan_target=target, metric_def=metrics[mname],
                        defaults={"sort_order": mi},
                    )
            return target

        # ------------------------------------------------------------------
        # Create Financial Coaching plan sections and targets
        # ------------------------------------------------------------------
        fc_created = 0
        for record_id, spec in FC_PARTICIPANTS.items():
            client = participants.get(record_id)
            if not client:
                continue
            for sec_key in spec["sections"]:
                sec_name, sec_sort, sec_targets = FC_SECTIONS[sec_key]
                section, _ = PlanSection.objects.get_or_create(
                    client_file=client, name=sec_name, program=program,
                    defaults={"status": "default", "sort_order": sec_sort},
                )
                for ti, (tgt_name, tgt_desc, tgt_metrics) in enumerate(sec_targets):
                    goal_spec = spec["goals"].get((sec_key, ti), {})
                    _create_target(
                        section=section,
                        client=client,
                        sort=ti,
                        name=tgt_name,
                        desc=tgt_desc,
                        status=goal_spec.get("status", "default"),
                        client_goal=goal_spec.get("client_goal", ""),
                        metric_names=tgt_metrics,
                        status_reason=goal_spec.get("status_reason", ""),
                    )
                    fc_created += 1

        self.stdout.write(f"  Financial Coaching plans: {fc_created} targets across 8 participants.")

        # ------------------------------------------------------------------
        # Create Tax Filing Support plan sections and targets
        # ------------------------------------------------------------------
        tax_sec_name, _tax_sec_sort, tax_sec_templates = TAX_SECTION
        tax_created = 0
        for record_id, spec in TAX_PARTICIPANTS.items():
            client = participants.get(record_id)
            if not client:
                continue
            section, _ = PlanSection.objects.get_or_create(
                client_file=client, name=tax_sec_name, program=program,
                defaults={"status": "default", "sort_order": 10},
            )
            for sort_i, goal_spec in enumerate(spec["goals"]):
                tmpl_idx = goal_spec["idx"]
                if tmpl_idx < len(tax_sec_templates):
                    _tmpl_name, tmpl_desc, tmpl_metrics = tax_sec_templates[tmpl_idx]
                else:
                    tmpl_desc, tmpl_metrics = "", ["Benefits Income Secured"]
                _create_target(
                    section=section,
                    client=client,
                    sort=sort_i,
                    name=goal_spec.get("name", ""),
                    desc=goal_spec.get("description", tmpl_desc),
                    status=goal_spec.get("status", "default"),
                    client_goal=goal_spec.get("client_goal", ""),
                    metric_names=tmpl_metrics,
                )
                tax_created += 1

        self.stdout.write(f"  Tax Filing plans: {tax_created} targets across 4 participants.")

    def create_notes(self, staff, program, participants):
        """Create 46 progress notes across 12 participants with 6 note templates.

        Templates:
          1. Intake Assessment (session)
          2. Coaching Session (session) — default
          3. Brief Check-In (phone)
          4. Tax Clinic Visit (session)
          5. Crisis or Urgent Contact (phone)
          6. Case Closing (session)

        Notes are backdated to realistic dates between each participant's
        intake date and 2026-02-24.
        """
        marcus = staff["marcus@demo.konote.ca"]
        aminata = staff["aminata@demo.konote.ca"]

        # Participant shortcuts by record ID
        p = participants  # {record_id: ClientFile}

        # Intake dates by record_id
        intake = {}
        for pdata in PARTICIPANTS:
            intake[pdata["record_id"]] = pdata["intake_date"]

        # Skip if notes already exist for this program
        first_client = p["PC-001"]
        if ProgressNote.objects.filter(
            client_file=first_client, author_program=program
        ).exists():
            self.stdout.write("  Notes: already exist — skipping.")
            return

        # ── Helper: timezone-aware datetime from a date ──────────────
        def dt(d, hour=10):
            from datetime import datetime as _dt
            return timezone.make_aware(
                _dt(d.year, d.month, d.day, hour, 0, 0)
            )

        # ==============================================================
        # Note Templates (6)
        # ==============================================================

        TEMPLATES = [
            {
                "name": "Intake Assessment",
                "name_fr": "Evaluation d'admission",
                "default_interaction_type": "session",
                "sections": [
                    ("Referral & Background", "Recommandation et contexte", "basic"),
                    ("Financial Situation", "Situation financiere", "basic"),
                    ("Identified Needs", "Besoins identifies", "basic"),
                    ("Goals & Next Steps", "Objectifs et prochaines etapes", "basic"),
                ],
            },
            {
                "name": "Coaching Session",
                "name_fr": "Seance de coaching",
                "default_interaction_type": "session",
                "sections": [
                    ("Session Summary", "Resume de la seance", "basic"),
                    ("Goals Reviewed", "Objectifs revus", "plan"),
                    ("Action Items", "Points d'action", "basic"),
                    ("Next Session Plan", "Plan de la prochaine seance", "basic"),
                ],
            },
            {
                "name": "Brief Check-In",
                "name_fr": "Suivi rapide",
                "default_interaction_type": "phone",
                "sections": [
                    ("Reason for Contact", "Raison du contact", "basic"),
                    ("Key Updates", "Mises a jour importantes", "basic"),
                    ("Follow-Up", "Suivi", "basic"),
                ],
            },
            {
                "name": "Tax Clinic Visit",
                "name_fr": "Visite a la clinique d'impots",
                "default_interaction_type": "session",
                "sections": [
                    ("Tax Years Filed", "Annees d'imposition produites", "basic"),
                    ("Documents & Benefits", "Documents et prestations", "basic"),
                    ("Follow-Up", "Suivi", "basic"),
                ],
            },
            {
                "name": "Crisis or Urgent Contact",
                "name_fr": "Contact de crise ou urgent",
                "default_interaction_type": "phone",
                "sections": [
                    ("Nature of Crisis", "Nature de la crise", "basic"),
                    ("Actions Taken", "Mesures prises", "basic"),
                    ("Referrals & Safety", "Recommandations et securite", "basic"),
                    ("Follow-Up Plan", "Plan de suivi", "basic"),
                ],
            },
            {
                "name": "Case Closing",
                "name_fr": "Fermeture de dossier",
                "default_interaction_type": "session",
                "sections": [
                    ("Summary of Services", "Resume des services", "basic"),
                    ("Outcomes Achieved", "Resultats atteints", "basic"),
                    ("Referrals & Continuing Support",
                     "Recommandations et soutien continu", "basic"),
                ],
            },
        ]

        template_map = {}  # name -> ProgressNoteTemplate
        for tspec in TEMPLATES:
            tmpl, _ = ProgressNoteTemplate.objects.get_or_create(
                name=tspec["name"],
                owning_program=program,
                defaults={
                    "name_fr": tspec["name_fr"],
                    "default_interaction_type": tspec["default_interaction_type"],
                    "status": "active",
                },
            )
            template_map[tspec["name"]] = tmpl
            for idx, (sec_name, sec_name_fr, sec_type) in enumerate(
                tspec["sections"], start=1
            ):
                ProgressNoteTemplateSection.objects.get_or_create(
                    template=tmpl,
                    name=sec_name,
                    defaults={
                        "name_fr": sec_name_fr,
                        "section_type": sec_type,
                        "sort_order": idx,
                    },
                )

        self.stdout.write(f"  Note templates: {len(TEMPLATES)} created.")

        # Shorthand template references
        t_intake = template_map["Intake Assessment"]
        t_coaching = template_map["Coaching Session"]
        t_checkin = template_map["Brief Check-In"]
        t_tax = template_map["Tax Clinic Visit"]
        t_crisis = template_map["Crisis or Urgent Contact"]

        # ==============================================================
        # Note data — 46 notes across 12 participants
        # Each entry: (template, days_after_intake, summary_text,
        #              engagement, alliance_rating, alliance_rater)
        # engagement/alliance only set on Coaching notes
        # ==============================================================

        # --- PC-001 Amira (marcus) — 6 notes ---
        NOTES = {
            "PC-001": [
                (t_intake, 0,
                 "Amira referred by Ontario Works caseworker. Single mother of two, "
                 "arrived in Canada 18 months ago from Syria. Currently receiving OW "
                 "benefits of $1,100/month. Has a payday loan of $800 at 47% interest "
                 "that is consuming a significant portion of her income. No bank "
                 "account — using cheque-cashing services at $15 per transaction. "
                 "Identified immediate needs: open a no-fee bank account, address "
                 "payday loan debt, file 2024 taxes to access CCB and GST/HST "
                 "credit. Amira is motivated and eager to build financial stability "
                 "for her children. Next steps: schedule bank appointment at local "
                 "credit union, gather tax documents, begin budget worksheet.",
                 "", None, ""),
                (t_coaching, 21,
                 "Reviewed budget worksheet Amira completed at home. Monthly income "
                 "$1,100 (OW), expenses $1,050. Opened no-fee account at Desjardins "
                 "last week — direct deposit set up for OW cheques. Discussed payday "
                 "loan repayment strategy: $50/pay towards principal. Amira reports "
                 "feeling less stressed about finances. Began exploring part-time "
                 "work options compatible with OW. Action items: contact YMCA "
                 "employment services, bring T4A and T5007 slips to next session "
                 "for tax filing.",
                 "engaged", 4, "worker_observed"),
                (t_coaching, 49,
                 "Amira started part-time cleaning work, earning $400/month. Updated "
                 "budget to reflect new income — now $1,400/month after OW adjustment. "
                 "Payday loan balance down to $400. Filed 2024 taxes through CVITP "
                 "clinic — expecting $2,100 CCB retroactive payment and $450 GST/HST "
                 "credit. Discussed importance of reporting employment income to OW. "
                 "Reviewed Amira's goal of building emergency fund once payday loan "
                 "is cleared. She is feeling more confident managing money.",
                 "engaged", 4, "worker_observed"),
                (t_coaching, 84,
                 "Payday loan fully paid off. CCB retroactive payment received — "
                 "deposited $1,500 into savings, remainder used for children's winter "
                 "clothing. Monthly income now stable at $1,400. Switched phone plan "
                 "to $25/month provider, saving $40/month. Budget tracking "
                 "consistently for 6 weeks. Discussed RESP options for children's "
                 "education savings. Amira expressed interest in upgrading her "
                 "English for better job prospects. Referred to LINC classes at "
                 "neighbourhood centre.",
                 "valuing", 5, "worker_observed"),
                (t_coaching, 126,
                 "Amira secured full-time cleaning position at $17.50/hour through "
                 "employer she was working for part-time. Income now approximately "
                 "$2,200/month. OW file closed. Opened TFSA with automatic $50/month "
                 "transfer. Emergency fund at $600. Credit score improved to 650 "
                 "from initial unscored status. Reviewed workplace benefits — "
                 "employer offers health and dental after 3 months. Amira enrolling "
                 "in evening LINC Level 5 classes. She is proud of her progress and "
                 "wants to eventually pursue PSW certification.",
                 "valuing", 5, "worker_observed"),
                (t_checkin, 140,
                 "Brief phone call to check on Amira's transition off Ontario Works. "
                 "Reports no issues with direct deposit from employer. LINC classes "
                 "going well. Confirmed next coaching session date. No urgent needs.",
                 "", None, ""),
            ],

            # --- PC-002 Jean-Pierre (aminata) — 5 notes ---
            "PC-002": [
                (t_intake, 0,
                 "Jean-Pierre refere par le centre communautaire francophone. Age "
                 "de 58 ans, monoparental avec un adolescent. Recoit le supplement "
                 "de revenu garanti et une petite pension. A accumule des dettes de "
                 "cartes de credit totalisant $4,200 apres une periode de chomage. "
                 "N'a pas produit ses declarations de revenus depuis 2021. Besoins "
                 "identifies: rattraper les declarations fiscales pour acceder au "
                 "credit pour la TPS/TVH, etablir un budget mensuel, negocier avec "
                 "les creanciers. Jean-Pierre est preoccupe mais cooperatif. "
                 "Prochaines etapes: rassembler les documents fiscaux pour 2021-2024, "
                 "examiner le budget mensuel avec les revenus actuels.",
                 "", None, ""),
                (t_coaching, 28,
                 "Reviewed Jean-Pierre's budget mensuel — income $1,800/month "
                 "(pension plus GIS), expenses $1,720. Very tight margin. Discussed "
                 "options for credit card debt: contacted creditors for hardship "
                 "reduction on interest rate. One card agreed to reduce from 19.99% "
                 "to 9.9%. Gathered tax documents for 2021-2023. Will file through "
                 "CVITP at next session. Jean-Pierre reports feeling hopeful about "
                 "getting back taxes done. Reviewed eligibility for Ontario Trillium "
                 "Benefit. Action items: bring remaining T-slips, research debt "
                 "consolidation.",
                 "engaged", 4, "worker_observed"),
                (t_coaching, 63,
                 "Filed 2021 and 2022 declarations de revenus through CVITP. "
                 "Jean-Pierre eligible for approximately $1,200 in retroactive "
                 "GST/HST credits. Discussed using portion for debt repayment. "
                 "Budget adherence improving — Jean-Pierre tracking expenses in "
                 "notebook. Credit card debt reduced to $3,400 through regular "
                 "payments and interest rate reduction. Explored OTB eligibility — "
                 "will be assessed once all returns filed. Son helping with online "
                 "banking setup. Next steps: file 2023-2024 returns, review GIS "
                 "renewal paperwork.",
                 "engaged", 4, "worker_observed"),
                (t_coaching, 98,
                 "All four years of tax returns now filed. CRA processing 2023-2024. "
                 "Retroactive GST/HST credit of $1,400 received — $800 applied to "
                 "credit card debt, $200 to emergency fund, $400 for son's school "
                 "supplies. Credit card debt now $2,600. Jean-Pierre reports sleeping "
                 "better and feeling more in control. Budget suivi consistently for "
                 "two months. Discussed Ontario Energy and Property Tax Credit — "
                 "expects additional $900 annually. Reviewed importance of filing "
                 "on time going forward to maintain benefit eligibility.",
                 "valuing", 4, "worker_observed"),
                (t_tax, 42,
                 "CVITP clinic session: filed Jean-Pierre's 2021 and 2022 tax "
                 "returns. Documents collected: T4A(P), T4A(OAS), GIS statements, "
                 "T5 bank interest, rent receipts for Ontario Trillium Benefit. "
                 "Applied for retroactive GST/HST credit for both years. Explained "
                 "CRA My Account portal — will help Jean-Pierre set up online "
                 "access at next visit. Follow-up: return for 2023-2024 filing "
                 "once NOAs received.",
                 "", None, ""),
            ],

            # --- PC-003 Priya (marcus) — 5 notes ---
            "PC-003": [
                (t_intake, 0,
                 "Priya referred by settlement agency. Software engineer from India, "
                 "in Canada 8 months. Professional credentials not yet recognized — "
                 "working part-time at retail store earning $16.55/hour. Husband "
                 "employed as warehouse worker. Household income approximately "
                 "$3,200/month. Carrying $8,000 in immigration-related debt (loans "
                 "for IRCC fees and settlement costs). Has bank account but "
                 "unfamiliar with Canadian credit system. Needs: build Canadian "
                 "credit history, create household budget, file first Canadian tax "
                 "return, explore credential recognition pathways. Priya is highly "
                 "organized and motivated. Next steps: apply for secured credit "
                 "card, begin budget worksheet, gather tax documents.",
                 "", None, ""),
                (t_coaching, 25,
                 "Reviewed household budget — income $3,200, expenses $2,900. "
                 "Priya applied for secured credit card with $500 deposit at TD. "
                 "Discussed Canadian credit scoring: payment history, utilization, "
                 "length of history. Set up automatic minimum payments plus extra "
                 "on credit card. Explored WES credential evaluation — $300 fee. "
                 "Discussed OSAP eligibility for bridging program at Humber "
                 "College. Action items: request transcripts from Indian "
                 "university, contact WES, set up CRA My Account.",
                 "engaged", 4, "worker_observed"),
                (t_coaching, 56,
                 "Priya completed WES application. Transcripts received from India. "
                 "Credit card used responsibly — balance paid in full monthly. "
                 "Credit score now 640 after two months. Filed first Canadian tax "
                 "return — refund of $800 expected due to tuition credits from "
                 "bridging program exploration. Budget tracking going well. "
                 "Household savings up to $500 in emergency fund. Discussed RESP "
                 "for daughter's education — eligible for Canada Learning Bond. "
                 "Priya reports feeling more confident navigating Canadian "
                 "financial systems.",
                 "engaged", 5, "worker_observed"),
                (t_coaching, 91,
                 "WES evaluation received — credentials recognized as equivalent "
                 "to Canadian bachelor's degree. Priya enrolled in 12-week IT "
                 "bridging program at Humber. Secured credit card upgraded to "
                 "regular card with $2,000 limit. Credit score at 680. Immigration "
                 "debt reduced to $5,500 through regular payments. Household now "
                 "saving $200/month. Opened RESP for daughter — $500 initial "
                 "deposit plus $50/month. CESG grant of $100 received. Discussed "
                 "networking strategies for Canadian tech job market.",
                 "valuing", 5, "worker_observed"),
                (t_coaching, 130,
                 "Priya completed bridging program. Secured junior developer "
                 "position at $55,000/year starting next month. Household income "
                 "will increase significantly. Credit score now 710. Immigration "
                 "debt at $4,200. Emergency fund at $1,200. RESP balance $800 "
                 "with CESG. Discussed workplace benefits enrollment, RRSP "
                 "contribution strategy for tax efficiency, and accelerated debt "
                 "repayment plan with new income. Priya is thriving and plans to "
                 "continue coaching quarterly for long-term financial planning.",
                 "valuing", 5, "worker_observed"),
            ],

            # --- PC-004 Kwame (aminata) — 5 notes ---
            "PC-004": [
                (t_intake, 0,
                 "Kwame referred by Skills for Change. Electrician from Ghana, in "
                 "Canada 14 months. Trade certification not yet recognized by "
                 "Ontario College of Trades. Currently working as general labourer "
                 "at $18/hour. Single, renting room in shared house. Income "
                 "$2,400/month, expenses $1,900. Has $1,500 in savings but no "
                 "Canadian credit history. Needs: navigate trade certification "
                 "process, build credit, file Canadian taxes, explore OSAP for "
                 "upgrading courses. Kwame is determined and resourceful. Next "
                 "steps: contact Ontario College of Trades, apply for secured "
                 "credit card, gather employment documents for tax filing.",
                 "", None, ""),
                (t_coaching, 21,
                 "Contacted Ontario College of Trades — Kwame needs to complete a "
                 "gap assessment and upgrading courses. Estimated 6-month process. "
                 "Applied for secured credit card at RBC with $300 deposit. Budget "
                 "reviewed — identified $200/month that can go toward savings. Set "
                 "up automatic transfer to TFSA. Discussed OSAP eligibility for "
                 "upgrading courses at George Brown College. Kwame feeling positive "
                 "about the pathway. Action items: complete OSAP application, "
                 "register for gap assessment, gather tax documents.",
                 "engaged", 4, "worker_observed"),
                (t_coaching, 56,
                 "OSAP application approved — Kwame enrolled in electrical "
                 "upgrading at George Brown starting January. Gap assessment "
                 "completed — needs three courses plus supervised hours. Secured "
                 "credit card active for 6 weeks with perfect payment history. "
                 "Budget adherence strong. Savings at $1,900. Discussed Ontario "
                 "Bridging Participant Assistance Program for additional funding. "
                 "Kwame reports feeling more settled and hopeful about career "
                 "prospects in Canada.",
                 "engaged", 4, "worker_observed"),
                (t_coaching, 91,
                 "Kwame completed first upgrading course with high marks. Employer "
                 "agreed to provide supervised hours counting toward certification. "
                 "Credit score established at 660. TFSA balance $2,800. Filed 2024 "
                 "taxes — refund of $600 expected from tuition credits. Discussed "
                 "apprenticeship wage rates once certified — significant income "
                 "increase expected. Kwame mentoring another Ghanaian newcomer at "
                 "Skills for Change. He reports strong sense of community support.",
                 "valuing", 5, "worker_observed"),
                (t_tax, 35,
                 "CVITP clinic session for Kwame. Filed 2024 Canadian tax return "
                 "— first filing in Canada. Documents: T4 from employer, rent "
                 "receipts, TTC Metropass receipts, tuition receipt from George "
                 "Brown. Applied for GST/HST credit. Explained importance of "
                 "annual filing for maintaining benefit eligibility. Follow-up: "
                 "will assist with OSAP income verification once NOA received.",
                 "", None, ""),
            ],

            # --- PC-005 Lin (marcus) — 4 notes ---
            "PC-005": [
                (t_intake, 0,
                 "Lin referred by public library newcomer program. Retired teacher "
                 "from China, in Canada 3 years. Sponsored by adult daughter. "
                 "Receives no income — daughter provides $800/month support. Not "
                 "eligible for OAS/GIS until 10-year residency requirement met. "
                 "Has never filed Canadian taxes. No credit history. Banking with "
                 "major bank at $16.95/month fees. Needs: file taxes for 2022-2024 "
                 "to establish CRA profile, switch to no-fee senior bank account, "
                 "explore community programs for low-income seniors. Lin is quiet "
                 "but attentive, communicates through daughter who interprets. "
                 "Next steps: gather available tax documents, schedule bank "
                 "appointment.",
                 "", None, ""),
                (t_coaching, 28,
                 "Helped Lin switch to no-fee senior account at same bank — saving "
                 "$203/year in fees. Set up daughter as joint account holder for "
                 "emergencies. Reviewed tax situation: Lin has had no employment "
                 "income but should file nil returns to establish CRA profile and "
                 "build toward GIS eligibility. Discussed Ontario Senior "
                 "Homeowners Property Tax Grant and Low-Income Seniors dental "
                 "program. Action items: bring T5 slips if any, schedule CVITP "
                 "appointment, apply for Ontario Drug Benefit program.",
                 "guarded", 3, "worker_observed"),
                (t_coaching, 70,
                 "Filed nil returns for 2022-2024 through CVITP. CRA My Account "
                 "set up with daughter's help. Applied for Ontario Drug Benefit — "
                 "approved. Lin reports feeling relieved to have tax situation "
                 "sorted. Discussed planning for OAS/GIS application in 2029. "
                 "Explored community centre programs: ESL classes, tai chi, "
                 "knitting group. Lin interested in ESL and tai chi. Daughter "
                 "reports Lin seems less isolated since attending library programs.",
                 "engaged", 4, "worker_observed"),
                (t_tax, 42,
                 "CVITP clinic: filed Lin's 2022, 2023, and 2024 nil returns. No "
                 "income to report but establishing CRA filing history for future "
                 "GIS eligibility. Provided documentation checklist for daughter: "
                 "keep records of financial support, medical expenses, any T5 bank "
                 "interest. Set up direct deposit for any future CRA payments. "
                 "Follow-up: annual tax filing reminder set for March 2027.",
                 "", None, ""),
            ],

            # --- PC-006 Sofia (aminata) — 4 notes ---
            "PC-006": [
                (t_intake, 0,
                 "Sofia referred by women's shelter outreach worker. Age 32, "
                 "single mother of three children (ages 2, 5, 7). Recently left "
                 "abusive relationship. Currently in transitional housing, "
                 "receiving Ontario Works $1,500/month plus Canada Child Benefit. "
                 "No bank account in her own name — previous accounts controlled "
                 "by ex-partner. Credit score damaged by debts opened in her name "
                 "without consent. Needs: open safe bank account, dispute "
                 "unauthorized debts, file taxes to maximize CCB, connect with "
                 "legal aid for family law. Sofia is understandably anxious but "
                 "determined to build independence. Next steps: accompany to bank "
                 "to open account, contact Equifax for credit report, refer to "
                 "legal aid.",
                 "", None, ""),
                (t_coaching, 28,
                 "Opened no-fee bank account at credit union with safety features "
                 "(no joint access, paperless statements). Direct deposit set up "
                 "for OW and CCB. Obtained credit report — three accounts opened "
                 "by ex-partner totalling $6,800. Filed fraud dispute with Equifax "
                 "and TransUnion. Connected Sofia with legal aid — family law "
                 "certificate issued. Began basic budget: income $2,300 (OW + CCB), "
                 "rent $900 (subsidized), expenses $1,800. Discussed Ontario Works "
                 "childcare subsidy for job readiness. Sofia reports feeling safer "
                 "with independent banking.",
                 "guarded", 3, "worker_observed"),
                (t_coaching, 63,
                 "Credit dispute resolved — two of three fraudulent accounts "
                 "removed. Third under review. Sofia's credit score improving. OW "
                 "caseworker approved childcare subsidy — eldest two children in "
                 "after-school program. Sofia enrolled in job readiness workshop "
                 "at community centre. Budget tracking started with envelope "
                 "system. Filed 2024 taxes — significant CCB adjustment expected "
                 "with single-parent status. Discussed safety planning around "
                 "financial documents. Sofia is gaining confidence and says she "
                 "feels like herself again.",
                 "engaged", 4, "worker_observed"),
                (t_crisis, 52,
                 "Sofia called in distress — received eviction notice from "
                 "transitional housing as maximum stay period approaching. "
                 "Immediate actions: contacted housing worker to confirm timeline "
                 "(60 days). Referred to Rent Bank for last-month deposit "
                 "assistance. Connected with Housing Connections for social "
                 "housing waitlist application. Explored rent supplement programs "
                 "through OW. Called shelter outreach to confirm safety — no "
                 "contact from ex-partner. Sofia calmed after plan was "
                 "established. Follow-up: housing search appointment scheduled "
                 "for next week, will review apartment listings together at "
                 "next coaching session.",
                 "", None, ""),
            ],

            # --- PC-007 Tyler (marcus) — 4 notes ---
            "PC-007": [
                (t_intake, 0,
                 "Tyler self-referred after seeing program poster at community "
                 "health centre. Age 24, First Nations (Algonquin), grew up on "
                 "Kitigan Zibi reserve. Moved to Ottawa 2 years ago for work. "
                 "Currently employed part-time at construction company, $19/hour. "
                 "Income approximately $2,000/month but irregular hours. Has "
                 "status card but unsure about tax exemption eligibility for "
                 "off-reserve income. Bank account at major bank with $14.95/month "
                 "fees. No credit history. Needs: clarify tax status, switch to "
                 "no-fee account, build credit, create budget for irregular "
                 "income. Tyler is friendly and open but has limited experience "
                 "with financial institutions. Next steps: review tax status, "
                 "schedule bank switch, begin income tracking.",
                 "", None, ""),
                (t_coaching, 25,
                 "Clarified Tyler's tax situation: off-reserve employment income "
                 "is taxable. Discussed T4 reporting. Helped switch to no-fee "
                 "chequing account — saving $180/year. Applied for secured credit "
                 "card. Created variable-income budget using average of last 3 "
                 "months. Discussed setting aside 15% of each paycheque for "
                 "taxes/savings in separate account. Tyler reports understanding "
                 "his finances better now. Action items: start income tracking "
                 "spreadsheet, bring tax documents for 2024 filing, look into "
                 "status card renewal.",
                 "engaged", 3, "worker_observed"),
                (t_coaching, 63,
                 "Tyler tracking income consistently for 5 weeks. Average monthly "
                 "income confirmed at $2,100. Savings account has $400 — building "
                 "toward $1,000 emergency fund goal. Credit card used for small "
                 "purchases and paid in full. Filed 2024 taxes — small refund "
                 "expected. Status card renewal application submitted. Discussed "
                 "apprenticeship opportunities through employer — Tyler interested "
                 "in carpentry certification. Explored union membership benefits. "
                 "Tyler seems more engaged with his financial future.",
                 "engaged", 4, "worker_observed"),
                (t_tax, 35,
                 "CVITP clinic: filed Tyler's 2024 tax return. Documents: T4 "
                 "from construction employer, rent receipts, bus pass receipts. "
                 "Clarified that off-reserve T4 income is fully taxable. Refund "
                 "of approximately $350 expected. Set up CRA direct deposit. "
                 "Discussed importance of quarterly tax installments if Tyler "
                 "moves to self-employment. Follow-up: assist with status card "
                 "documentation once renewed.",
                 "", None, ""),
            ],

            # --- PC-008 Olga (aminata) — 4 notes ---
            "PC-008": [
                (t_intake, 0,
                 "Olga referred by settlement agency. Age 67, recently arrived "
                 "from Ukraine under CUAET program. Retired school principal. "
                 "Receiving temporary financial assistance through resettlement "
                 "program — $1,200/month. Lives with niece's family. No Canadian "
                 "banking, no tax filings, no credit history. Pension from "
                 "Ukraine ($200 USD/month equivalent) deposited to Ukrainian "
                 "account — unclear if accessible. Needs: open Canadian bank "
                 "account, file taxes, explore social assistance eligibility, "
                 "navigate OAS/GIS timeline. Olga speaks limited English — niece "
                 "interprets. She seems overwhelmed but cooperative. Next steps: "
                 "bank account opening, document gathering for tax filing, CUAET "
                 "benefit timeline review.",
                 "", None, ""),
                (t_coaching, 35,
                 "Opened no-fee newcomer account at RBC with niece as translator. "
                 "Set up direct deposit for resettlement assistance. Reviewed "
                 "CUAET financial support timeline — benefits continue for 12 "
                 "months. Discussed OAS/GIS eligibility: 10-year residency "
                 "requirement, but may qualify earlier under social security "
                 "agreement with Ukraine. Contacted Service Canada for assessment. "
                 "Created simple budget: income $1,200 (resettlement) + $200 "
                 "(Ukraine pension via wire transfer — set up monthly). Olga "
                 "reports feeling safer with Canadian bank account. Niece helping "
                 "with online banking.",
                 "guarded", 3, "worker_observed"),
                (t_tax, 42,
                 "CVITP clinic: filed Olga's 2024 tax return — first Canadian "
                 "filing. Reported resettlement assistance income and Ukrainian "
                 "pension (converted to CAD). Applied for GST/HST credit. "
                 "Explained foreign income reporting requirements. Documents: "
                 "CUAET financial statements, bank records showing Ukrainian "
                 "pension transfers, SIN confirmation. Follow-up: await NOA, "
                 "assist with OTB application if eligible.",
                 "", None, ""),
                (t_tax, 70,
                 "Second CVITP visit: NOA received confirming 2024 return "
                 "processed. GST/HST credit approved — $496 annually. Assisted "
                 "Olga with Ontario Trillium Benefit application. Reviewed "
                 "Service Canada response on OAS eligibility under Canada-Ukraine "
                 "social security agreement: Olga may count Ukrainian pension "
                 "years toward residency requirement. Submitted additional "
                 "documentation. Olga expressed gratitude — says the tax process "
                 "was much simpler than she expected. Follow-up: OAS decision "
                 "expected in 8-10 weeks.",
                 "", None, ""),
            ],

            # --- PC-009 Daniel (marcus) — 4 notes ---
            "PC-009": [
                (t_intake, 0,
                 "Daniel self-referred through agency website. Age 41, "
                 "Canadian-born. Recently divorced, adjusting to single-income "
                 "household. Works as forklift operator, $22/hour full-time. "
                 "Income $3,500/month. Carries $12,000 in credit card debt "
                 "accumulated during separation. Pays $800/month child support "
                 "for two children. Renting bachelor apartment at $1,200/month. "
                 "Has bank account and credit cards but feels overwhelmed by "
                 "debt. Needs: debt management strategy, post-divorce budget, "
                 "explore credit counselling options, file taxes reflecting new "
                 "marital status. Daniel is stressed but determined. Next steps: "
                 "complete income/expense worksheet, obtain credit report, "
                 "research debt consolidation.",
                 "", None, ""),
                (t_coaching, 21,
                 "Completed detailed budget: income $3,500, fixed expenses "
                 "$2,800 (rent $1,200, child support $800, car $400, insurance "
                 "$200, phone $80, food $120). Discretionary spending needs "
                 "work. Credit report obtained — score 580, three cards maxed. "
                 "Discussed options: debt consolidation loan vs. consumer "
                 "proposal vs. avalanche method. Daniel prefers to avoid formal "
                 "insolvency. Applied for consolidation loan at 9.9% — awaiting "
                 "decision. Set up minimum auto-payments on all cards to avoid "
                 "late fees. Action items: track all spending for 2 weeks, "
                 "research food bank options to reduce grocery costs.",
                 "engaged", 3, "worker_observed"),
                (t_coaching, 56,
                 "Consolidation loan approved at $12,000 / 9.9% / 48 months — "
                 "payment $305/month vs. previous $450 minimums across three "
                 "cards. Cards cut up. Budget adjusted — now has $145/month "
                 "freed up. Daniel tracking spending consistently. Found savings "
                 "on groceries through food bank and discount stores. Discussed "
                 "employer benefits: Daniel has RRSP matching he wasn't using. "
                 "Enrolled in 3% match — free money. Filed taxes — refund of "
                 "$1,100 expected. Daniel reports feeling less panicked about "
                 "finances. Kids spending every other weekend — budgeted "
                 "$100/month for activities with them.",
                 "engaged", 4, "worker_observed"),
                (t_coaching, 84,
                 "Tax refund received — $800 to consolidation loan principal, "
                 "$300 to emergency fund. Consolidation loan balance now $10,400. "
                 "Budget adherence consistent for 6 weeks. Credit score improved "
                 "to 620. RRSP contributions accumulating with employer match. "
                 "Daniel reports relationship with kids is better now that "
                 "financial stress is reduced. Discussed long-term goals: wants "
                 "to save for kids' education, possibly buy a condo in 3-5 "
                 "years. Created 5-year financial roadmap. Daniel feeling "
                 "optimistic and committed to the plan.",
                 "valuing", 4, "worker_observed"),
            ],

            # --- PC-010 Hana (aminata) — 3 notes ---
            "PC-010": [
                (t_intake, 0,
                 "Hana referred by mosque community worker. Age 45, arrived from "
                 "Turkey 6 months ago with husband and three children. Husband "
                 "works as cook, $17/hour. Hana not working — limited English, "
                 "caring for youngest child (age 3). Household income "
                 "$2,700/month. Renting 2-bedroom apartment at $1,400/month — "
                 "overcrowded but affordable. No Canadian tax filings, no credit "
                 "history. Bank account opened at arrival but paying high fees. "
                 "Needs: file taxes to access CCB and GST/HST credits, switch to "
                 "lower-fee account, create budget, explore childcare options so "
                 "Hana can attend English classes. Hana is warm and engaged "
                 "despite language barrier — husband interprets. Next steps: "
                 "gather tax documents, review bank fees.",
                 "", None, ""),
                (t_coaching, 28,
                 "Switched family to no-fee account — saving $190/year. Set up "
                 "direct deposit for husband's pay. Filed 2024 taxes for both "
                 "Hana and husband — significant CCB entitlement expected for "
                 "three children ($1,400/month estimated). GST/HST credit also "
                 "anticipated. Created household budget reflecting expected CCB "
                 "income. Discussed Ontario childcare subsidy — Hana eligible "
                 "for fee reduction at licensed daycare. Applied for subsidy. "
                 "Explored LINC classes near home — found program with onsite "
                 "childcare. Hana excited about possibility of attending English "
                 "classes. Action items: follow up on CCB processing, complete "
                 "daycare subsidy paperwork.",
                 "engaged", 4, "worker_observed"),
                (t_coaching, 63,
                 "CCB payments started — $1,400/month. Household income now "
                 "$4,100. GST/HST credit of $720/year approved. Budget updated "
                 "and family is now meeting all basic needs. Childcare subsidy "
                 "approved — youngest in licensed daycare 3 days/week. Hana "
                 "enrolled in LINC Level 2 classes. Discussed opening RESP for "
                 "children — $50/month per child to maximize CESG. Opened TFSA "
                 "with $100 initial deposit. Hana reports feeling more settled "
                 "and says the CCB has made an enormous difference for the "
                 "family. Husband exploring second job options for evenings.",
                 "engaged", 4, "worker_observed"),
            ],

            # --- PC-011 James (marcus) — 1 note ---
            "PC-011": [
                (t_intake, 0,
                 "James referred by Salvation Army shelter. Age 29, "
                 "Canadian-born, currently homeless and staying at shelter. "
                 "Recently aged out of Children's Aid care at 21 but experienced "
                 "housing instability since. Intermittent employment — last "
                 "worked 4 months ago at warehouse. Receiving Ontario Works "
                 "$733/month. No bank account — uses shelter address for mail. "
                 "Has not filed taxes in 3 years. Possible ODSP eligibility due "
                 "to mental health concerns — has diagnosis of anxiety and "
                 "depression. Needs: open bank account, file back taxes, explore "
                 "ODSP application, connect with mental health supports, "
                 "housing-first approach. James is quiet and guarded but agreed "
                 "to work with coach. Next steps: accompany to bank for "
                 "ID-based account opening, gather available documents.",
                 "", None, ""),
            ],

            # --- PC-012 Marie-Claire (aminata) — 1 note ---
            "PC-012": [
                (t_intake, 0,
                 "Marie-Claire referee par une amie qui a participe au "
                 "programme. Agee de 52 ans, originaire de la Republique "
                 "democratique du Congo, au Canada depuis 4 ans. Travaille "
                 "comme preposee aux beneficiaires dans un centre de soins de "
                 "longue duree, $18.50/heure. Revenu mensuel $2,500. "
                 "Monoparentale avec deux enfants adultes. A produit ses "
                 "declarations de revenus chaque annee mais n'a jamais verifie "
                 "si elle recoit tous les credits auxquels elle a droit. Pas "
                 "de REER ni de CELI. Credit score inconnu. Besoins: revision "
                 "complete des prestations, strategie d'epargne, verification "
                 "du dossier de credit, planification de la retraite. "
                 "Marie-Claire est energique et motivee. Prochaines etapes: "
                 "obtenir le rapport de credit, examiner les avis de cotisation "
                 "recents, evaluer l'admissibilite aux prestations non reclamees.",
                 "", None, ""),
            ],
        }

        # ==============================================================
        # Create all notes
        # ==============================================================

        # Coach mapping by record_id (from PARTICIPANTS data)
        coach_map = {}
        for pdata in PARTICIPANTS:
            if pdata["coach"] == "marcus@demo.konote.ca":
                coach_map[pdata["record_id"]] = marcus
            else:
                coach_map[pdata["record_id"]] = aminata

        total_created = 0
        suggestion_count = 0

        # Build lookup: (record_id, note_index) -> (suggestion_text, priority)
        suggestion_lookup = {}
        for rid, sug_list in PARTICIPANT_SUGGESTIONS.items():
            for note_idx, text, priority in sug_list:
                suggestion_lookup[(rid, note_idx)] = (text, priority)

        # Track notes that have suggestions for theme linking later
        self._notes_with_suggestions = []

        for record_id, note_list in NOTES.items():
            client = p[record_id]
            author = coach_map[record_id]
            intake_date = intake[record_id]

            for note_idx, (template, days_offset, summary_text,
                           engagement, alliance, alliance_rater) in enumerate(
                               note_list):

                note_date = intake_date + timedelta(days=days_offset)
                note_dt = dt(note_date, hour=10)

                note = ProgressNote(
                    client_file=client,
                    note_type="full",
                    interaction_type=template.default_interaction_type,
                    outcome="reached",
                    status="default",
                    template=template,
                    author=author,
                    author_program=program,
                )

                # Set encrypted summary via property
                note.summary = summary_text

                # Set program-specific participant suggestion if designated
                sug = suggestion_lookup.get((record_id, note_idx))
                if sug:
                    note.participant_suggestion = sug[0]
                    note.suggestion_priority = sug[1]
                    suggestion_count += 1

                # Set engagement observation on coaching notes
                if engagement:
                    note.engagement_observation = engagement

                # Set alliance rating on coaching notes where specified
                if alliance is not None:
                    note.alliance_rating = alliance
                    note.alliance_rater = alliance_rater

                note.save()

                # Track notes with suggestions for theme linking
                if sug:
                    self._notes_with_suggestions.append(note)

                # Backdate created_at and set backdate field
                ProgressNote.objects.filter(pk=note.pk).update(
                    created_at=note_dt,
                    backdate=note_dt,
                )

                total_created += 1

        self.stdout.write(
            f"  Progress notes: {total_created} created across "
            f"12 participants ({suggestion_count} with suggestions)."
        )

    def create_suggestion_themes(self, staff, program):
        """Create suggestion themes and link them to notes via keyword matching.

        Uses SUGGESTION_THEMES definitions with comma-separated keywords.
        Each theme is linked only to notes whose participant_suggestion text
        contains at least one keyword. No blind fallback — a theme with zero
        linked notes is better than a theme with irrelevant ones.
        """
        if SuggestionTheme.objects.filter(program=program).exists():
            self.stdout.write("  Suggestion themes: already exist — skipping.")
            return

        sara = staff["sara@demo.konote.ca"]
        notes = getattr(self, "_notes_with_suggestions", [])

        themes_created = 0
        links_created = 0

        for name, description, keywords_str, priority in SUGGESTION_THEMES:
            theme = SuggestionTheme.objects.create(
                program=program,
                name=name,
                description=description,
                keywords=keywords_str,
                priority=priority,
                status="open",
                source="manual",
                created_by=sara,
            )
            themes_created += 1

            # Keyword matching — link notes whose suggestion text matches
            keywords = [k.strip().lower() for k in keywords_str.split(",") if k.strip()]
            for note in notes:
                suggestion_text = (note.participant_suggestion or "").lower()
                if any(kw in suggestion_text for kw in keywords):
                    SuggestionLink.objects.create(
                        theme=theme,
                        progress_note=note,
                        auto_linked=True,
                        linked_by=sara,
                    )
                    links_created += 1

        self.stdout.write(
            f"  Suggestion themes: {themes_created} themes, "
            f"{links_created} links created."
        )

    def create_metrics(self, staff, program, participants):
        """Create metric definitions and trend data.

        Creates ProgressNote objects (if not already present from create_notes),
        links them to existing PlanTargets via ProgressNoteTarget, and records
        MetricValue entries with realistic financial coaching trajectories.
        """

        # ------------------------------------------------------------------
        # Built-in metric definitions — look up or create
        # ------------------------------------------------------------------
        BUILTIN_METRICS = [
            {
                "name": "Goal Progress (1-10)",
                "category": "general",
                "min_value": 1,
                "max_value": 10,
                "unit": "score",
                "definition": "Client's self-assessed progress toward their stated goal. 1 = no progress, 10 = goal achieved.",
            },
            {
                "name": "How are you feeling today?",
                "category": "general",
                "min_value": 1,
                "max_value": 5,
                "unit": "score",
                "definition": "Simple wellbeing check-in at each session. 1 = not great at all, 5 = really good.",
            },
            {
                "name": "Since we last met, how are things going?",
                "category": "general",
                "min_value": 1,
                "max_value": 5,
                "unit": "score",
                "definition": "Change since previous session. 1 = much harder, 5 = much better.",
            },
            {
                "name": "Confidence",
                "category": "general",
                "min_value": 1,
                "max_value": 10,
                "unit": "score",
                "definition": "Self-reported confidence level. 1 = no confidence, 10 = fully confident.",
            },
            {
                "name": "Progress",
                "category": "general",
                "min_value": 1,
                "max_value": 10,
                "unit": "score",
                "definition": "Overall progress assessment. 1 = no progress, 10 = goal achieved.",
            },
            {
                "name": "Wellbeing",
                "category": "general",
                "min_value": 1,
                "max_value": 10,
                "unit": "score",
                "definition": "Overall wellbeing self-assessment. 1 = very poor, 10 = excellent.",
            },
            {
                "name": "Confidence navigating services",
                "category": "general",
                "min_value": 1,
                "max_value": 5,
                "unit": "score",
                "definition": "How confident are you accessing community services on your own? 1 = not confident, 5 = very confident.",
            },
            {
                "name": "Employment Status",
                "category": "employment",
                "min_value": 1,
                "max_value": 5,
                "unit": "status",
                "definition": "Current employment status. 1 = unemployed, 5 = full-time stable.",
            },
            {
                "name": "Housing Stability Index",
                "category": "housing",
                "min_value": 1,
                "max_value": 5,
                "unit": "score",
                "definition": "Composite measure of housing stability. 1 = homeless/crisis, 5 = stable long-term housing.",
            },
            {
                "name": "Job Readiness Score",
                "category": "employment",
                "min_value": 1,
                "max_value": 5,
                "unit": "score",
                "definition": "Assessment of employment readiness. 1 = significant barriers, 5 = job-ready.",
            },
            {
                "name": "Life Skills Assessment",
                "category": "general",
                "min_value": 1,
                "max_value": 5,
                "unit": "score",
                "definition": "Composite life skills score. 1 = very limited, 5 = independent.",
            },
            {
                "name": "Social Support Network",
                "category": "general",
                "min_value": 1,
                "max_value": 5,
                "unit": "score",
                "definition": "Size and quality of support network. 1 = isolated, 5 = strong diverse network.",
            },
        ]

        builtin = {}
        for spec in BUILTIN_METRICS:
            obj = MetricDefinition.objects.filter(name=spec["name"]).first()
            if not obj:
                obj = MetricDefinition.objects.create(
                    name=spec["name"],
                    definition=spec["definition"],
                    category=spec["category"],
                    is_library=True,
                    is_enabled=True,
                    min_value=spec["min_value"],
                    max_value=spec["max_value"],
                    unit=spec["unit"],
                    metric_type="scale",
                    higher_is_better=True,
                )
            builtin[spec["name"]] = obj

        # ------------------------------------------------------------------
        # Coach lookup — maps record_id to staff User (note author)
        # ------------------------------------------------------------------
        coach_map = {}
        for p in PARTICIPANTS:
            coach_map[p["record_id"]] = staff.get(p["coach"])

        # ------------------------------------------------------------------
        # Per-participant metric data
        #
        # For each participant we define:
        #   - "notes": number of coaching sessions (ProgressNote objects)
        #   - "session_offsets": week offsets from intake date for each session
        #   - "metrics": dict of metric_name -> [value_per_session]
        #
        # Metrics with fewer values than sessions record values only for
        # the first N sessions (baseline metrics get 1 recording).
        # ------------------------------------------------------------------

        METRIC_DATA = {
            # PC-001 Amira — Improving trajectory
            "PC-001": {
                "notes": 3,
                "session_offsets": [0, 4, 8],
                "progress_descriptors": ["harder", "shifting", "good_place"],
                "metrics": {
                    "Goal Progress (1-10)": [3, 5, 7],
                    "How are you feeling today?": [2, 3, 4],
                    "Since we last met, how are things going?": [3, 4, 5],
                    "Confidence": [3, 5, 7],
                    "Progress": [3, 5, 7],
                    "Wellbeing": [3, 5, 7],
                    "Confidence navigating services": [2, 3, 4],
                    "Employment Status": [1],
                    "Housing Stability Index": [3],
                    "Job Readiness Score": [2],
                    "Life Skills Assessment": [2],
                    "Social Support Network": [2],
                },
            },
            # PC-002 Jean-Pierre — Stable trajectory
            "PC-002": {
                "notes": 3,
                "session_offsets": [0, 3, 7],
                "progress_descriptors": ["holding", "holding", "shifting"],
                "metrics": {
                    "Goal Progress (1-10)": [6, 6, 7],
                    "How are you feeling today?": [3, 3, 4],
                    "Since we last met, how are things going?": [3, 3, 4],
                    "Confidence": [7, 7, 7],
                    "Progress": [6, 6, 7],
                    "Wellbeing": [6, 6, 7],
                    "Employment Status": [2],
                    "Housing Stability Index": [4],
                    "Job Readiness Score": [3],
                    "Life Skills Assessment": [3],
                    "Social Support Network": [3],
                },
            },
            # PC-003 Priya — Credit recovery trajectory
            "PC-003": {
                "notes": 3,
                "session_offsets": [0, 3, 7],
                "progress_descriptors": ["harder", "shifting", "good_place"],
                "metrics": {
                    "Goal Progress (1-10)": [4, 6, 7],
                    "How are you feeling today?": [3, 4, 4],
                    "Since we last met, how are things going?": [3, 4, 5],
                    "Confidence": [4, 6, 8],
                    "Progress": [4, 6, 7],
                    "Wellbeing": [4, 6, 7],
                    "Employment Status": [3],
                    "Housing Stability Index": [4],
                    "Job Readiness Score": [4],
                    "Life Skills Assessment": [3],
                    "Social Support Network": [3],
                },
            },
            # PC-004 Kwame — Income growth trajectory
            "PC-004": {
                "notes": 3,
                "session_offsets": [0, 4, 9],
                "progress_descriptors": ["harder", "shifting", "shifting"],
                "metrics": {
                    "Goal Progress (1-10)": [3, 5, 7],
                    "How are you feeling today?": [2, 3, 4],
                    "Since we last met, how are things going?": [3, 4, 4],
                    "Confidence": [4, 6, 7],
                    "Progress": [3, 5, 7],
                    "Wellbeing": [4, 5, 7],
                    "Employment Status": [4],
                    "Housing Stability Index": [3],
                    "Job Readiness Score": [3],
                    "Life Skills Assessment": [3],
                    "Social Support Network": [3],
                },
            },
            # PC-005 Lin — Benefits access trajectory
            "PC-005": {
                "notes": 3,
                "session_offsets": [0, 3, 6],
                "progress_descriptors": ["holding", "shifting", "good_place"],
                "metrics": {
                    "Goal Progress (1-10)": [5, 7, 8],
                    "How are you feeling today?": [3, 4, 4],
                    "Since we last met, how are things going?": [3, 4, 5],
                    "Confidence": [5, 6, 7],
                    "Progress": [5, 7, 8],
                    "Wellbeing": [5, 6, 7],
                    "Confidence navigating services": [2, 3, 4],
                    "Employment Status": [5],
                    "Housing Stability Index": [4],
                    "Job Readiness Score": [2],
                    "Life Skills Assessment": [3],
                    "Social Support Network": [3],
                },
            },
            # PC-006 Sofia — Slow start trajectory
            "PC-006": {
                "notes": 2,
                "session_offsets": [0, 4],
                "progress_descriptors": ["harder", "holding"],
                "metrics": {
                    "Goal Progress (1-10)": [3, 4],
                    "How are you feeling today?": [2, 3],
                    "Confidence": [3, 4],
                    "Progress": [3, 4],
                    "Wellbeing": [3, 4],
                    "Employment Status": [3],
                    "Housing Stability Index": [3],
                    "Job Readiness Score": [2],
                    "Life Skills Assessment": [2],
                    "Social Support Network": [2],
                },
            },
            # PC-007 Tyler — Building foundation trajectory
            "PC-007": {
                "notes": 2,
                "session_offsets": [0, 4],
                "progress_descriptors": ["harder", "shifting"],
                "metrics": {
                    "Goal Progress (1-10)": [2, 5],
                    "How are you feeling today?": [2, 3],
                    "Confidence": [3, 5],
                    "Progress": [2, 5],
                    "Wellbeing": [3, 5],
                    "Confidence navigating services": [1, 3],
                    "Employment Status": [1],
                    "Housing Stability Index": [2],
                    "Job Readiness Score": [2],
                    "Life Skills Assessment": [2],
                    "Social Support Network": [2],
                },
            },
            # PC-008 Olga — Benefits recovery trajectory
            "PC-008": {
                "notes": 2,
                "session_offsets": [0, 4],
                "progress_descriptors": ["harder", "shifting"],
                "metrics": {
                    "Goal Progress (1-10)": [4, 6],
                    "How are you feeling today?": [2, 3],
                    "Confidence": [3, 5],
                    "Progress": [4, 6],
                    "Wellbeing": [3, 5],
                    "Confidence navigating services": [2, 3],
                    "Employment Status": [2],
                    "Housing Stability Index": [3],
                    "Job Readiness Score": [2],
                    "Life Skills Assessment": [3],
                    "Social Support Network": [2],
                },
            },
            # PC-009 Daniel — Debt management trajectory
            "PC-009": {
                "notes": 2,
                "session_offsets": [0, 3],
                "progress_descriptors": ["harder", "holding"],
                "metrics": {
                    "Goal Progress (1-10)": [3, 4],
                    "How are you feeling today?": [2, 3],
                    "Confidence": [4, 5],
                    "Progress": [3, 4],
                    "Wellbeing": [3, 4],
                    "Employment Status": [4],
                    "Housing Stability Index": [3],
                    "Job Readiness Score": [3],
                    "Life Skills Assessment": [3],
                    "Social Support Network": [3],
                },
            },
            # PC-010 Hana — Early baseline (1 session only)
            "PC-010": {
                "notes": 1,
                "session_offsets": [0],
                "progress_descriptors": ["harder"],
                "metrics": {
                    "Goal Progress (1-10)": [3],
                    "How are you feeling today?": [2],
                    "Confidence": [3],
                    "Progress": [3],
                    "Wellbeing": [3],
                    "Confidence navigating services": [2],
                    "Employment Status": [4],
                    "Housing Stability Index": [3],
                    "Job Readiness Score": [3],
                    "Life Skills Assessment": [3],
                    "Social Support Network": [2],
                },
            },
        }

        # ------------------------------------------------------------------
        # Create notes, link to targets, and record metric values
        # ------------------------------------------------------------------
        notes_created = 0
        pnt_created = 0
        mv_created = 0

        for record_id, spec in METRIC_DATA.items():
            client = participants.get(record_id)
            if not client:
                continue

            coach = coach_map.get(record_id)
            if not coach:
                continue

            # Find intake date for session date calculations
            intake_date = None
            for p in PARTICIPANTS:
                if p["record_id"] == record_id:
                    intake_date = p["intake_date"]
                    break
            if not intake_date:
                continue

            num_notes = spec["notes"]
            session_offsets = spec["session_offsets"]
            descriptors = spec.get("progress_descriptors", [""] * num_notes)

            # ----------------------------------------------------------
            # Step 1: Find or create ProgressNote objects for this participant
            # ----------------------------------------------------------
            existing_notes = list(
                ProgressNote.objects.filter(
                    client_file=client,
                    author_program=program,
                ).order_by("created_at")
            )

            notes = []
            for i in range(num_notes):
                session_date = timezone.make_aware(
                    timezone.datetime(
                        intake_date.year,
                        intake_date.month,
                        intake_date.day,
                        10, 0, 0,
                    )
                ) + timedelta(weeks=session_offsets[i])

                if i < len(existing_notes):
                    notes.append(existing_notes[i])
                else:
                    # Create a coaching session note
                    note = ProgressNote(
                        client_file=client,
                        note_type="full",
                        interaction_type="session",
                        status="default",
                        author=coach,
                        author_program=program,
                    )
                    note.summary = f"Coaching session {i + 1} with {client.record_id}."
                    note.save()
                    # Backdate: override created_at via update to bypass auto_now_add
                    ProgressNote.objects.filter(pk=note.pk).update(
                        created_at=session_date,
                        backdate=session_date,
                    )
                    note.refresh_from_db()
                    notes.append(note)
                    notes_created += 1

            # ----------------------------------------------------------
            # Step 2: Find existing PlanTargets for this participant
            # ----------------------------------------------------------
            plan_targets = list(
                PlanTarget.objects.filter(
                    plan_section__client_file=client,
                    plan_section__program=program,
                ).select_related("plan_section").order_by(
                    "plan_section__sort_order", "sort_order"
                )
            )

            if not plan_targets:
                # No plan targets — skip metric recording for this participant
                continue

            # ----------------------------------------------------------
            # Step 3 & 4: For each note, link to targets and record metrics
            # ----------------------------------------------------------
            active_targets = [t for t in plan_targets if t.status != "deactivated"]

            for note_idx, note in enumerate(notes):
                descriptor = descriptors[note_idx] if note_idx < len(descriptors) else ""

                # Link this note to all active plan targets
                for target_idx, target in enumerate(active_targets):
                    pnt, pnt_was_created = ProgressNoteTarget.objects.get_or_create(
                        progress_note=note,
                        plan_target=target,
                    )
                    if pnt_was_created:
                        # Set progress descriptor via update to avoid
                        # encrypted field issues on the initial save
                        if descriptor:
                            ProgressNoteTarget.objects.filter(pk=pnt.pk).update(
                                progress_descriptor=descriptor,
                            )
                        pnt_created += 1

                    # Record metric values for each built-in metric
                    for metric_name, values in spec["metrics"].items():
                        if note_idx >= len(values):
                            continue

                        metric_def = builtin.get(metric_name)
                        if not metric_def:
                            continue

                        # Goal Progress is target-specific — record on every target.
                        # All other metrics are session-level — record only on the
                        # first active target to avoid duplicates.
                        if target_idx > 0 and metric_name != "Goal Progress (1-10)":
                            continue

                        MetricValue.objects.get_or_create(
                            progress_note_target=pnt,
                            metric_def=metric_def,
                            defaults={"value": str(values[note_idx])},
                        )
                        mv_created += 1

        self.stdout.write(
            f"  Metrics: {notes_created} notes, {pnt_created} note-target links, "
            f"{mv_created} metric values created."
        )
