"""
Seed rich demo data for demo clients (DEMO-001 through DEMO-015).

Creates:
- Plans with sections and targets linked to approachable metrics
- Progress notes with metric recordings following realistic trends
- Qualitative progress data (client words, progress descriptors, engagement)
- Events (intake, follow-ups, referrals, crises)
- Alerts for clients with notable situations
- Custom field values (contact info, emergency contacts, referral sources)
- Demo groups (service, activity, project) with sessions, attendance, and highlights

This gives charts and reports meaningful data to display.

Run with: python manage.py seed_demo_data
Only runs when DEMO_MODE is enabled.
"""
import random
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.clients.models import ClientDetailValue, ClientFile, CustomFieldDefinition
from apps.events.models import Alert, Event, EventType
from apps.groups.models import (
    Group,
    GroupMembership,
    GroupSession,
    GroupSessionAttendance,
    GroupSessionHighlight,
    ProjectMilestone,
    ProjectOutcome,
)
from apps.notes.models import MetricValue, ProgressNote, ProgressNoteTarget
from apps.plans.models import (
    MetricDefinition,
    PlanSection,
    PlanTarget,
    PlanTargetMetric,
    PlanTargetRevision,
)
from apps.programs.models import Program
from seeds.demo_client_fields import CLIENT_CUSTOM_FIELDS

User = get_user_model()


# ---------------------------------------------------------------------------
# Program configuration — maps programs to workers and interaction types
# ---------------------------------------------------------------------------

PROGRAM_WORKER = {
    "Supported Employment": "demo-worker-1",
    "Housing Stability": "demo-worker-1",
    "Youth Drop-In": "demo-worker-2",
    "Newcomer Connections": "demo-worker-2",
    "Community Kitchen": "demo-worker-2",
}

# Default interaction type per program (Housing and Newcomer get varied in code)
PROGRAM_INTERACTION_TYPE = {
    "Supported Employment": "session",
    "Housing Stability": "session",
    "Youth Drop-In": "group",
    "Newcomer Connections": "session",
    "Community Kitchen": "group",
}


# ---------------------------------------------------------------------------
# Client plans — sections, targets, and metrics for each demo client
# ---------------------------------------------------------------------------

CLIENT_PLANS = {
    # =========================================================================
    # Supported Employment (Casey Worker) — DEMO-001, 002, 003
    # =========================================================================
    "DEMO-001": {
        "label": "Jordan Rivera — improving, got first interview",
        "program": "Supported Employment",
        "trend": "improving",
        "note_count": 10,
        "sections": [
            {
                "name": "Job Search",
                "targets": [
                    {
                        "name": "Build interview skills",
                        "desc": "Feel confident walking into an interview.",
                        "metrics": [
                            "Confidence in your job search",
                            "How ready do you feel for work?",
                        ],
                    },
                    {
                        "name": "Submit applications regularly",
                        "desc": "Keep momentum on applications even when it's hard.",
                        "metrics": [
                            "Job Applications (past month)",
                            "Goal Progress (1-10)",
                        ],
                    },
                ],
            },
        ],
    },
    "DEMO-002": {
        "label": "Taylor Chen — struggling, interview anxiety",
        "program": "Supported Employment",
        "trend": "struggling",
        "note_count": 10,
        "sections": [
            {
                "name": "Work Readiness",
                "targets": [
                    {
                        "name": "Feel more ready for work",
                        "desc": "Build confidence day by day.",
                        "metrics": [
                            "How ready do you feel for work?",
                            "How are you feeling today?",
                        ],
                    },
                    {
                        "name": "Build job search confidence",
                        "desc": "Get comfortable with applications and interviews.",
                        "metrics": [
                            "Confidence in your job search",
                            "Job Applications (past month)",
                        ],
                    },
                ],
            },
        ],
    },
    "DEMO-003": {
        "label": "Avery Osei — stable, working part-time, near discharge",
        "program": "Supported Employment",
        "trend": "stable",
        "note_count": 7,
        "sections": [
            {
                "name": "Work Maintenance",
                "targets": [
                    {
                        "name": "Maintain work routine",
                        "desc": "Keep showing up and doing well.",
                        "metrics": [
                            "How ready do you feel for work?",
                            "Goal Progress (1-10)",
                        ],
                    },
                ],
            },
        ],
    },
    # =========================================================================
    # Housing Stability (Casey Worker) — DEMO-004, 005, 006
    # =========================================================================
    "DEMO-004": {
        "label": "Sam Williams — crisis then improving, was in shelter",
        "program": "Housing Stability",
        "trend": "crisis_then_improving",
        "note_count": 12,
        "sections": [
            {
                "name": "Housing",
                "targets": [
                    {
                        "name": "Find a safe place to live",
                        "desc": "Move from shelter to stable housing.",
                        "metrics": [
                            "Housing Stability Index",
                            "How safe do you feel where you live?",
                        ],
                    },
                    {
                        "name": "Build income stability",
                        "desc": "Have enough to cover rent and basics.",
                        "metrics": ["Monthly Income", "Goal Progress (1-10)"],
                    },
                ],
            },
        ],
    },
    "DEMO-005": {
        "label": "Kai Dubois — struggling, eviction risk",
        "program": "Housing Stability",
        "trend": "struggling",
        "note_count": 10,
        "sections": [
            {
                "name": "Housing",
                "targets": [
                    {
                        "name": "Avoid eviction",
                        "desc": "Keep current housing or find something better.",
                        "metrics": [
                            "Housing Stability Index",
                            "How safe do you feel where you live?",
                        ],
                    },
                    {
                        "name": "Feel more settled",
                        "desc": "Reduce the constant stress about housing.",
                        "metrics": [
                            "How are you feeling today?",
                            "Goal Progress (1-10)",
                        ],
                    },
                ],
            },
        ],
    },
    "DEMO-006": {
        "label": "Jesse Morales — mixed, stabilising",
        "program": "Housing Stability",
        "trend": "mixed",
        "note_count": 9,
        "sections": [
            {
                "name": "Housing",
                "targets": [
                    {
                        "name": "Stabilise housing situation",
                        "desc": "Stop moving around and find somewhere to stay.",
                        "metrics": [
                            "Housing Stability Index",
                            "How safe do you feel where you live?",
                        ],
                    },
                    {
                        "name": "Build income",
                        "desc": "Get income to a level that covers rent.",
                        "metrics": ["Monthly Income"],
                    },
                ],
            },
        ],
    },
    # =========================================================================
    # Youth Drop-In (Noor Worker) — DEMO-007, 008, 009
    # =========================================================================
    "DEMO-007": {
        "label": "Jayden Martinez — improving, emerging leader",
        "program": "Youth Drop-In",
        "trend": "improving",
        "note_count": 9,
        "sections": [
            {
                "name": "Group Participation",
                "targets": [
                    {
                        "name": "Feel part of the group",
                        "desc": "Build friendships and feel like you belong.",
                        "metrics": [
                            "How connected do you feel to the group?",
                            "Sessions attended this month",
                        ],
                    },
                    {
                        "name": "Build life skills",
                        "desc": "Learn things that help outside the program too.",
                        "metrics": [
                            "Service Engagement",
                            "Goal Progress (1-10)",
                        ],
                    },
                ],
            },
        ],
    },
    "DEMO-008": {
        "label": "Maya Thompson — crisis then improving, was withdrawn",
        "program": "Youth Drop-In",
        "trend": "crisis_then_improving",
        "note_count": 10,
        "sections": [
            {
                "name": "Attendance & Wellbeing",
                "targets": [
                    {
                        "name": "Show up more often",
                        "desc": "Come to the program regularly, even on hard days.",
                        "metrics": [
                            "Sessions attended this month",
                            "How are you feeling today?",
                        ],
                    },
                    {
                        "name": "Feel more connected",
                        "desc": "Start talking to other youth and joining activities.",
                        "metrics": [
                            "How connected do you feel to the group?",
                            "Goal Progress (1-10)",
                        ],
                    },
                ],
            },
        ],
    },
    "DEMO-009": {
        "label": "Zara Ahmed — mixed, loves activities but homework struggles",
        "program": "Youth Drop-In",
        "trend": "mixed",
        "note_count": 9,
        "sections": [
            {
                "name": "Engagement",
                "targets": [
                    {
                        "name": "Stay engaged with program",
                        "desc": "Keep coming even when school feels overwhelming.",
                        "metrics": [
                            "Sessions attended this month",
                            "Service Engagement",
                        ],
                    },
                    {
                        "name": "Feel better day-to-day",
                        "desc": "Have more good days than bad.",
                        "metrics": [
                            "How are you feeling today?",
                            "Goal Progress (1-10)",
                        ],
                    },
                ],
            },
        ],
    },
    # =========================================================================
    # Newcomer Connections (Noor Worker) — DEMO-010, 011, 012
    # =========================================================================
    "DEMO-010": {
        "label": "Amara Diallo — improving, found family doctor",
        "program": "Newcomer Connections",
        "trend": "improving",
        "note_count": 10,
        "sections": [
            {
                "name": "Settlement",
                "targets": [
                    {
                        "name": "Navigate services on my own",
                        "desc": "Be able to book appointments and find services without help.",
                        "metrics": [
                            "Confidence navigating services",
                            "Community connections this month",
                        ],
                    },
                    {
                        "name": "Feel more comfortable with English",
                        "desc": "Use English for everyday things without so much stress.",
                        "metrics": [
                            "Comfort with English in daily life",
                            "Goal Progress (1-10)",
                        ],
                    },
                ],
            },
        ],
    },
    "DEMO-011": {
        "label": "Fatima Hassan — struggling, isolated, language barriers",
        "program": "Newcomer Connections",
        "trend": "struggling",
        "note_count": 9,
        "sections": [
            {
                "name": "Settlement",
                "targets": [
                    {
                        "name": "Build confidence with English",
                        "desc": "Feel less afraid to speak English in public.",
                        "metrics": [
                            "Comfort with English in daily life",
                            "How are you feeling today?",
                        ],
                    },
                    {
                        "name": "Access community services",
                        "desc": "Know where to go for help and feel OK asking.",
                        "metrics": [
                            "Confidence navigating services",
                            "Community connections this month",
                        ],
                    },
                ],
            },
        ],
    },
    "DEMO-012": {
        "label": "Carlos Reyes — stable, near program graduation",
        "program": "Newcomer Connections",
        "trend": "stable",
        "note_count": 8,
        "sections": [
            {
                "name": "Settlement",
                "targets": [
                    {
                        "name": "Connect with community",
                        "desc": "Build a network of people and places in the neighbourhood.",
                        "metrics": [
                            "Community connections this month",
                            "Confidence navigating services",
                        ],
                    },
                    {
                        "name": "Practise English daily",
                        "desc": "Use English at home, work, and in the community.",
                        "metrics": [
                            "Comfort with English in daily life",
                            "Goal Progress (1-10)",
                        ],
                    },
                ],
            },
        ],
    },
    # =========================================================================
    # Community Kitchen (Both workers) — DEMO-013, 014, 015
    # =========================================================================
    "DEMO-013": {
        "label": "Priya Sharma — improving, cooking for kids",
        "program": "Community Kitchen",
        "trend": "improving",
        "note_count": 8,
        "sections": [
            {
                "name": "Cooking Skills",
                "targets": [
                    {
                        "name": "Cook healthy meals for my kids",
                        "desc": "Learn to make affordable, healthy meals from scratch.",
                        "metrics": [
                            "Cooking confidence",
                            "Healthy meals prepared this week",
                        ],
                    },
                    {
                        "name": "Show up consistently",
                        "desc": "Make the Kitchen a regular part of my week.",
                        "metrics": [
                            "Sessions attended this month",
                            "How are you feeling today?",
                        ],
                    },
                ],
            },
        ],
    },
    "DEMO-014": {
        "label": "Liam O'Connor — stable, volunteers to help",
        "program": "Community Kitchen",
        "trend": "stable",
        "note_count": 7,
        "sections": [
            {
                "name": "Cooking Skills",
                "targets": [
                    {
                        "name": "Keep cooking skills growing",
                        "desc": "Try new recipes and techniques each week.",
                        "metrics": [
                            "Cooking confidence",
                            "Healthy meals prepared this week",
                        ],
                    },
                ],
            },
        ],
    },
    "DEMO-015": {
        "label": "Nadia Kovac — mixed, learning basics",
        "program": "Community Kitchen",
        "trend": "mixed",
        "note_count": 8,
        "sections": [
            {
                "name": "Cooking & Connection",
                "targets": [
                    {
                        "name": "Learn to cook on a budget",
                        "desc": "Replace takeout with homemade meals.",
                        "metrics": [
                            "Cooking confidence",
                            "Healthy meals prepared this week",
                        ],
                    },
                    {
                        "name": "Feel part of something",
                        "desc": "Connect with others in the Kitchen community.",
                        "metrics": [
                            "How are you feeling today?",
                            "Sessions attended this month",
                        ],
                    },
                ],
            },
        ],
    },
}

# Kitchen plan sections for cross-enrolled clients (on top of primary plans)
CROSS_ENROLMENT_PLANS = {
    "DEMO-001": {
        "program": "Community Kitchen",
        "sections": [
            {
                "name": "Kitchen Skills",
                "targets": [
                    {
                        "name": "Try new recipes",
                        "desc": "Expand cooking skills through Kitchen sessions.",
                        "metrics": [
                            "Cooking confidence",
                            "Healthy meals prepared this week",
                        ],
                    },
                ],
            },
        ],
    },
    "DEMO-004": {
        "program": "Community Kitchen",
        "sections": [
            {
                "name": "Kitchen Skills",
                "targets": [
                    {
                        "name": "Cook meals at home",
                        "desc": "Use Kitchen recipes to eat healthier and save money.",
                        "metrics": [
                            "Cooking confidence",
                            "Healthy meals prepared this week",
                        ],
                    },
                ],
            },
        ],
    },
    "DEMO-010": {
        "program": "Community Kitchen",
        "sections": [
            {
                "name": "Kitchen Skills",
                "targets": [
                    {
                        "name": "Learn Canadian recipes",
                        "desc": "Try recipes that use local, affordable ingredients.",
                        "metrics": [
                            "Cooking confidence",
                            "Healthy meals prepared this week",
                        ],
                    },
                ],
            },
        ],
    },
}


# ---------------------------------------------------------------------------
# Client goals — participant-voiced, set on the first target of each client
# ---------------------------------------------------------------------------

CLIENT_GOALS = {
    "DEMO-001": "I want to get a job where I feel respected",
    "DEMO-002": "I want to stop panicking before every interview",
    "DEMO-003": "I want to keep my routine going and not slide back",
    "DEMO-004": "I need a place that feels safe — not just a roof",
    "DEMO-005": "I don't want to lose my apartment",
    "DEMO-006": "I just want things to stop being so unpredictable",
    "DEMO-007": "I want to feel like I belong somewhere",
    "DEMO-008": "I want to stop being so shy and actually talk to people",
    "DEMO-009": "I want to do better in school but I don't know how",
    "DEMO-010": "I want to go to the doctor without needing someone to come with me",
    "DEMO-011": "I want to feel less alone in this country",
    "DEMO-012": "I want to be able to do things on my own here",
    "DEMO-013": "I want to cook proper meals for my kids, not just frozen stuff",
    "DEMO-014": "I like helping out here — it gives me purpose",
    "DEMO-015": "I want to learn to cook so I'm not always eating takeout",
}


# ---------------------------------------------------------------------------
# Qualitative data — client words that progress through the journey
# ---------------------------------------------------------------------------

CLIENT_WORDS_SAMPLES = [
    "It's hard",
    "I don't know if this is working",
    "I almost didn't come today",
    "I showed up today",
    "I'm trying",
    "It's getting a bit easier",
    "I actually wanted to come today",
    "Something feels different",
    "I told my friend about what we talked about",
    "I'm starting to believe this might work",
]


# ---------------------------------------------------------------------------
# Program-specific note texts
# ---------------------------------------------------------------------------

PROGRAM_QUICK_NOTES = {
    "Supported Employment": [
        "Brief check-in before mock interview. Feeling nervous but prepared.",
        "Phone call — confirmed workshop attendance for Thursday.",
        "Client dropped off updated resume for review.",
        "Quick chat after job fair. Picked up three leads.",
        "Left voicemail about new job posting that matches client's skills.",
        "Client called to share news — got a callback for an interview.",
        "Checked in after missed appointment. Will reschedule for next week.",
        "Brief follow-up on application status. Still waiting to hear back.",
    ],
    "Housing Stability": [
        "Brief check-in. Reports feeling more settled this week.",
        "Phone call — confirmed apartment viewing for Wednesday.",
        "Client dropped in to update address after move.",
        "Quick call about landlord communication. Situation stable.",
        "Left voicemail re: housing application deadline this Friday.",
        "Client called — worried about rent increase. Discussed options.",
        "Checked in after missed appointment. Had a housing emergency.",
        "Brief follow-up on utility assistance application.",
    ],
    "Youth Drop-In": [
        "Quick check-in during snack time. In good spirits.",
        "Helped set up for group activity without being asked.",
        "Arrived late but stayed for the full session.",
        "Brief chat about homework. Offered to help next week.",
        "Phone call to parent about upcoming field trip permission form.",
        "Quick check-in — group was smaller today, quieter energy.",
        "Asked about volunteering at the centre. Excited about it.",
        "Brief debrief after group. Good energy today.",
    ],
    "Newcomer Connections": [
        "Brief check-in before conversation circle. Feeling confident.",
        "Phone call — helped find the right bus route to an appointment.",
        "Client dropped in to ask about English classes in the neighbourhood.",
        "Quick follow-up on doctor's appointment. Found it stressful.",
        "Left voicemail about community event this Saturday.",
        "Client called to say they registered for a library card on their own.",
        "Brief chat about school enrollment for client's children.",
        "Checked in after missed session. Had a family commitment.",
    ],
    "Community Kitchen": [
        "Quick check-in before session. Excited about today's recipe.",
        "Brief chat during cleanup. Volunteered to organise the pantry.",
        "Tried a new technique today — seemed proud of the result.",
        "Phone call — confirmed ingredients for next week's session.",
        "Quick debrief after session. Good teamwork today.",
        "Mentioned cooking the recipe at home for family. Big smile.",
        "Brief check-in. Smaller group today but engaged.",
        "Brought family's feedback on last week's recipe. They loved it.",
    ],
}

PROGRAM_FULL_SUMMARIES = {
    "Supported Employment": [
        "Resume review session. Updated work history and tailored cover letter for retail position. Client showing more confidence in describing skills.",
        "Mock interview practice. Worked through common questions. Struggled with 'tell me about yourself' but improved after rehearsing.",
        "Reviewed three job postings together. Client identified two that match their skills. Discussed application strategy and timelines.",
        "Follow-up on recent interview. Felt it went well but anxious about waiting. Discussed managing expectations and next steps.",
        "Goal-setting session. Adjusted job search targets based on recent progress. Feeling more focused and motivated.",
        "Workshop debrief. Attended workplace safety certification. Discussed how this opens up new positions.",
        "Reviewed application tracker. Several applications submitted this month. One callback received.",
        "Session focused on workplace communication skills. Role-played difficult conversations with a supervisor.",
    ],
    "Housing Stability": [
        "Apartment viewing debrief. Looked at two units today. One is affordable but far from transit. Discussed trade-offs.",
        "Budgeting session. Reviewed monthly expenses and identified areas to save. Surprised by food delivery costs.",
        "Landlord mediation follow-up. Communication has improved since last meeting. Rent arrears plan is on track.",
        "Housing application support. Completed subsidised housing application together. Wait time is 6-12 months.",
        "Crisis follow-up. Received eviction notice. Connected with legal aid for next steps. Safety plan updated.",
        "Session focused on tenant rights. Reviewed what landlords can and cannot do. Feeling more empowered.",
        "Monthly review of housing stability. Reports feeling safer and more settled. Neighbours have been friendly.",
        "Joint session with income support worker. Explored additional benefits client may be eligible for.",
    ],
    "Youth Drop-In": [
        "Group activity: team-building exercises. Took a leadership role organising teams. Strong positive energy.",
        "Homework help session. Was frustrated at first but stuck with it. Made progress on math assignment.",
        "Check-in circle. Youth shared highs and lows of the week. Good conversation about school stress.",
        "Arts and crafts activity. Made vision boards. Good conversations about goals and dreams.",
        "Field trip to community centre pool. All youth attended. Seemed more relaxed in the social setting.",
        "Cooking activity — made trail mix. Practised measuring and following instructions. Lots of laughing.",
        "Group discussion about online safety. Youth engaged well and shared their own experiences.",
        "End-of-month celebration. Youth reflected on what they enjoyed most. 'This place feels like home.'",
    ],
    "Newcomer Connections": [
        "Conversation circle session. Practised ordering at a restaurant. Helped translate for newer members.",
        "Service navigation appointment. Accompanied to walk-in clinic. Managed the intake form with support.",
        "Community orientation walk. Showed the library, community centre, and grocery store. Took notes.",
        "Group session on banking. Practised vocabulary for common transactions. Several opened accounts this month.",
        "Individual session. Found a family doctor on their own — celebrated this milestone. Discussed next goals.",
        "Conversation circle focused on weather and seasons. Good energy. Spoke more than usual today.",
        "Settlement planning session. Reviewed progress toward program goals. Close to graduation.",
        "Group activity: potluck lunch. Brought dishes from home countries. Beautiful cultural exchange.",
    ],
    "Community Kitchen": [
        "Today's recipe: lentil soup. Group worked together well. Helped each other with knife skills.",
        "Budget grocery challenge. Each participant planned a week of meals under $40. Creative solutions shared.",
        "Session focused on meal prep and batch cooking. Shared systems for Sunday meal prep.",
        "Today's recipe: stir-fry with seasonal vegetables. Discussed food safety and proper storage.",
        "Nutrition basics session. Talked about reading labels and understanding ingredients. Very engaged.",
        "Today's recipe: banana bread. Several had never baked before. Excitement when it came out of the oven.",
        "Session on cooking for picky eaters. Parents shared tips. Kids now ask to help cook.",
        "End-of-month review. Shared recipes tried at home. 'Cooking has become my favourite part of the week.'",
    ],
}


# ---------------------------------------------------------------------------
# Generate realistic metric value sequences
# ---------------------------------------------------------------------------


def _generate_trend_values(trend, count, metric_name, metric_def):
    """Generate a list of metric values that follow a realistic trend."""
    lo = metric_def.min_value or 0
    hi = metric_def.max_value or 100

    # For "lower is better" metrics, invert the trend direction
    lower_is_better = metric_name in (
        "PHQ-9 (Depression)",
        "GAD-7 (Anxiety)",
        "K10 (Psychological Distress)",
        "Nights in Shelter (past 30 days)",
        "Cravings Intensity",
    )

    values = []
    for i in range(count):
        t = i / max(count - 1, 1)  # 0.0 to 1.0

        if trend == "improving":
            if lower_is_better:
                base = hi * 0.7 + (hi * 0.2 - hi * 0.7) * t
            else:
                base = lo + (hi - lo) * (0.25 + 0.5 * t)

        elif trend == "struggling":
            if lower_is_better:
                base = hi * 0.5 + (hi * 0.1) * t
            else:
                base = lo + (hi - lo) * (0.35 - 0.1 * t)

        elif trend == "mixed":
            if i % 3 == 0:
                base = lo + (hi - lo) * 0.5
            elif i % 3 == 1:
                base = lo + (hi - lo) * 0.35
            else:
                base = lo + (hi - lo) * 0.6
            if lower_is_better:
                base = hi - base + lo

        elif trend == "crisis_then_improving":
            if t < 0.3:
                if lower_is_better:
                    base = hi * 0.8
                else:
                    base = lo + (hi - lo) * 0.15
            else:
                recovery_t = (t - 0.3) / 0.7
                if lower_is_better:
                    base = hi * 0.8 - (hi * 0.5) * recovery_t
                else:
                    base = lo + (hi - lo) * (0.15 + 0.55 * recovery_t)

        elif trend == "stable":
            if lower_is_better:
                base = lo + (hi - lo) * 0.2
            else:
                base = lo + (hi - lo) * 0.75

        else:
            base = lo + (hi - lo) * 0.5

        # Add noise (+-8% of range)
        noise = (hi - lo) * 0.08 * (random.random() - 0.5)
        val = base + noise
        val = max(lo, min(hi, val))

        # Round appropriately based on unit
        if metric_def.unit in (
            "days", "nights", "hours", "applications",
            "meals", "sessions", "connections",
        ):
            val = int(round(val))
        elif metric_def.unit == "$":
            val = round(val / 50) * 50
        elif metric_def.unit == "%":
            val = round(val)
        else:
            val = round(val, 1)

        values.append(val)

    return values


# ---------------------------------------------------------------------------
# Events per client
# ---------------------------------------------------------------------------

CLIENT_EVENTS = {
    # Supported Employment (Casey)
    "DEMO-001": [
        {"type": "Intake", "title": "Employment program intake", "days_ago": 150},
        {"type": "Follow-up", "title": "30-day check-in — resume submitted", "days_ago": 120},
        {"type": "Follow-up", "title": "Mock interview session", "days_ago": 80},
        {"type": "Follow-up", "title": "First real interview — callback received", "days_ago": 40},
    ],
    "DEMO-002": [
        {"type": "Intake", "title": "Employment program intake", "days_ago": 140},
        {"type": "Follow-up", "title": "Resume building workshop", "days_ago": 110},
        {"type": "Follow-up", "title": "Monthly check-in — struggling with anxiety", "days_ago": 70},
        {"type": "Referral", "title": "Referred to anxiety support group", "days_ago": 50},
    ],
    "DEMO-003": [
        {"type": "Intake", "title": "Employment program intake", "days_ago": 180},
        {"type": "Follow-up", "title": "90-day review — working part-time", "days_ago": 90},
        {"type": "Follow-up", "title": "Discharge planning discussion", "days_ago": 20},
    ],
    # Housing Stability (Casey)
    "DEMO-004": [
        {"type": "Intake", "title": "Housing intake — shelter referral", "days_ago": 160},
        {"type": "Crisis", "title": "Emergency shelter stay after eviction", "days_ago": 140},
        {"type": "Follow-up", "title": "Housing search — two viewings booked", "days_ago": 100},
        {"type": "Follow-up", "title": "Moved into transitional housing", "days_ago": 60},
        {"type": "Follow-up", "title": "Monthly check-in — settling in well", "days_ago": 20},
    ],
    "DEMO-005": [
        {"type": "Intake", "title": "Housing intake", "days_ago": 130},
        {"type": "Crisis", "title": "Eviction notice received", "days_ago": 110},
        {"type": "Referral", "title": "Referred to legal aid for tenant rights", "days_ago": 100},
        {"type": "Follow-up", "title": "Monthly check-in — eviction fight ongoing", "days_ago": 60},
    ],
    "DEMO-006": [
        {"type": "Intake", "title": "Housing intake — self-referral", "days_ago": 145},
        {"type": "Follow-up", "title": "Apartment viewing — too expensive", "days_ago": 110},
        {"type": "Follow-up", "title": "Budgeting session", "days_ago": 70},
        {"type": "Follow-up", "title": "Monthly check-in — couch surfing", "days_ago": 30},
    ],
    # Youth Drop-In (Noor)
    "DEMO-007": [
        {"type": "Intake", "title": "Youth Drop-In intake", "days_ago": 120},
        {"type": "Follow-up", "title": "Starting to open up in group", "days_ago": 80},
        {"type": "Follow-up", "title": "Leadership moment — organised team activity", "days_ago": 40},
    ],
    "DEMO-008": [
        {"type": "Intake", "title": "Youth Drop-In intake", "days_ago": 135},
        {"type": "Crisis", "title": "Didn't attend for 3 weeks — outreach call", "days_ago": 100},
        {"type": "Follow-up", "title": "Returned to group — quieter but present", "days_ago": 75},
        {"type": "Follow-up", "title": "Monthly check-in — attendance improving", "days_ago": 30},
    ],
    "DEMO-009": [
        {"type": "Intake", "title": "Youth Drop-In intake", "days_ago": 110},
        {"type": "Follow-up", "title": "Loves activities, homework is hard", "days_ago": 70},
        {"type": "Follow-up", "title": "Connected with homework tutor", "days_ago": 35},
    ],
    # Newcomer Connections (Noor)
    "DEMO-010": [
        {"type": "Intake", "title": "Newcomer intake — settlement support", "days_ago": 150},
        {"type": "Follow-up", "title": "Accompanied to walk-in clinic", "days_ago": 120},
        {"type": "Follow-up", "title": "Found family doctor independently!", "days_ago": 70},
        {"type": "Follow-up", "title": "Monthly check-in — growing confidence", "days_ago": 25},
    ],
    "DEMO-011": [
        {"type": "Intake", "title": "Newcomer intake", "days_ago": 140},
        {"type": "Follow-up", "title": "Conversation circle — very quiet", "days_ago": 100},
        {"type": "Follow-up", "title": "Monthly check-in — still isolated", "days_ago": 60},
        {"type": "Referral", "title": "Referred to women's support group", "days_ago": 30},
    ],
    "DEMO-012": [
        {"type": "Intake", "title": "Newcomer intake", "days_ago": 155},
        {"type": "Follow-up", "title": "Community orientation walk", "days_ago": 120},
        {"type": "Follow-up", "title": "90-day review — strong progress", "days_ago": 65},
        {"type": "Follow-up", "title": "Graduation planning session", "days_ago": 15},
    ],
    # Community Kitchen (Both workers)
    "DEMO-013": [
        {"type": "Intake", "title": "Community Kitchen intake", "days_ago": 120},
        {"type": "Follow-up", "title": "Session check-in — really enjoying it", "days_ago": 75},
        {"type": "Follow-up", "title": "Kids tried the recipes at home", "days_ago": 30},
    ],
    "DEMO-014": [
        {"type": "Intake", "title": "Community Kitchen intake", "days_ago": 130},
        {"type": "Follow-up", "title": "Volunteered to help with setup", "days_ago": 80},
        {"type": "Follow-up", "title": "Monthly check-in — consistent attendance", "days_ago": 25},
    ],
    "DEMO-015": [
        {"type": "Intake", "title": "Community Kitchen intake", "days_ago": 100},
        {"type": "Follow-up", "title": "Tried cooking at home for first time", "days_ago": 55},
        {"type": "Follow-up", "title": "Monthly check-in — mixed feelings", "days_ago": 20},
    ],
}


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------


class Command(BaseCommand):
    help = "Populate demo clients with plans, notes, events, and alerts for charts/reports."

    def _populate_custom_fields(self):
        """Populate custom field values for demo clients (always runs, idempotent)."""
        fields_updated = 0
        fields_skipped = 0
        clients_missing = 0
        for record_id, field_values in CLIENT_CUSTOM_FIELDS.items():
            client = ClientFile.objects.filter(record_id=record_id).first()
            if not client:
                clients_missing += 1
                continue
            for field_name, value in field_values.items():
                try:
                    field_def = CustomFieldDefinition.objects.get(name=field_name)
                    cdv, _ = ClientDetailValue.objects.get_or_create(
                        client_file=client,
                        field_def=field_def,
                    )
                    cdv.set_value(value)
                    cdv.save()
                    fields_updated += 1
                except CustomFieldDefinition.DoesNotExist:
                    fields_skipped += 1
        if fields_updated:
            self.stdout.write(
                f"  Custom fields: {fields_updated} values populated for demo clients."
            )
        if clients_missing:
            self.stdout.write(self.style.WARNING(
                f"  Custom fields: {clients_missing} demo client(s) not found in database. "
                "Run 'python manage.py seed' to create them."
            ))
        if fields_skipped:
            self.stdout.write(self.style.WARNING(
                f"  Custom fields: {fields_skipped} skipped (field definitions not found). "
                "Run 'python manage.py seed' to create them."
            ))

    def handle(self, *args, **options):
        if not settings.DEMO_MODE:
            self.stdout.write(self.style.WARNING("DEMO_MODE is not enabled. Skipping."))
            return

        # Always populate custom fields (idempotent via get_or_create)
        self._populate_custom_fields()

        # Always ensure demo registration link exists (idempotent)
        programs_by_name = {p.name: p for p in Program.objects.all()}
        created_by = User.objects.filter(is_admin=True).first() or User.objects.first()
        if programs_by_name and created_by:
            self._create_demo_registration_link(programs_by_name, created_by)

        # Always ensure demo groups exist (idempotent via get_or_create)
        # Moved above the early-return guard so groups are created even when
        # other rich data already exists (e.g. environment seeded before groups
        # feature was added).
        try:
            worker1 = User.objects.get(username="demo-worker-1")
            worker2 = User.objects.get(username="demo-worker-2")
            workers_early = {"demo-worker-1": worker1, "demo-worker-2": worker2}
            now_early = timezone.now()
            random.seed(42)
            self._create_demo_groups(workers_early, programs_by_name, now_early)
        except User.DoesNotExist:
            pass  # Workers not yet created — full seed below will handle it

        # Check if rich data already exists
        if ProgressNote.objects.filter(
            client_file__record_id__startswith="DEMO-"
        ).exists():
            self.stdout.write("  Demo rich data already exists. Skipping.")
            return

        # Fetch workers
        try:
            worker1 = User.objects.get(username="demo-worker-1")
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(
                "demo-worker-1 not found. Run seed first."
            ))
            return

        try:
            worker2 = User.objects.get(username="demo-worker-2")
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(
                "demo-worker-2 not found. Run seed first."
            ))
            return

        workers = {"demo-worker-1": worker1, "demo-worker-2": worker2}

        # Fetch programs
        programs_by_name = {p.name: p for p in Program.objects.all()}
        for name in PROGRAM_WORKER:
            if name not in programs_by_name:
                self.stdout.write(self.style.ERROR(
                    f"Program '{name}' not found. Run seed first."
                ))
                return

        # Cache metric definitions and event types
        metrics_by_name = {
            m.name: m for m in MetricDefinition.objects.filter(is_library=True)
        }
        event_types = {et.name: et for et in EventType.objects.all()}

        now = timezone.now()
        random.seed(42)  # Reproducible demo data

        # --- Seed primary plans and notes for all 15 clients ---
        for record_id, plan_config in CLIENT_PLANS.items():
            self._seed_client_data(
                record_id, plan_config, workers, programs_by_name,
                metrics_by_name, event_types, now,
            )

        # --- Seed cross-enrolment plans (Kitchen) ---
        for record_id, cross_config in CROSS_ENROLMENT_PLANS.items():
            self._seed_cross_enrolment(
                record_id, cross_config, workers, programs_by_name,
                metrics_by_name, now,
            )

        # --- Create alerts for specific clients ---
        self._create_alerts(workers, programs_by_name)

        # --- Create demo groups ---
        self._create_demo_groups(workers, programs_by_name, now)

        self.stdout.write(self.style.SUCCESS(
            "  Demo rich data seeded successfully (15 clients across 5 programs)."
        ))

    def _create_demo_registration_link(self, programs_by_name, created_by):
        """Create a public registration link with slug 'demo' for the project website."""
        from apps.clients.models import CustomFieldGroup
        from apps.registration.models import RegistrationLink

        program = programs_by_name.get("Supported Employment")
        if not program:
            self.stdout.write(self.style.WARNING(
                "  Supported Employment program not found — skipping demo registration link."
            ))
            return

        description = (
            "This is a sample registration form. "
            "Your agency can customise which fields appear, "
            "add field groups, set capacity limits, and brand it with your logo."
        )

        link, created = RegistrationLink.objects.get_or_create(
            slug="demo",
            defaults={
                "program": program,
                "title": "Program Registration",
                "description": description,
                "auto_approve": False,
                "created_by": created_by,
            },
        )

        # Keep the demo link simple — only Contact Information.
        # Always reset field groups so redeployments pick up changes.
        contact_group = CustomFieldGroup.objects.filter(
            title="Contact Information", status="active"
        ).first()
        if contact_group:
            link.field_groups.set([contact_group])
        else:
            self.stdout.write(self.style.WARNING(
                "  Contact Information field group not found — demo form will have no custom fields."
            ))

        if created:
            self.stdout.write("  Created demo registration link (slug: demo)")
        else:
            # Update title/description on existing links too
            link.title = "Program Registration"
            link.description = description
            link.save(update_fields=["title", "description"])
            self.stdout.write("  Updated demo registration link.")

    def _seed_client_data(
        self, record_id, plan_config, workers, programs_by_name,
        metrics_by_name, event_types, now,
    ):
        """Create plan, notes, and events for one client."""
        client = ClientFile.objects.filter(record_id=record_id).first()
        if not client:
            self.stdout.write(self.style.WARNING(
                f"  Client {record_id} not found. Skipping."
            ))
            return

        program_name = plan_config["program"]
        program = programs_by_name.get(program_name)
        worker_username = PROGRAM_WORKER.get(program_name, "demo-worker-1")
        author = workers.get(worker_username)

        if not program or not author:
            self.stdout.write(self.style.WARNING(
                f"  Missing program/worker for {record_id}. Skipping."
            ))
            return

        self.stdout.write(f"  Seeding {record_id}: {plan_config['label']}...")

        # ----------------------------------------------------------
        # 1. Create plan sections, targets, and link metrics
        # ----------------------------------------------------------
        all_targets = []  # [(PlanTarget, [MetricDefinition, ...])]
        first_target = True

        for s_idx, section_data in enumerate(plan_config["sections"]):
            section = PlanSection.objects.create(
                client_file=client,
                name=section_data["name"],
                program=program,
                sort_order=s_idx,
            )

            for t_idx, target_data in enumerate(section_data["targets"]):
                target = PlanTarget.objects.create(
                    plan_section=section,
                    client_file=client,
                    name=target_data["name"],
                    description=target_data["desc"],
                    sort_order=t_idx,
                )

                # Set client_goal on the first target
                if first_target and record_id in CLIENT_GOALS:
                    target.client_goal = CLIENT_GOALS[record_id]
                    target.save()
                    first_target = False

                # Create initial revision
                PlanTargetRevision.objects.create(
                    plan_target=target,
                    name=target.name,
                    description=target.description,
                    status="default",
                    changed_by=author,
                )

                # Link metrics
                target_metrics = []
                for m_idx, metric_name in enumerate(target_data["metrics"]):
                    metric_def = metrics_by_name.get(metric_name)
                    if metric_def:
                        PlanTargetMetric.objects.create(
                            plan_target=target,
                            metric_def=metric_def,
                            sort_order=m_idx,
                        )
                        target_metrics.append(metric_def)
                    else:
                        self.stdout.write(self.style.WARNING(
                            f"    Metric '{metric_name}' not found."
                        ))

                all_targets.append((target, target_metrics))

        # ----------------------------------------------------------
        # 2. Create progress notes with metric recordings
        # ----------------------------------------------------------
        note_count = plan_config["note_count"]
        trend = plan_config["trend"]
        quick_notes = PROGRAM_QUICK_NOTES.get(
            program_name, PROGRAM_QUICK_NOTES["Supported Employment"]
        )
        full_summaries = PROGRAM_FULL_SUMMARIES.get(
            program_name, PROGRAM_FULL_SUMMARIES["Supported Employment"]
        )

        # Spread notes over 180 days (6 months)
        note_days = sorted(
            [random.randint(5, 175) for _ in range(note_count)], reverse=True
        )

        # Pre-generate metric value sequences
        metric_sequences = {}
        for target, target_metrics in all_targets:
            for md in target_metrics:
                key = (target.pk, md.pk)
                metric_sequences[key] = _generate_trend_values(
                    trend, note_count, md.name, md
                )

        # Determine base interaction type
        base_interaction = PROGRAM_INTERACTION_TYPE.get(program_name, "session")

        for note_idx, days_ago in enumerate(note_days):
            is_quick = note_idx % 3 == 0  # ~1/3 quick notes
            note_type = "quick" if is_quick else "full"
            backdate = now - timedelta(
                days=days_ago, hours=random.randint(8, 17)
            )

            # Vary interaction type for Housing and Newcomer programs
            if program_name == "Housing Stability":
                interaction = random.choice(
                    ["session", "session", "phone", "home_visit"]
                )
            elif program_name == "Newcomer Connections":
                interaction = random.choice(["session", "session", "group"])
            else:
                interaction = base_interaction

            # Engagement observation progresses over time
            progress_fraction = note_idx / max(note_count - 1, 1)
            if progress_fraction < 0.3:
                engagement = "guarded"
            elif progress_fraction < 0.6:
                engagement = "engaged"
            else:
                engagement = "valuing"

            note = ProgressNote.objects.create(
                client_file=client,
                note_type=note_type,
                interaction_type=interaction,
                author=author,
                author_program=program,
                backdate=backdate,
                notes_text=(
                    random.choice(quick_notes) if is_quick else ""
                ),
                summary=(
                    "" if is_quick else random.choice(full_summaries)
                ),
                engagement_observation=engagement,
            )

            # For full notes, record metrics against each target
            if not is_quick:
                # Qualitative progress descriptor
                if progress_fraction < 0.3:
                    descriptor = "harder"
                elif progress_fraction < 0.5:
                    descriptor = "holding"
                elif progress_fraction < 0.75:
                    descriptor = "shifting"
                else:
                    descriptor = "good_place"

                # Client words — pick based on journey position
                words_idx = min(
                    int(progress_fraction * len(CLIENT_WORDS_SAMPLES)),
                    len(CLIENT_WORDS_SAMPLES) - 1,
                )

                for target, target_metrics in all_targets:
                    pnt = ProgressNoteTarget.objects.create(
                        progress_note=note,
                        plan_target=target,
                        notes=random.choice(full_summaries),
                        progress_descriptor=descriptor,
                        client_words=CLIENT_WORDS_SAMPLES[words_idx],
                    )

                    for md in target_metrics:
                        key = (target.pk, md.pk)
                        seq = metric_sequences[key]
                        val = seq[note_idx] if note_idx < len(seq) else seq[-1]
                        MetricValue.objects.create(
                            progress_note_target=pnt,
                            metric_def=md,
                            value=str(val),
                        )

        # ----------------------------------------------------------
        # 3. Create events
        # ----------------------------------------------------------
        for evt_data in CLIENT_EVENTS.get(record_id, []):
            et = event_types.get(evt_data["type"])
            if not et:
                continue
            Event.objects.create(
                client_file=client,
                title=evt_data["title"],
                event_type=et,
                author_program=program,
                start_timestamp=now - timedelta(days=evt_data["days_ago"]),
            )

    def _seed_cross_enrolment(
        self, record_id, cross_config, workers, programs_by_name,
        metrics_by_name, now,
    ):
        """Add Kitchen plan section and targets for a cross-enrolled client."""
        client = ClientFile.objects.filter(record_id=record_id).first()
        if not client:
            return

        program_name = cross_config["program"]
        program = programs_by_name.get(program_name)
        if not program:
            return

        # Use the client's primary program worker
        primary_program = CLIENT_PLANS[record_id]["program"]
        worker_username = PROGRAM_WORKER.get(primary_program, "demo-worker-1")
        author = workers.get(worker_username)

        for s_idx, section_data in enumerate(cross_config["sections"]):
            section = PlanSection.objects.create(
                client_file=client,
                name=section_data["name"],
                program=program,
                sort_order=10 + s_idx,  # after primary plan sections
            )

            for t_idx, target_data in enumerate(section_data["targets"]):
                target = PlanTarget.objects.create(
                    plan_section=section,
                    client_file=client,
                    name=target_data["name"],
                    description=target_data["desc"],
                    sort_order=t_idx,
                )

                PlanTargetRevision.objects.create(
                    plan_target=target,
                    name=target.name,
                    description=target.description,
                    status="default",
                    changed_by=author,
                )

                for m_idx, metric_name in enumerate(target_data["metrics"]):
                    metric_def = metrics_by_name.get(metric_name)
                    if metric_def:
                        PlanTargetMetric.objects.create(
                            plan_target=target,
                            metric_def=metric_def,
                            sort_order=m_idx,
                        )

    def _create_alerts(self, workers, programs_by_name):
        """Create alerts for clients with notable situations."""
        alert_data = [
            {
                "record_id": "DEMO-004",
                "content": "Housing crisis — was in emergency shelter. Now in transitional housing. Check in weekly.",
                "program": "Housing Stability",
                "worker": "demo-worker-1",
            },
            {
                "record_id": "DEMO-005",
                "content": "Eviction risk — legal aid case pending. Monitor closely.",
                "program": "Housing Stability",
                "worker": "demo-worker-1",
            },
            {
                "record_id": "DEMO-008",
                "content": "Was withdrawn for several weeks. Now attending again — approach gently, don't push.",
                "program": "Youth Drop-In",
                "worker": "demo-worker-2",
            },
            {
                "record_id": "DEMO-011",
                "content": "Very isolated. Language barrier makes group participation difficult. Needs 1:1 support.",
                "program": "Newcomer Connections",
                "worker": "demo-worker-2",
            },
        ]

        for ad in alert_data:
            client = ClientFile.objects.filter(record_id=ad["record_id"]).first()
            if not client:
                continue
            program = programs_by_name.get(ad["program"])
            author = workers.get(ad["worker"])
            if program and author:
                Alert.objects.create(
                    client_file=client,
                    content=ad["content"],
                    author=author,
                    author_program=program,
                )

    # ------------------------------------------------------------------
    # Demo groups: service groups, activity groups, and projects
    # ------------------------------------------------------------------

    def _create_demo_groups(self, workers, programs_by_name, now):
        """Create demo groups with sessions, attendance, and highlights."""
        worker1 = workers["demo-worker-1"]
        worker2 = workers["demo-worker-2"]

        vibes = ["solid", "great", "low", "solid", "great", "solid", "great", "solid"]

        def get_client(rid):
            return ClientFile.objects.filter(record_id=rid).first()

        # -------------------------------------------------------
        # Group 1: Wednesday After-School Circle (service_group)
        # Under Youth Drop-In, facilitated by Noor
        # -------------------------------------------------------
        youth_program = programs_by_name.get("Youth Drop-In")
        circle, created = Group.objects.get_or_create(
            name="Wednesday After-School Circle",
            defaults={
                "group_type": "service_group",
                "program": youth_program,
                "description": (
                    "Weekly peer support and activities for youth. "
                    "Check-in circles, skill-building, and group discussions."
                ),
            },
        )

        # Always ensure demo client memberships are properly linked
        # (fixes orphaned memberships from re-seeding)
        circle_members = []
        for rid in ["DEMO-007", "DEMO-008", "DEMO-009"]:
            client = get_client(rid)
            if client:
                membership, _ = GroupMembership.objects.get_or_create(
                    group=circle,
                    client_file=client,
                    defaults={"role": "member"},
                )
                circle_members.append(membership)

        # Remove orphaned memberships (NULL client_file, empty name)
        GroupMembership.objects.filter(
            group=circle, client_file__isnull=True, member_name="",
        ).delete()

        if created:
            self.stdout.write("  Creating group: Wednesday After-School Circle...")

            session_notes_list = [
                "Good discussion about managing stress at school.",
                "Quiet session today. Several members seemed tired.",
                "Great energy — members shared coping strategies with each other.",
                "Focused on conflict resolution skills. Role-playing exercise went well.",
                "Check-in round took most of the session. Members needed space to talk.",
                "Introduced grounding techniques. Members practised together.",
                "Peer support was strong today. Jayden mentored newer members.",
                "Wrapped up the resilience module. Members reflected on growth.",
            ]

            for i in range(8):
                days_ago = 84 - (i * 11)
                session_date = (now - timedelta(days=days_ago)).date()
                session, s_created = GroupSession.objects.get_or_create(
                    group=circle,
                    session_date=session_date,
                    defaults={
                        "facilitator": worker2,
                        "group_vibe": vibes[i % len(vibes)],
                    },
                )
                if s_created:
                    session.notes = session_notes_list[i]
                    session.save()

                    # Attendance — a few scattered absences
                    for j, membership in enumerate(circle_members):
                        absent = (i == 1 and j == 1) or (i == 4 and j == 2)
                        GroupSessionAttendance.objects.get_or_create(
                            group_session=session,
                            membership=membership,
                            defaults={"present": not absent},
                        )

            # Add highlights
            sessions = list(
                GroupSession.objects.filter(group=circle).order_by("session_date")
            )
            if len(sessions) >= 6 and len(circle_members) >= 2:
                h1, _ = GroupSessionHighlight.objects.get_or_create(
                    group_session=sessions[2],
                    membership=circle_members[0],
                    defaults={},
                )
                h1.notes = "Jayden organised the check-in circle on his own today. Real leadership emerging."
                h1.save()

                h2, _ = GroupSessionHighlight.objects.get_or_create(
                    group_session=sessions[5],
                    membership=circle_members[1],
                    defaults={},
                )
                h2.notes = "Maya spoke up during group for the first time. Shared something personal. Big step."
                h2.save()

        # -------------------------------------------------------
        # Group 2: Thursday Kitchen Session (activity_group)
        # Under Community Kitchen, facilitated by Noor
        # -------------------------------------------------------
        kitchen_program = programs_by_name.get("Community Kitchen")
        kitchen, created = Group.objects.get_or_create(
            name="Thursday Kitchen Session",
            defaults={
                "group_type": "activity_group",
                "program": kitchen_program,
                "description": (
                    "Weekly cooking sessions. Learn affordable, healthy recipes. "
                    "Open to all participants."
                ),
            },
        )

        # Always ensure demo client memberships are properly linked
        kitchen_members = []
        for rid in [
            "DEMO-013", "DEMO-014", "DEMO-015",
            "DEMO-001", "DEMO-004", "DEMO-010",
        ]:
            client = get_client(rid)
            if client:
                membership, _ = GroupMembership.objects.get_or_create(
                    group=kitchen,
                    client_file=client,
                    defaults={"role": "member"},
                )
                kitchen_members.append(membership)

        # Remove orphaned memberships (NULL client_file, empty name)
        GroupMembership.objects.filter(
            group=kitchen, client_file__isnull=True, member_name="",
        ).delete()

        if created:
            self.stdout.write("  Creating group: Thursday Kitchen Session...")

            kitchen_session_notes = [
                "Lentil soup day. Everyone pitched in. Good teamwork on the prep station.",
                "Budget grocery challenge — planned a week of meals under $40 each.",
                "Batch cooking session. Priya shared her meal prep system with the group.",
                "Stir-fry day. Practised knife skills and proper seasoning. Lots of laughing.",
                "Banana bread baking. First time baking for several participants. Big smiles.",
                "Nutrition labels session. Group was surprised by sugar content in cereals.",
            ]

            for i in range(6):
                days_ago = 77 - (i * 14)
                session_date = (now - timedelta(days=days_ago)).date()
                session, s_created = GroupSession.objects.get_or_create(
                    group=kitchen,
                    session_date=session_date,
                    defaults={
                        "facilitator": worker2,
                        "group_vibe": vibes[i % len(vibes)],
                    },
                )
                if s_created:
                    session.notes = kitchen_session_notes[i]
                    session.save()

                    for j, membership in enumerate(kitchen_members):
                        # Cross-enrolled clients (index 3+) miss a couple of sessions
                        absent = (i == 2 and j >= 3) or (i == 4 and j == 5)
                        GroupSessionAttendance.objects.get_or_create(
                            group_session=session,
                            membership=membership,
                            defaults={"present": not absent},
                        )

            # Highlights
            sessions = list(
                GroupSession.objects.filter(group=kitchen).order_by("session_date")
            )
            if len(sessions) >= 5 and len(kitchen_members) >= 2:
                h1, _ = GroupSessionHighlight.objects.get_or_create(
                    group_session=sessions[2],
                    membership=kitchen_members[0],
                    defaults={},
                )
                h1.notes = "Priya cooked the stir-fry recipe for her kids at home. They asked for seconds."
                h1.save()

                h2, _ = GroupSessionHighlight.objects.get_or_create(
                    group_session=sessions[4],
                    membership=kitchen_members[1],
                    defaults={},
                )
                h2.notes = "Liam volunteered to help clean up and organise the pantry. Natural helper."
                h2.save()

        # -------------------------------------------------------
        # Group 3: Community Mural Project (project)
        # Under Youth Drop-In, facilitated by Noor
        # -------------------------------------------------------
        mural, created = Group.objects.get_or_create(
            name="Community Mural Project",
            defaults={
                "group_type": "project",
                "program": youth_program,
                "description": (
                    "Youth design and paint a mural for the community centre hallway. "
                    "Develops teamwork, creativity, and ownership."
                ),
            },
        )

        # Always ensure demo client memberships are properly linked
        mural_members = []
        for rid in ["DEMO-007", "DEMO-009"]:
            client = get_client(rid)
            if client:
                membership, _ = GroupMembership.objects.get_or_create(
                    group=mural,
                    client_file=client,
                    defaults={"role": "member"},
                )
                mural_members.append(membership)

        # Non-client volunteer artist
        vol_membership, _ = GroupMembership.objects.get_or_create(
            group=mural,
            client_file=None,
            member_name="Alex (Volunteer Artist)",
            defaults={"role": "leader"},
        )
        mural_members.append(vol_membership)

        # Remove orphaned memberships (NULL client_file, empty name)
        # but keep intentional non-client members (like Alex)
        GroupMembership.objects.filter(
            group=mural, client_file__isnull=True, member_name="",
        ).delete()

        if created:
            self.stdout.write("  Creating group: Community Mural Project...")

            mural_session_notes = [
                "Brainstorming session — youth chose 'belonging' as the theme. Sketched ideas on big paper.",
                "Design refinement. Combined everyone's ideas into one layout. Alex helped with proportions.",
                "Started painting the background. Jayden took charge of mixing colours.",
                "Detail work today. Zara painted the tree section. Careful, focused work.",
            ]

            for i in range(4):
                days_ago = 60 - (i * 18)
                session_date = (now - timedelta(days=days_ago)).date()
                session, s_created = GroupSession.objects.get_or_create(
                    group=mural,
                    session_date=session_date,
                    defaults={
                        "facilitator": worker2,
                        "group_vibe": vibes[i % len(vibes)],
                    },
                )
                if s_created:
                    session.notes = mural_session_notes[i]
                    session.save()

                    for membership in mural_members:
                        GroupSessionAttendance.objects.get_or_create(
                            group_session=session,
                            membership=membership,
                            defaults={"present": True},
                        )

            # Milestones
            milestones = [
                {
                    "title": "Theme chosen and design approved",
                    "status": "complete",
                    "due_date": (now - timedelta(days=55)).date(),
                    "completed_date": (now - timedelta(days=56)).date(),
                    "notes": "Youth voted on 'belonging' as the theme. Design sketched and approved by centre director.",
                },
                {
                    "title": "Background painted",
                    "status": "complete",
                    "due_date": (now - timedelta(days=30)).date(),
                    "completed_date": (now - timedelta(days=28)).date(),
                    "notes": "Base colours and sky gradient complete. Looking great.",
                },
                {
                    "title": "Mural complete and unveiled",
                    "status": "in_progress",
                    "due_date": (now + timedelta(days=14)).date(),
                    "completed_date": None,
                    "notes": "Detail work in progress. Planning an unveiling event with families.",
                },
            ]
            for idx, ms in enumerate(milestones):
                ProjectMilestone.objects.get_or_create(
                    group=mural,
                    title=ms["title"],
                    defaults={
                        "status": ms["status"],
                        "due_date": ms["due_date"],
                        "completed_date": ms["completed_date"],
                        "notes": ms["notes"],
                        "sort_order": idx,
                    },
                )

            # Outcomes
            ProjectOutcome.objects.get_or_create(
                group=mural,
                outcome_date=(now - timedelta(days=20)).date(),
                defaults={
                    "description": (
                        "Both youth attended all 4 sessions. Jayden said "
                        "'I've never made something this big before.' "
                        "Visible pride and ownership."
                    ),
                    "evidence": (
                        "Attendance records. Facilitator observation. "
                        "Photos of work in progress."
                    ),
                    "created_by": worker2,
                },
            )

        self.stdout.write("  Demo groups seeded.")
