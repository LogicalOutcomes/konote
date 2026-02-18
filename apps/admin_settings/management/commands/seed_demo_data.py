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
- Email and staff-sent communications with varied delivery statuses
- Portal content (journal entries, messages, staff notes, correction requests)
- Registration submissions in various review states
- Suggestion themes linked to participant suggestions (for Outcome Insights)
- Staff-to-staff messages (internal operational messages about participants)

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
from apps.communications.models import Communication
from apps.events.models import (
    Alert,
    AlertCancellationRecommendation,
    CalendarFeedToken,
    Event,
    EventType,
    Meeting,
)
from apps.groups.models import (
    Group,
    GroupMembership,
    GroupSession,
    GroupSessionAttendance,
    GroupSessionHighlight,
    ProjectMilestone,
    ProjectOutcome,
)
from apps.communications.models import StaffMessage
from apps.notes.models import (
    MetricValue, ProgressNote, ProgressNoteTarget,
    SuggestionLink, SuggestionTheme, recalculate_theme_priority,
)
from apps.plans.models import (
    MetricDefinition,
    PlanSection,
    PlanTarget,
    PlanTargetMetric,
    PlanTargetRevision,
)
from apps.portal.models import (
    CorrectionRequest,
    ParticipantJournalEntry,
    ParticipantMessage,
    ParticipantUser,
    StaffPortalNote,
)
from apps.programs.models import Program
from apps.registration.models import RegistrationLink, RegistrationSubmission
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
    "It's hard right now and I don't know if I can keep going with this",
    "I don't know if this is working but I'm trying to stay with it anyway",
    "I almost didn't come today but I'm glad I made myself show up here",
    "I showed up today even though everything in me wanted to stay home instead",
    "I'm trying to take it one day at a time like we talked about last session",
    "It's getting a bit easier now that I have a plan to follow each week",
    "I actually wanted to come today which is new for me if I'm being honest",
    "Something feels different this time like maybe things are actually changing for me",
    "I told my friend about what we talked about and they said it made sense to them",
    "I'm starting to believe this might actually work out in the end for me somehow",
]

PARTICIPANT_REFLECTIONS = [
    "I think the biggest thing I'm learning is that it's okay to ask for help when I need it",
    "Today I realised I've actually come a long way since we first started working together",
    "I want to keep practising what we talked about because it really does make a difference",
    "I feel like I'm finally starting to understand what I need to do to move forward from here",
    "The hardest part is still showing up but once I'm here I always feel better about things",
]

PARTICIPANT_SUGGESTIONS = [
    "It would help to have more evening sessions for people who work during the day",
    "Maybe we could do a group session where people share what's working for them",
    "I think having a buddy system would help new people feel less alone at the start",
    "It would be nice to have some written materials I can take home and review later",
    "I wish there was a way to check in between sessions when things get really hard",
]


# ---------------------------------------------------------------------------
# Suggestion themes — grouped by program for executive dashboard & insights
# ---------------------------------------------------------------------------

PROGRAM_THEMES = {
    "Supported Employment": [
        {
            "name": "Evening & weekend session availability",
            "description": "Multiple participants have asked about sessions outside regular business hours to accommodate work schedules.",
            "status": "open",
            "source": "ai_generated",
            "keywords": "evening,weekend,hours,schedule,work,day",
        },
        {
            "name": "Peer mentoring from program alumni",
            "description": "Interest in connecting with people who have completed the program and found work.",
            "status": "in_progress",
            "source": "ai_generated",
            "keywords": "buddy,mentor,alumni,share,working,group",
            "addressed_note": "Recruiting two alumni volunteers to pilot monthly peer sessions.",
        },
    ],
    "Housing Stability": [
        {
            "name": "Faster response to maintenance requests",
            "description": "Participants report delays getting landlords to address repairs and want help advocating.",
            "status": "open",
            "source": "manual",
            "keywords": "maintenance,repair,landlord,response",
        },
        {
            "name": "Help navigating tenant rights",
            "description": "Several participants didn't know their rights around rent increases and eviction notices.",
            "status": "addressed",
            "source": "ai_generated",
            "keywords": "tenant,rights,eviction,rent,legal",
            "addressed_note": "Created a tenant rights info sheet and added it to intake package.",
        },
    ],
    "Youth Drop-In": [
        {
            "name": "More variety in group activities",
            "description": "Youth want more options beyond the current rotation — art, cooking, outdoor activities.",
            "status": "open",
            "source": "ai_generated",
            "keywords": "group,activities,variety,options",
        },
        {
            "name": "Quiet space for homework",
            "description": "Some youth want a calmer area to do homework before or after group activities.",
            "status": "in_progress",
            "source": "manual",
            "keywords": "homework,quiet,space,study",
            "addressed_note": "Testing a homework corner in the back room on Tuesdays and Thursdays.",
        },
        {
            "name": "Later drop-in hours",
            "description": "Older youth have asked about staying later, especially on Fridays.",
            "status": "open",
            "source": "ai_generated",
            "keywords": "hours,later,evening,stay",
        },
    ],
    "Newcomer Connections": [
        {
            "name": "Buddy system for newcomers",
            "description": "New arrivals feel isolated and want to be paired with someone who arrived earlier.",
            "status": "open",
            "source": "ai_generated",
            "keywords": "buddy,alone,new,paired,start",
        },
        {
            "name": "Childcare during sessions",
            "description": "Parents with young children struggle to attend without childcare support.",
            "status": "open",
            "source": "manual",
            "keywords": "childcare,children,attend,sessions",
        },
    ],
    "Community Kitchen": [
        {
            "name": "Recipe variety and dietary options",
            "description": "Participants want more recipes reflecting different cultural backgrounds and dietary needs.",
            "status": "in_progress",
            "source": "ai_generated",
            "keywords": "recipe,variety,dietary,cultural,options,materials",
            "addressed_note": "Surveying participants about dietary needs and cultural preferences.",
        },
        {
            "name": "Take-home portions for families",
            "description": "Several participants asked about taking extra portions home for family members.",
            "status": "open",
            "source": "ai_generated",
            "keywords": "take,home,family,portions",
        },
    ],
}


# ---------------------------------------------------------------------------
# Staff messages — operational messages between staff about participants
# ---------------------------------------------------------------------------

DEMO_STAFF_MESSAGES = [
    {
        "client": "DEMO-001",
        "left_by": "demo-frontdesk",
        "for_user": "demo-worker-1",
        "message": "Jordan called \u2014 wants to move Thursday's session to Friday if possible",
        "status": "unread",
        "days_ago": 1,
    },
    {
        "client": "DEMO-002",
        "left_by": "demo-frontdesk",
        "for_user": "demo-worker-1",
        "message": "Taylor dropped off updated resume at front desk",
        "status": "unread",
        "days_ago": 2,
    },
    {
        "client": "DEMO-004",
        "left_by": "demo-frontdesk",
        "for_user": "demo-worker-1",
        "message": "Sam's landlord called asking for a letter of support \u2014 said you'd know what it's about",
        "status": "read",
        "days_ago": 4,
    },
    {
        "client": "DEMO-007",
        "left_by": "demo-frontdesk",
        "for_user": "demo-worker-2",
        "message": "Priya's parent called \u2014 family may be away next week",
        "status": "unread",
        "days_ago": 1,
    },
    {
        "client": "DEMO-010",
        "left_by": "demo-frontdesk",
        "for_user": "demo-worker-2",
        "message": "Fatima asked if conversation circle can be moved to afternoon",
        "status": "unread",
        "days_ago": 3,
    },
    {
        "client": "DEMO-013",
        "left_by": "demo-worker-2",
        "for_user": "demo-worker-1",
        "message": "Checked in with Marcus at kitchen session \u2014 seemed quieter than usual, might be worth a follow-up",
        "status": "unread",
        "days_ago": 2,
    },
    {
        "client": "DEMO-005",
        "left_by": "demo-manager",
        "for_user": "demo-worker-1",
        "message": "Kai's housing tribunal date is March 4th \u2014 can you update the file?",
        "status": "read",
        "days_ago": 5,
    },
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

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Delete existing demo notes/plans/events and regenerate from scratch.",
        )

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
                # Also set preferred_name on the core model field
                if field_name == "Preferred Name":
                    client.preferred_name = value
                    client.save()
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

        # Always ensure at least one pending alert cancellation recommendation
        # exists for the Reviews queue (idempotent).
        try:
            worker1 = User.objects.get(username="demo-worker-1")
            workers_early = {"demo-worker-1": worker1}
            self._ensure_pending_alert_recommendation(workers_early, programs_by_name)
        except User.DoesNotExist:
            pass

        # Always ensure portal content exists (idempotent).
        # Runs before the early-return guard because seed.py creates the
        # ParticipantUser AFTER seed_demo_data returns on first run.
        try:
            worker1 = User.objects.get(username="demo-worker-1")
            workers_early = {"demo-worker-1": worker1}
            self._create_demo_portal_content(workers_early, timezone.now())
        except User.DoesNotExist:
            pass

        # Always ensure registration submissions exist (idempotent).
        try:
            worker1 = User.objects.get(username="demo-worker-1")
            workers_early = {"demo-worker-1": worker1}
            self._create_demo_registration_submissions(workers_early, programs_by_name, timezone.now())
        except User.DoesNotExist:
            pass

        # Check if rich data already exists
        force = options.get("force", False)
        demo_notes_exist = ProgressNote.objects.filter(
            client_file__record_id__startswith="DEMO-"
        ).exists()

        if demo_notes_exist and not force:
            self.stdout.write("  Demo rich data already exists. Skipping. (Use --force to regenerate.)")
            return

        if demo_notes_exist and force:
            # Delete suggestion themes for demo programs (cascades to SuggestionLink)
            demo_programs = Program.objects.filter(
                enrollments__client_file__record_id__startswith="DEMO-"
            ).distinct()
            theme_count_del = SuggestionTheme.objects.filter(
                program__in=demo_programs
            ).delete()[0]
            # Delete staff messages for demo clients
            staff_msg_count = StaffMessage.objects.filter(
                client_file__record_id__startswith="DEMO-"
            ).delete()[0]
            # Delete demo communications
            comm_count = Communication.objects.filter(
                client_file__record_id__startswith="DEMO-"
            ).delete()[0]
            # Delete demo notes (cascades to ProgressNoteTarget, MetricValue)
            note_count = ProgressNote.objects.filter(
                client_file__record_id__startswith="DEMO-"
            ).delete()[0]
            # Delete demo plans (cascades to PlanTarget, PlanTargetRevision, PlanTargetMetric)
            plan_count = PlanSection.objects.filter(
                client_file__record_id__startswith="DEMO-"
            ).delete()[0]
            # Delete demo events and alerts (Meeting cascades from Event)
            event_count = Event.objects.filter(
                client_file__record_id__startswith="DEMO-"
            ).delete()[0]
            alert_count = Alert.objects.filter(
                client_file__record_id__startswith="DEMO-"
            ).delete()[0]
            # Delete portal content (journal entries, messages, staff notes, corrections)
            journal_count = ParticipantJournalEntry.objects.filter(
                client_file__record_id__startswith="DEMO-"
            ).delete()[0]
            message_count = ParticipantMessage.objects.filter(
                client_file__record_id__startswith="DEMO-"
            ).delete()[0]
            staff_note_count = StaffPortalNote.objects.filter(
                client_file__record_id__startswith="DEMO-"
            ).delete()[0]
            correction_count = CorrectionRequest.objects.filter(
                client_file__record_id__startswith="DEMO-"
            ).delete()[0]
            # Delete registration submissions (keep the link itself)
            submission_count = RegistrationSubmission.objects.filter(
                registration_link__slug="demo"
            ).delete()[0]
            # Delete calendar feed tokens for demo workers
            demo_users = User.objects.filter(is_demo=True)
            CalendarFeedToken.objects.filter(user__in=demo_users).delete()
            self.stdout.write(
                f"  --force: Deleted {theme_count_del} themes, {staff_msg_count} staff messages, "
                f"{comm_count} communications, {note_count} notes, "
                f"{plan_count} plans, {event_count} events, {alert_count} alerts, "
                f"{journal_count} journal entries, {message_count} portal messages, "
                f"{staff_note_count} staff notes, {correction_count} correction requests, "
                f"{submission_count} registration submissions."
            )

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

        # --- Ensure one pending recommendation exists for Reviews queue demo ---
        self._ensure_pending_alert_recommendation(workers, programs_by_name)

        # --- Create demo groups ---
        self._create_demo_groups(workers, programs_by_name, now)

        # --- Create demo meetings ---
        self._create_demo_meetings(workers, programs_by_name, now)

        # --- Create demo communication logs ---
        self._create_demo_communications(workers, programs_by_name, now)

        # --- Create email/staff-sent communications with varied statuses ---
        self._create_demo_email_communications(workers, programs_by_name, now)

        # --- Create portal content (journal, messages, notes, corrections) ---
        self._create_demo_portal_content(workers, now)

        # --- Create registration submissions ---
        self._create_demo_registration_submissions(workers, programs_by_name, now)

        # --- Set contact info and messaging consent ---
        self._set_client_contact_and_consent(now)

        # --- Create calendar feed tokens for demo workers ---
        self._create_demo_calendar_feeds(workers)

        # --- Create suggestion themes and link to notes ---
        self._create_demo_suggestion_themes(workers, programs_by_name)

        # --- Create staff-to-staff messages ---
        self._create_demo_staff_messages(workers, programs_by_name, now)

        self.stdout.write(self.style.SUCCESS(
            "  Demo rich data seeded successfully (15 clients across 5 programs)."
        ))

    def _create_demo_registration_link(self, programs_by_name, created_by):
        """Create a public registration link with slug 'demo' for the project website."""
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
                "auto_approve": True,
                "created_by": created_by,
            },
        )

        # Keep the demo form minimal and welcoming — no custom field groups.
        # Core fields (name, email, phone, consent) are enough for registration.
        # Agencies can attach field groups to their own registration links.
        link.field_groups.clear()

        if created:
            self.stdout.write("  Created demo registration link (slug: demo)")
        else:
            # Update existing links to match current seed defaults
            link.title = "Program Registration"
            link.description = description
            link.auto_approve = True
            link.save(update_fields=["title", "description", "auto_approve"])
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

            # Set created_at to match backdate so notes appear historical.
            # Must use .update() because auto_now_add prevents .save().
            ProgressNote.objects.filter(pk=note.pk).update(created_at=backdate)

            # Add participant reflection to ~half of full notes
            needs_save = False
            if not is_quick and note_idx % 2 == 0:
                reflection_idx = min(
                    int(progress_fraction * len(PARTICIPANT_REFLECTIONS)),
                    len(PARTICIPANT_REFLECTIONS) - 1,
                )
                note.participant_reflection = PARTICIPANT_REFLECTIONS[reflection_idx]
                needs_save = True

            # Add participant suggestion to ~1/3 of full notes
            if not is_quick and note_idx % 3 == 1:
                suggestion_idx = note_idx % len(PARTICIPANT_SUGGESTIONS)
                note.participant_suggestion = PARTICIPANT_SUGGESTIONS[suggestion_idx]
                note.suggestion_priority = random.choice(
                    ["noted", "worth_exploring", "important"]
                )
                needs_save = True

            if needs_save:
                note.save()

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

    def _ensure_pending_alert_recommendation(self, workers, programs_by_name):
        """Ensure one pending cancellation recommendation exists for demo reviews."""
        client = ClientFile.objects.filter(record_id="DEMO-005").first()
        if not client:
            return

        program = programs_by_name.get("Housing Stability")
        recommender = workers.get("demo-worker-1")
        if not program or not recommender:
            return

        alert = Alert.objects.filter(
            client_file=client,
            author_program=program,
            status="default",
        ).order_by("-created_at").first()

        if not alert:
            alert = Alert.objects.create(
                client_file=client,
                content="Eviction risk — legal aid case pending. Monitor closely.",
                author=recommender,
                author_program=program,
            )

        if AlertCancellationRecommendation.objects.filter(alert=alert, status="pending").exists():
            return

        AlertCancellationRecommendation.objects.create(
            alert=alert,
            recommended_by=recommender,
            assessment=(
                "Client has had six weeks of stable housing check-ins with no new "
                "risk indicators. Recommend closing this alert and monitoring in regular notes."
            ),
        )

    # ------------------------------------------------------------------
    # Demo groups: groups and projects
    # ------------------------------------------------------------------

    def _create_demo_groups(self, workers, programs_by_name, now):
        """Create demo groups with sessions, attendance, and highlights."""
        worker1 = workers["demo-worker-1"]
        worker2 = workers["demo-worker-2"]

        vibes = ["solid", "great", "low", "solid", "great", "solid", "great", "solid"]

        def get_client(rid):
            return ClientFile.objects.filter(record_id=rid).first()

        # -------------------------------------------------------
        # Group 1: Wednesday After-School Circle (group)
        # Under Youth Drop-In, facilitated by Noor
        # -------------------------------------------------------
        youth_program = programs_by_name.get("Youth Drop-In")
        circle, created = Group.objects.get_or_create(
            name="Wednesday After-School Circle",
            defaults={
                "group_type": "group",
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
        # Group 2: Thursday Kitchen Session (group)
        # Under Community Kitchen, facilitated by Noor
        # -------------------------------------------------------
        kitchen_program = programs_by_name.get("Community Kitchen")
        kitchen, created = Group.objects.get_or_create(
            name="Thursday Kitchen Session",
            defaults={
                "group_type": "group",
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

    # ------------------------------------------------------------------
    # Demo meetings: scheduled, completed, no-show across programs
    # ------------------------------------------------------------------

    def _create_demo_meetings(self, workers, programs_by_name, now):
        """Create demo meetings to populate the meeting list and calendar feed."""
        worker1 = workers["demo-worker-1"]
        worker2 = workers["demo-worker-2"]

        meeting_data = [
            # (record_id, worker, program, title, days_offset, location, status, duration, reminder_status)
            # days_offset: positive = future, negative = past
            {
                "record_id": "DEMO-001",
                "worker": worker1,
                "program": "Supported Employment",
                "days_offset": 3,
                "location": "Office A — 2nd floor",
                "status": "scheduled",
                "duration": 45,
                "reminder_status": "sent",
            },
            {
                "record_id": "DEMO-002",
                "worker": worker1,
                "program": "Supported Employment",
                "days_offset": -5,
                "location": "Community Room",
                "status": "completed",
                "duration": 60,
                "reminder_status": "sent",
            },
            {
                "record_id": "DEMO-002",
                "worker": worker1,
                "program": "Supported Employment",
                "days_offset": 7,
                "location": "Office A — 2nd floor",
                "status": "scheduled",
                "duration": 45,
                "reminder_status": "not_sent",
            },
            {
                "record_id": "DEMO-004",
                "worker": worker1,
                "program": "Housing Stability",
                "days_offset": 5,
                "location": "Housing Support Office",
                "status": "scheduled",
                "duration": 60,
                "reminder_status": "not_sent",
            },
            {
                "record_id": "DEMO-005",
                "worker": worker1,
                "program": "Housing Stability",
                "days_offset": -2,
                "location": "Housing Support Office",
                "status": "no_show",
                "duration": 45,
                "reminder_status": "sent",
            },
            {
                "record_id": "DEMO-006",
                "worker": worker1,
                "program": "Housing Stability",
                "days_offset": -10,
                "location": "Coffee shop — Bloor & Spadina",
                "status": "completed",
                "duration": 30,
                "reminder_status": "sent",
            },
            {
                "record_id": "DEMO-007",
                "worker": worker2,
                "program": "Youth Drop-In",
                "days_offset": 4,
                "location": "Youth Room",
                "status": "scheduled",
                "duration": 30,
                "reminder_status": "not_sent",
            },
            {
                "record_id": "DEMO-010",
                "worker": worker2,
                "program": "Newcomer Connections",
                "days_offset": 6,
                "location": "Settlement Office",
                "status": "scheduled",
                "duration": 60,
                "reminder_status": "not_sent",
            },
            {
                "record_id": "DEMO-011",
                "worker": worker2,
                "program": "Newcomer Connections",
                "days_offset": -4,
                "location": "Community Centre — Room 3",
                "status": "completed",
                "duration": 45,
                "reminder_status": "sent",
            },
            {
                "record_id": "DEMO-013",
                "worker": worker2,
                "program": "Community Kitchen",
                "days_offset": 10,
                "location": "Kitchen",
                "status": "scheduled",
                "duration": 30,
                "reminder_status": "not_sent",
            },
            # --- Additional meetings for full coverage ---
            # DEMO-003 (Avery) — discharge planning, multi-attendee
            {
                "record_id": "DEMO-003",
                "worker": worker1,
                "program": "Supported Employment",
                "days_offset": -14,
                "location": "Office A — 2nd floor",
                "status": "completed",
                "duration": 30,
                "reminder_status": "sent",
            },
            {
                "record_id": "DEMO-003",
                "attendees": [worker1, worker2],
                "program": "Supported Employment",
                "days_offset": -3,
                "location": "Conference Room B",
                "status": "completed",
                "duration": 45,
                "reminder_status": "sent",
            },
            # DEMO-008 (Maya) — return after withdrawal
            {
                "record_id": "DEMO-008",
                "worker": worker2,
                "program": "Youth Drop-In",
                "days_offset": -8,
                "location": "Youth Room",
                "status": "completed",
                "duration": 30,
                "reminder_status": "sent",
            },
            {
                "record_id": "DEMO-008",
                "worker": worker2,
                "program": "Youth Drop-In",
                "days_offset": 5,
                "location": "Youth Room",
                "status": "scheduled",
                "duration": 30,
                "reminder_status": "not_sent",
            },
            # DEMO-009 (Zara) — cancelled + completed
            {
                "record_id": "DEMO-009",
                "worker": worker2,
                "program": "Youth Drop-In",
                "days_offset": -12,
                "location": "Youth Room",
                "status": "cancelled",
                "duration": 30,
                "reminder_status": "sent",
            },
            {
                "record_id": "DEMO-009",
                "worker": worker2,
                "program": "Youth Drop-In",
                "days_offset": -6,
                "location": "Library study room",
                "status": "completed",
                "duration": 45,
                "reminder_status": "sent",
            },
            # DEMO-012 (Carlos) — multi-attendee coordination
            {
                "record_id": "DEMO-012",
                "attendees": [worker2, worker1],
                "program": "Newcomer Connections",
                "days_offset": -9,
                "location": "Settlement Office",
                "status": "completed",
                "duration": 60,
                "reminder_status": "sent",
            },
            {
                "record_id": "DEMO-012",
                "worker": worker2,
                "program": "Newcomer Connections",
                "days_offset": 8,
                "location": "Settlement Office",
                "status": "scheduled",
                "duration": 45,
                "reminder_status": "not_sent",
            },
            # DEMO-014 (Liam) — kitchen follow-up
            {
                "record_id": "DEMO-014",
                "worker": worker2,
                "program": "Community Kitchen",
                "days_offset": -7,
                "location": "Kitchen",
                "status": "completed",
                "duration": 30,
                "reminder_status": "sent",
            },
            # DEMO-015 (Nadia) — cancelled by client
            {
                "record_id": "DEMO-015",
                "worker": worker2,
                "program": "Community Kitchen",
                "days_offset": -5,
                "location": "Kitchen",
                "status": "cancelled",
                "duration": 45,
                "reminder_status": "sent",
                "reminder_status_reason": "Client called to cancel — feeling unwell.",
            },
        ]

        created = 0
        for md in meeting_data:
            client = ClientFile.objects.filter(record_id=md["record_id"]).first()
            if not client:
                continue
            program = programs_by_name.get(md["program"])
            if not program:
                continue

            timestamp = now + timedelta(
                days=md["days_offset"],
                hours=random.choice([9, 10, 11, 13, 14, 15]),
            )

            # Create the underlying Event
            event = Event.objects.create(
                client_file=client,
                title="Meeting",
                start_timestamp=timestamp,
                author_program=program,
            )
            # Backdate created_at for past meetings
            if md["days_offset"] < 0:
                Event.objects.filter(pk=event.pk).update(
                    created_at=timestamp - timedelta(days=2)
                )

            # Create the Meeting
            meeting = Meeting.objects.create(
                event=event,
                location=md["location"],
                duration_minutes=md["duration"],
                status=md["status"],
                reminder_sent=md["reminder_status"] == "sent",
                reminder_status=md["reminder_status"],
                reminder_status_reason=md.get("reminder_status_reason", ""),
            )
            # Support single worker or explicit attendee list
            attendees = md.get("attendees", [md["worker"]] if "worker" in md else [])
            for a in attendees:
                meeting.attendees.add(a)
            created += 1

        self.stdout.write(f"  Demo meetings: {created} created.")

    # ------------------------------------------------------------------
    # Demo communications: phone calls, texts, in-person across programs
    # ------------------------------------------------------------------

    def _create_demo_communications(self, workers, programs_by_name, now):
        """Create demo communication logs for the client timeline."""
        worker1 = workers["demo-worker-1"]
        worker2 = workers["demo-worker-2"]

        comm_data = [
            # Supported Employment — Casey
            {
                "record_id": "DEMO-001",
                "worker": worker1,
                "program": "Supported Employment",
                "comms": [
                    {"channel": "phone", "direction": "outbound", "days_ago": 25,
                     "subject": "Interview prep follow-up",
                     "content": "Called to confirm mock interview time. Jordan feeling nervous but excited."},
                    {"channel": "sms", "direction": "outbound", "days_ago": 18,
                     "subject": "", "content": "Reminder: bring your updated resume to Thursday's session."},
                    {"channel": "sms", "direction": "inbound", "days_ago": 17,
                     "subject": "", "content": "Thanks! Will do."},
                    {"channel": "phone", "direction": "inbound", "days_ago": 8,
                     "subject": "Interview callback",
                     "content": "Jordan called — got a callback for the retail position. Very excited."},
                ],
            },
            {
                "record_id": "DEMO-002",
                "worker": worker1,
                "program": "Supported Employment",
                "comms": [
                    {"channel": "phone", "direction": "outbound", "days_ago": 20,
                     "subject": "Check-in after missed session",
                     "content": "Left voicemail — Taylor missed Tuesday's session. Confirmed reschedule for Friday."},
                    {"channel": "phone", "direction": "outbound", "days_ago": 6,
                     "subject": "Pre-interview encouragement",
                     "content": "Called to go over interview tips. Taylor still anxious but knows the material well."},
                ],
            },
            # Housing Stability — Casey
            {
                "record_id": "DEMO-004",
                "worker": worker1,
                "program": "Housing Stability",
                "comms": [
                    {"channel": "phone", "direction": "outbound", "days_ago": 30,
                     "subject": "Housing application status",
                     "content": "Called to check on subsidised housing application. Still on wait list — 4-6 months."},
                    {"channel": "sms", "direction": "outbound", "days_ago": 15,
                     "subject": "", "content": "Hi Sam — just checking in. How's the new place going?"},
                    {"channel": "sms", "direction": "inbound", "days_ago": 14,
                     "subject": "", "content": "Good thanks! Neighbours are nice. Still getting settled."},
                    {"channel": "in_person", "direction": "outbound", "days_ago": 5,
                     "subject": "Drop-in check-in",
                     "content": "Sam dropped by the office. Settling in well. Discussed budgeting for groceries."},
                ],
            },
            {
                "record_id": "DEMO-005",
                "worker": worker1,
                "program": "Housing Stability",
                "comms": [
                    {"channel": "phone", "direction": "outbound", "days_ago": 22,
                     "subject": "Legal aid referral follow-up",
                     "content": "Called to check if Kai connected with legal aid. Still waiting for callback."},
                    {"channel": "phone", "direction": "outbound", "days_ago": 3,
                     "subject": "Missed meeting follow-up",
                     "content": "Called after no-show. Kai apologised — had a family emergency. Rescheduled."},
                ],
            },
            # Youth Drop-In — Noor
            {
                "record_id": "DEMO-007",
                "worker": worker2,
                "program": "Youth Drop-In",
                "comms": [
                    {"channel": "phone", "direction": "outbound", "days_ago": 28,
                     "subject": "Parent contact — field trip",
                     "content": "Called Elena (parent) about upcoming field trip. Permission form signed."},
                    {"channel": "in_person", "direction": "outbound", "days_ago": 10,
                     "subject": "Quick check-in",
                     "content": "Jayden pulled me aside after group. Wants to help facilitate next week's activity."},
                ],
            },
            {
                "record_id": "DEMO-008",
                "worker": worker2,
                "program": "Youth Drop-In",
                "comms": [
                    {"channel": "phone", "direction": "outbound", "days_ago": 35,
                     "subject": "Outreach — missed 3 weeks",
                     "content": "Called Maya's dad. Maya has been anxious about group. Encouraged gentle return."},
                    {"channel": "in_person", "direction": "outbound", "days_ago": 12,
                     "subject": "Welcome back check-in",
                     "content": "Maya came back today. Quiet but stayed the whole session. Small step forward."},
                ],
            },
            # Newcomer Connections — Noor
            {
                "record_id": "DEMO-010",
                "worker": worker2,
                "program": "Newcomer Connections",
                "comms": [
                    {"channel": "phone", "direction": "outbound", "days_ago": 40,
                     "subject": "Doctor appointment support",
                     "content": "Called to offer to accompany Amara to walk-in clinic. She said she'll try on her own first."},
                    {"channel": "phone", "direction": "inbound", "days_ago": 32,
                     "subject": "Doctor visit success",
                     "content": "Amara called — went to the clinic by herself! Was nervous but managed it. Big milestone."},
                    {"channel": "sms", "direction": "outbound", "days_ago": 8,
                     "subject": "", "content": "Community event at the library this Saturday 2pm. Would you like to come?"},
                    {"channel": "sms", "direction": "inbound", "days_ago": 7,
                     "subject": "", "content": "Yes I will come! Can I bring my husband?"},
                ],
            },
            {
                "record_id": "DEMO-011",
                "worker": worker2,
                "program": "Newcomer Connections",
                "comms": [
                    {"channel": "phone", "direction": "outbound", "days_ago": 20,
                     "subject": "Check-in after referral",
                     "content": "Called to follow up on women's support group referral. Fatima attended once — found it helpful."},
                ],
            },
            # Community Kitchen — Noor
            {
                "record_id": "DEMO-013",
                "worker": worker2,
                "program": "Community Kitchen",
                "comms": [
                    {"channel": "phone", "direction": "inbound", "days_ago": 15,
                     "subject": "Recipe feedback",
                     "content": "Priya called to say her kids loved the lentil soup recipe. Asked for the banana bread one too."},
                    {"channel": "in_person", "direction": "outbound", "days_ago": 4,
                     "subject": "Session feedback",
                     "content": "Quick chat after kitchen session. Priya feeling more confident with meal planning."},
                ],
            },
            {
                "record_id": "DEMO-014",
                "worker": worker2,
                "program": "Community Kitchen",
                "comms": [
                    {"channel": "in_person", "direction": "outbound", "days_ago": 9,
                     "subject": "Volunteer role discussion",
                     "content": "Liam asked about becoming a regular volunteer helper. Discussed responsibilities."},
                ],
            },
        ]

        created = 0
        for group in comm_data:
            client = ClientFile.objects.filter(record_id=group["record_id"]).first()
            if not client:
                continue
            program = programs_by_name.get(group["program"])
            if not program:
                continue

            for c in group["comms"]:
                comm = Communication(
                    client_file=client,
                    direction=c["direction"],
                    channel=c["channel"],
                    method="manual_log",
                    subject=c.get("subject", ""),
                    logged_by=group["worker"],
                    author_program=program,
                    delivery_status="delivered",
                )
                comm.content = c.get("content", "")
                comm.save()
                # Backdate created_at
                backdate = now - timedelta(
                    days=c["days_ago"], hours=random.randint(8, 17)
                )
                Communication.objects.filter(pk=comm.pk).update(created_at=backdate)
                created += 1

        self.stdout.write(f"  Demo communications: {created} logged.")

    # ------------------------------------------------------------------
    # Email and staff-sent communications with varied delivery statuses
    # ------------------------------------------------------------------

    def _create_demo_email_communications(self, workers, programs_by_name, now):
        """Create email-channel, staff-sent, and system-sent communications.

        Also fills the 5 clients that had zero communications (DEMO-003, 006,
        009, 012, 015) and adds delivery-status variety (bounced, failed,
        pending, blocked) that was missing from the manual-log comms.
        """
        worker1 = workers["demo-worker-1"]
        worker2 = workers["demo-worker-2"]

        email_comm_data = [
            # ---- Staff-sent emails (clients with email addresses) ----
            # DEMO-001 (Jordan) — Supported Employment
            {
                "record_id": "DEMO-001",
                "worker": worker1,
                "program": "Supported Employment",
                "comms": [
                    {"channel": "email", "direction": "outbound", "method": "staff_sent",
                     "days_ago": 22, "subject": "Interview prep resources",
                     "content": "Hi Jordan — attached are the practice questions we talked about. You've got this!",
                     "delivery_status": "delivered"},
                    {"channel": "email", "direction": "outbound", "method": "staff_sent",
                     "days_ago": 10, "subject": "Resume workshop this Thursday",
                     "content": "Just a reminder about the resume workshop at 2 pm on Thursday. Bring a printed copy of your current resume.",
                     "delivery_status": "delivered"},
                ],
            },
            # DEMO-003 (Avery) — Supported Employment — currently zero comms
            {
                "record_id": "DEMO-003",
                "worker": worker1,
                "program": "Supported Employment",
                "comms": [
                    {"channel": "email", "direction": "outbound", "method": "staff_sent",
                     "days_ago": 18, "subject": "Part-time schedule update",
                     "content": "Hi Avery — your employer confirmed the new hours starting next Monday. Let me know if you have questions.",
                     "delivery_status": "delivered"},
                    {"channel": "email", "direction": "outbound", "method": "staff_sent",
                     "days_ago": 5, "subject": "Program completion survey",
                     "content": "As you near the end of the program, we'd love your feedback. Here's a short survey link.",
                     "delivery_status": "bounced",
                     "delivery_status_display": "Mailbox full — message bounced back."},
                    {"channel": "phone", "direction": "inbound", "method": "manual_log",
                     "days_ago": 12, "subject": "Reference letter request",
                     "content": "Avery called asking for a reference letter for a new job application. Will prepare it this week.",
                     "delivery_status": "delivered", "outcome": "reached"},
                ],
            },
            # DEMO-009 (Zara) — Youth Drop-In — currently zero comms
            {
                "record_id": "DEMO-009",
                "worker": worker2,
                "program": "Youth Drop-In",
                "comms": [
                    {"channel": "email", "direction": "outbound", "method": "staff_sent",
                     "days_ago": 20, "subject": "Field trip permission form",
                     "content": "Hi — please find the attached permission form for next week's field trip. Have a parent sign and bring it to the next session.",
                     "delivery_status": "delivered"},
                    {"channel": "email", "direction": "outbound", "method": "staff_sent",
                     "days_ago": 7, "subject": "Homework help session moved to Wednesday",
                     "content": "The Tuesday homework help session is moving to Wednesday this week only. Same time, same room.",
                     "delivery_status": "pending"},
                    {"channel": "phone", "direction": "inbound", "method": "manual_log",
                     "days_ago": 14, "subject": "Parent called about schedule",
                     "content": "Zara's mum called to ask about the holiday schedule. Confirmed the program runs through the break.",
                     "delivery_status": "delivered", "outcome": "reached"},
                ],
            },
            # DEMO-012 (Carlos) — Newcomer Connections — currently zero comms
            {
                "record_id": "DEMO-012",
                "worker": worker2,
                "program": "Newcomer Connections",
                "comms": [
                    {"channel": "email", "direction": "outbound", "method": "staff_sent",
                     "days_ago": 30, "subject": "Welcome to the program",
                     "content": "Hi Carlos — welcome to Newcomer Connections! Your first appointment is next Tuesday at 10 am.",
                     "delivery_status": "delivered"},
                    {"channel": "email", "direction": "outbound", "method": "staff_sent",
                     "days_ago": 16, "subject": "Language class confirmation",
                     "content": "You're registered for the intermediate English class starting March 3. Location: Community Centre, Room 4.",
                     "delivery_status": "delivered"},
                    {"channel": "email", "direction": "outbound", "method": "staff_sent",
                     "days_ago": 4, "subject": "Document checklist for PR application",
                     "content": "Attached is the checklist we discussed. Bring everything to our next meeting and we'll go through it together.",
                     "delivery_status": "failed",
                     "delivery_status_display": "Email address may no longer be valid."},
                ],
            },
            # DEMO-014 (Liam) — Community Kitchen — has 1 in-person, add emails
            {
                "record_id": "DEMO-014",
                "worker": worker2,
                "program": "Community Kitchen",
                "comms": [
                    {"channel": "email", "direction": "outbound", "method": "staff_sent",
                     "days_ago": 24, "subject": "Volunteer schedule for February",
                     "content": "Hi Liam — here's the volunteer schedule for next month. You're down for Tuesday and Thursday sessions.",
                     "delivery_status": "delivered"},
                    {"channel": "email", "direction": "outbound", "method": "staff_sent",
                     "days_ago": 6, "subject": "Food handler certificate information",
                     "content": "If you're interested in the food handler certification, the next course is March 15. The agency covers the fee.",
                     "delivery_status": "delivered"},
                ],
            },
            # ---- Manual-log comms for clients with no phone/email ----
            # DEMO-006 (Jesse) — Housing Stability — no phone, no email
            {
                "record_id": "DEMO-006",
                "worker": worker1,
                "program": "Housing Stability",
                "comms": [
                    {"channel": "in_person", "direction": "outbound", "method": "manual_log",
                     "days_ago": 18, "subject": "Drop-in visit at shelter",
                     "content": "Visited Jesse at the shelter. Looking better — mentioned sleeping through the night for the first time in weeks.",
                     "delivery_status": "delivered"},
                    {"channel": "in_person", "direction": "outbound", "method": "manual_log",
                     "days_ago": 6, "subject": "Met at agency front desk",
                     "content": "Jesse came to the office to pick up housing application forms. Seemed more hopeful today.",
                     "delivery_status": "delivered"},
                ],
            },
            # DEMO-015 (Nadia) — Community Kitchen — currently zero comms
            {
                "record_id": "DEMO-015",
                "worker": worker2,
                "program": "Community Kitchen",
                "comms": [
                    {"channel": "phone", "direction": "outbound", "method": "manual_log",
                     "days_ago": 16, "subject": "Session reminder",
                     "content": "Left voicemail reminding Nadia about Saturday's session. Mentioned we'll be making pasta from scratch.",
                     "delivery_status": "delivered", "outcome": "voicemail"},
                    {"channel": "sms", "direction": "outbound", "method": "manual_log",
                     "days_ago": 10, "subject": "",
                     "content": "Hi Nadia — here's the grocery list for this week's session. See you Saturday!",
                     "delivery_status": "delivered"},
                    {"channel": "in_person", "direction": "outbound", "method": "manual_log",
                     "days_ago": 3, "subject": "Post-session chat",
                     "content": "Quick chat after session. Nadia said she made the soup at home and her roommate loved it.",
                     "delivery_status": "delivered"},
                ],
            },
            # ---- System-sent messages (meeting reminders) ----
            {
                "record_id": "DEMO-004",
                "worker": worker1,
                "program": "Housing Stability",
                "comms": [
                    {"channel": "sms", "direction": "outbound", "method": "system_sent",
                     "days_ago": 6, "subject": "Meeting reminder",
                     "content": "Reminder: You have a meeting with Casey at Housing Support Office tomorrow at 10 am.",
                     "delivery_status": "delivered",
                     "external_id": "demo-sms-001"},
                ],
            },
            {
                "record_id": "DEMO-002",
                "worker": worker1,
                "program": "Supported Employment",
                "comms": [
                    {"channel": "sms", "direction": "outbound", "method": "system_sent",
                     "days_ago": 6, "subject": "Meeting reminder",
                     "content": "Reminder: You have a meeting at Community Room on Friday at 2 pm.",
                     "delivery_status": "sent",
                     "external_id": "demo-sms-002"},
                ],
            },
            {
                "record_id": "DEMO-010",
                "worker": worker2,
                "program": "Newcomer Connections",
                "comms": [
                    {"channel": "sms", "direction": "outbound", "method": "staff_sent",
                     "days_ago": 9, "subject": "",
                     "content": "Community potluck this Saturday at 2 pm — would love to see you there!",
                     "delivery_status": "blocked",
                     "delivery_status_display": "Carrier rejected the message."},
                ],
            },
            # DEMO-007 (Jayden) — staff-sent SMS
            {
                "record_id": "DEMO-007",
                "worker": worker2,
                "program": "Youth Drop-In",
                "comms": [
                    {"channel": "sms", "direction": "outbound", "method": "staff_sent",
                     "days_ago": 5, "subject": "",
                     "content": "See you at tomorrow's session! We're doing the mural project.",
                     "delivery_status": "sent"},
                ],
            },
        ]

        created = 0
        for group in email_comm_data:
            client = ClientFile.objects.filter(record_id=group["record_id"]).first()
            if not client:
                continue
            program = programs_by_name.get(group["program"])
            if not program:
                continue

            for c in group["comms"]:
                comm = Communication(
                    client_file=client,
                    direction=c["direction"],
                    channel=c["channel"],
                    method=c.get("method", "manual_log"),
                    subject=c.get("subject", ""),
                    outcome=c.get("outcome", ""),
                    logged_by=group["worker"],
                    author_program=program,
                    delivery_status=c.get("delivery_status", "delivered"),
                    delivery_status_display=c.get("delivery_status_display", ""),
                    external_id=c.get("external_id", ""),
                )
                comm.content = c.get("content", "")
                comm.save()
                # Backdate created_at
                backdate = now - timedelta(
                    days=c["days_ago"], hours=random.randint(8, 17)
                )
                Communication.objects.filter(pk=comm.pk).update(created_at=backdate)
                created += 1

        self.stdout.write(f"  Email/staff-sent communications: {created} logged.")

    # ------------------------------------------------------------------
    # Portal content: journal entries, messages, staff notes, corrections
    # ------------------------------------------------------------------

    def _create_demo_portal_content(self, workers, now):
        """Create portal content for DEMO-001 (Jordan Rivera).

        Only DEMO-001 has a ParticipantUser account. This method is called
        from the idempotent section of handle() so it works even when
        seed.py creates the ParticipantUser after seed_demo_data returns.
        """
        participant = ParticipantUser.objects.filter(
            client_file__record_id="DEMO-001"
        ).first()
        if not participant:
            self.stdout.write("  Portal content: DEMO-001 has no portal account. Skipping.")
            return

        # Skip if journal entries already exist (idempotent)
        if ParticipantJournalEntry.objects.filter(
            participant_user=participant
        ).exists():
            self.stdout.write("  Portal content: already exists. Skipping.")
            return

        client = participant.client_file
        worker1 = workers.get("demo-worker-1")

        # Look up Jordan's plan targets for linking
        jordan_targets = list(PlanTarget.objects.filter(
            plan_section__client_file=client
        ))
        interview_target = next(
            (t for t in jordan_targets if "interview" in (t.name or "").lower()),
            jordan_targets[0] if jordan_targets else None,
        )
        applications_target = next(
            (t for t in jordan_targets if "application" in (t.name or "").lower()),
            jordan_targets[1] if len(jordan_targets) > 1 else None,
        )

        # --- Journal entries ---
        journal_data = [
            {
                "days_ago": 52,
                "target": interview_target,
                "content": (
                    "Had my first mock interview today. It was terrifying but Casey "
                    "said I did okay. I keep replaying the parts I messed up."
                ),
            },
            {
                "days_ago": 40,
                "target": None,
                "content": (
                    "Bad day. Couldn't get out of bed until noon. Feeling like "
                    "nobody's going to hire me. But I made it to the drop-in at "
                    "least."
                ),
            },
            {
                "days_ago": 28,
                "target": applications_target,
                "content": (
                    "Sent out three applications this week! Two online and one in "
                    "person at the cafe on Queen Street. The in-person one felt "
                    "weird but I did it."
                ),
            },
            {
                "days_ago": 15,
                "target": interview_target,
                "content": (
                    "Got called back for the retail job! Real interview next "
                    "Wednesday. Casey is going to do one more practice run with me. "
                    "Nervous but also kind of excited?"
                ),
            },
            {
                "days_ago": 6,
                "target": None,
                "content": (
                    "Interview went better than I thought. I remembered to breathe "
                    "and make eye contact like we practised. Haven't heard back yet "
                    "though."
                ),
            },
            {
                "days_ago": 1,
                "target": None,
                "content": (
                    "Cooking class was fun — made lentil soup and brought some "
                    "home. Having something good to eat when I got back made the "
                    "whole day feel better."
                ),
            },
        ]

        journal_count = 0
        for jd in journal_data:
            entry = ParticipantJournalEntry(
                participant_user=participant,
                client_file=client,
                plan_target=jd["target"],
            )
            entry.content = jd["content"]
            entry.save()
            backdate = now - timedelta(days=jd["days_ago"], hours=random.randint(18, 22))
            ParticipantJournalEntry.objects.filter(pk=entry.pk).update(created_at=backdate)
            journal_count += 1

        # --- Participant messages ---
        message_data = [
            {
                "days_ago": 45,
                "message_type": "general",
                "archived_days_ago": 30,
                "content": (
                    "Hi Casey, I lost the bus route info you gave me. Can you send "
                    "it again?"
                ),
            },
            {
                "days_ago": 20,
                "message_type": "pre_session",
                "archived_days_ago": 18,
                "content": (
                    "Before our Thursday meeting — I wanted to let you know I've "
                    "been feeling really anxious this week. Just so you know."
                ),
            },
            {
                "days_ago": 8,
                "message_type": "general",
                "archived_days_ago": None,
                "content": (
                    "Is there a dress code for the interview? I don't have dress "
                    "shoes. Is that going to be a problem?"
                ),
            },
            {
                "days_ago": 2,
                "message_type": "pre_session",
                "archived_days_ago": None,
                "content": (
                    "I'd like to talk about what happens after I get a job. Like, "
                    "do I still come here?"
                ),
            },
        ]

        msg_count = 0
        for md in message_data:
            msg = ParticipantMessage(
                participant_user=participant,
                client_file=client,
                message_type=md["message_type"],
            )
            msg.content = md["content"]
            msg.save()
            backdate = now - timedelta(days=md["days_ago"], hours=random.randint(8, 20))
            updates = {"created_at": backdate}
            if md["archived_days_ago"] is not None:
                updates["archived_at"] = now - timedelta(days=md["archived_days_ago"])
            ParticipantMessage.objects.filter(pk=msg.pk).update(**updates)
            msg_count += 1

        # --- Staff portal notes ---
        note_data = [
            {
                "days_ago": 38,
                "content": (
                    "Great work showing up every week, Jordan. Consistency matters "
                    "and you're building a real routine."
                ),
            },
            {
                "days_ago": 14,
                "content": (
                    "You've been doing amazing with the interview prep. Remember — "
                    "they called YOU back. That says something."
                ),
            },
            {
                "days_ago": 3,
                "content": (
                    "So proud of how the interview went. Whatever happens with this "
                    "one, you showed you can do it. We'll keep going."
                ),
            },
        ]

        note_count = 0
        for nd in note_data:
            note = StaffPortalNote(
                client_file=client,
                from_user=worker1,
                is_active=True,
            )
            note.content = nd["content"]
            note.save()
            backdate = now - timedelta(days=nd["days_ago"], hours=random.randint(9, 16))
            StaffPortalNote.objects.filter(pk=note.pk).update(created_at=backdate)
            note_count += 1

        # --- Correction requests ---
        correction_data = [
            {
                "days_ago": 10,
                "data_type": "goal",
                "object_id": interview_target.pk if interview_target else 1,
                "status": "corrected",
                "resolved_days_ago": 7,
                "description": (
                    "It says my goal is to 'build interview skills' but I'd "
                    "rather it say 'feel ready for interviews'. Can you change it?"
                ),
                "staff_response": "Updated the goal wording as requested.",
            },
            {
                "days_ago": 3,
                "data_type": "metric",
                "object_id": 1,  # placeholder — metric value PK
                "status": "pending",
                "resolved_days_ago": None,
                "description": (
                    "The confidence score from last week seems wrong — I said 7 "
                    "but it shows 5. Can someone check?"
                ),
                "staff_response": "",
            },
        ]

        correction_count = 0
        for cd in correction_data:
            req = CorrectionRequest(
                participant_user=participant,
                client_file=client,
                data_type=cd["data_type"],
                object_id=cd["object_id"],
                status=cd["status"],
                staff_response=cd["staff_response"],
            )
            req.description = cd["description"]
            req.save()
            updates = {
                "created_at": now - timedelta(days=cd["days_ago"]),
            }
            if cd["resolved_days_ago"] is not None:
                updates["resolved_at"] = now - timedelta(days=cd["resolved_days_ago"])
            CorrectionRequest.objects.filter(pk=req.pk).update(**updates)
            correction_count += 1

        self.stdout.write(
            f"  Portal content: {journal_count} journal entries, "
            f"{msg_count} messages, {note_count} staff notes, "
            f"{correction_count} correction requests."
        )

    # ------------------------------------------------------------------
    # Registration submissions with varied review statuses
    # ------------------------------------------------------------------

    def _create_demo_registration_submissions(self, workers, programs_by_name, now):
        """Create demo registration submissions for the 'demo' registration link."""
        link = RegistrationLink.objects.filter(slug="demo").first()
        if not link:
            self.stdout.write("  Registration submissions: no demo link found. Skipping.")
            return

        # Skip if submissions already exist (idempotent)
        if RegistrationSubmission.objects.filter(registration_link=link).exists():
            self.stdout.write("  Registration submissions: already exist. Skipping.")
            return

        reviewer = User.objects.filter(is_admin=True).first() or workers.get("demo-worker-1")

        submission_data = [
            {
                "first_name": "Aisha", "last_name": "Nkomo",
                "email": "aisha.nkomo@example.com", "phone": "4165552001",
                "status": "approved", "days_ago": 14, "reviewed_days_ago": 12,
                "review_notes": "Documents verified. Assigned to Casey.",
                "field_values": {"how_heard": "Community poster", "notes": "Available weekday mornings."},
            },
            {
                "first_name": "Luca", "last_name": "Bianchi",
                "email": "luca.bianchi@example.com", "phone": "6475552002",
                "status": "approved", "days_ago": 10, "reviewed_days_ago": 8,
                "review_notes": "Previous participant returning. Welcome back.",
                "field_values": {"how_heard": "Previous enrolment", "notes": "Was in the program last year."},
            },
            {
                "first_name": "Min-Ji", "last_name": "Park",
                "email": "minji.park@example.com", "phone": "9055552003",
                "status": "pending", "days_ago": 3, "reviewed_days_ago": None,
                "review_notes": "",
                "field_values": {"how_heard": "Friend", "notes": "Looking forward to the program."},
            },
            {
                "first_name": "Tariq", "last_name": "Hassan",
                "email": "tariq.hassan@example.com", "phone": "4165552004",
                "status": "pending", "days_ago": 1, "reviewed_days_ago": None,
                "review_notes": "",
                "field_values": {"how_heard": "Online search", "notes": ""},
            },
            {
                "first_name": "Svetlana", "last_name": "Petrov",
                "email": "svetlana.petrov@example.com", "phone": "6475552005",
                "status": "rejected", "days_ago": 7, "reviewed_days_ago": 5,
                "review_notes": "Referred to partner agency — not in our catchment area.",
                "field_values": {"how_heard": "Community agency", "notes": "Lives in Mississauga."},
            },
            {
                "first_name": "Derek", "last_name": "Okafor",
                "email": "derek.okafor@example.com", "phone": "9055552006",
                "status": "waitlist", "days_ago": 5, "reviewed_days_ago": 4,
                "review_notes": "Program at capacity. Added to wait list for next cohort.",
                "field_values": {"how_heard": "Shelter staff", "notes": "Currently staying at Fred Victor."},
            },
        ]

        created = 0
        for sd in submission_data:
            sub = RegistrationSubmission(
                registration_link=link,
                field_values=sd["field_values"],
                status=sd["status"],
            )
            sub.first_name = sd["first_name"]
            sub.last_name = sd["last_name"]
            sub.email = sd["email"]
            sub.phone = sd["phone"]
            sub.save()

            # Backdate submitted_at and optionally set reviewed_at/reviewed_by
            updates = {
                "submitted_at": now - timedelta(days=sd["days_ago"], hours=random.randint(8, 18)),
            }
            if sd["reviewed_days_ago"] is not None:
                updates["reviewed_at"] = now - timedelta(days=sd["reviewed_days_ago"])
                updates["reviewed_by"] = reviewer
            RegistrationSubmission.objects.filter(pk=sub.pk).update(**updates)
            created += 1

        self.stdout.write(f"  Registration submissions: {created} created.")

    # ------------------------------------------------------------------
    # Contact info and messaging consent on ClientFile model fields
    # ------------------------------------------------------------------

    def _set_client_contact_and_consent(self, now):
        """Set phone, email, and CASL consent on demo clients.

        Most clients get phone + SMS consent so messaging scenarios work.
        Two clients are deliberately different for SCN-084 (consent guardrails):
        - DEMO-006 (Jesse Morales): no phone, no email — tests "can't message"
        - DEMO-005 (Kai Dubois): has phone but SMS consent withdrawn
        """
        from datetime import date

        consent_date = date(2025, 9, 15)  # Realistic past date

        # Map record_id → (phone, email, sms_consent, email_consent, preferred_contact)
        # Values mirror demo_client_fields.py custom field data
        client_contacts = {
            "DEMO-001": ("4165550123", "jordan.rivera@example.com", True, True, "both"),
            "DEMO-002": ("6475550234", "", True, False, "sms"),
            "DEMO-003": ("9055550345", "avery.osei@example.com", False, True, "email"),
            "DEMO-004": ("4165550456", "", True, False, "sms"),
            "DEMO-005": ("6475550567", "", False, False, "none"),  # consent withdrawn below
            "DEMO-006": ("", "", False, False, "none"),  # no contact info at all
            "DEMO-007": ("9055550789", "", True, False, "sms"),
            "DEMO-008": ("6475550890", "", True, False, "sms"),
            "DEMO-009": ("4165550901", "zara.a@example.com", False, True, "email"),
            "DEMO-010": ("9055551012", "", True, False, "sms"),
            "DEMO-011": ("4165551123", "", True, False, "sms"),
            "DEMO-012": ("6475551234", "carlos.reyes@example.com", True, True, "both"),
            "DEMO-013": ("9055551345", "", True, False, "sms"),
            "DEMO-014": ("4165551456", "liam.oconnor@example.com", False, True, "email"),
            "DEMO-015": ("6475551567", "", True, False, "sms"),
        }

        updated = 0
        for record_id, (phone, email, sms, email_c, pref) in client_contacts.items():
            client = ClientFile.objects.filter(record_id=record_id).first()
            if not client:
                continue

            client.phone = phone  # empty string clears encrypted field
            client.email = email

            client.sms_consent = sms
            client.email_consent = email_c
            client.preferred_contact_method = pref

            if sms or email_c:
                client.sms_consent_date = consent_date if sms else None
                client.email_consent_date = consent_date if email_c else None
                client.consent_messaging_type = "express"

            client.save()
            updated += 1

        # DEMO-005: explicitly mark SMS consent as withdrawn (SCN-084 step 2)
        kai = ClientFile.objects.filter(record_id="DEMO-005").first()
        if kai:
            kai.sms_consent = False
            kai.sms_consent_date = consent_date  # originally consented
            kai.sms_consent_withdrawn_date = date(2026, 1, 10)  # withdrew later
            kai.consent_notes = "Client requested to stop receiving text messages."
            kai.save()

        self.stdout.write(
            f"  Client contact & consent: {updated} clients updated. "
            f"DEMO-006=no contact, DEMO-005=SMS withdrawn."
        )

    # ------------------------------------------------------------------
    # Calendar feed tokens for demo workers
    # ------------------------------------------------------------------

    def _create_demo_calendar_feeds(self, workers):
        """Create calendar feed tokens so demo workers can see their iCal feeds."""
        import secrets

        created = 0
        for username, user in workers.items():
            _, was_created = CalendarFeedToken.objects.get_or_create(
                user=user,
                defaults={
                    "token": secrets.token_urlsafe(48),
                    "is_active": True,
                },
            )
            if was_created:
                created += 1

        if created:
            self.stdout.write(f"  Calendar feed tokens: {created} created for demo workers.")

    def _create_demo_suggestion_themes(self, workers, programs_by_name):
        """Create suggestion themes and link them to existing demo notes."""
        theme_count = 0
        link_count = 0

        for program_name, theme_defs in PROGRAM_THEMES.items():
            program = programs_by_name.get(program_name)
            if not program:
                continue

            # Get demo notes with suggestions for this program
            notes_with_suggestions = list(
                ProgressNote.objects.filter(
                    client_file__record_id__startswith="DEMO-",
                    author_program=program,
                ).exclude(suggestion_priority="")
                .select_related("client_file")
            )

            worker_username = PROGRAM_WORKER.get(program_name, "demo-worker-1")
            author = workers.get(worker_username)

            for theme_def in theme_defs:
                theme = SuggestionTheme.objects.create(
                    program=program,
                    name=theme_def["name"],
                    description=theme_def["description"],
                    status=theme_def["status"],
                    source=theme_def.get("source", "ai_generated"),
                    keywords=theme_def.get("keywords", ""),
                    addressed_note=theme_def.get("addressed_note", ""),
                    created_by=author,
                )
                theme_count += 1

                # Link notes via keyword matching
                keywords = {
                    kw.strip().lower()
                    for kw in theme_def.get("keywords", "").split(",")
                    if kw.strip()
                }
                linked_notes = []
                for note in notes_with_suggestions:
                    suggestion_text = (note.participant_suggestion or "").lower()
                    if any(kw in suggestion_text for kw in keywords):
                        SuggestionLink.objects.create(
                            theme=theme,
                            progress_note=note,
                            auto_linked=True,
                            linked_by=author,
                        )
                        linked_notes.append(note)
                        link_count += 1

                # If no keyword matches, link 1-2 arbitrary notes so theme isn't empty
                if not linked_notes and notes_with_suggestions:
                    for fallback_note in notes_with_suggestions[:2]:
                        if not SuggestionLink.objects.filter(
                            theme=theme, progress_note=fallback_note
                        ).exists():
                            SuggestionLink.objects.create(
                                theme=theme,
                                progress_note=fallback_note,
                                auto_linked=False,
                                linked_by=author,
                            )
                            link_count += 1

                # Recalculate priority from linked note priorities
                recalculate_theme_priority(theme)

        self.stdout.write(
            f"  Suggestion themes: {theme_count} themes, {link_count} links created."
        )

    def _create_demo_staff_messages(self, workers, programs_by_name, now):
        """Create internal staff-to-staff messages about demo participants."""
        from apps.clients.models import ClientFile

        # Build user lookup — include manager and front desk
        users_by_username = dict(workers)
        for username in ("demo-frontdesk", "demo-manager"):
            try:
                users_by_username[username] = User.objects.get(username=username)
            except User.DoesNotExist:
                self.stdout.write(self.style.WARNING(
                    f"  {username} not found — skipping staff messages for that user."
                ))

        created = 0
        for msg_def in DEMO_STAFF_MESSAGES:
            client = ClientFile.objects.filter(
                record_id=msg_def["client"]
            ).first()
            if not client:
                continue

            left_by = users_by_username.get(msg_def["left_by"])
            for_user = users_by_username.get(msg_def["for_user"])
            if not left_by:
                continue

            # Determine program from client's enrolment
            enrolment = client.enrollments.select_related("program").first()
            author_program = enrolment.program if enrolment else None

            msg = StaffMessage(
                client_file=client,
                left_by=left_by,
                for_user=for_user,
                status=msg_def["status"],
                author_program=author_program,
            )
            msg.content = msg_def["message"]
            msg.save()

            # Backdate created_at
            days_ago = msg_def.get("days_ago", 1)
            backdated = now - timedelta(days=days_ago, hours=random.randint(1, 8))
            StaffMessage.objects.filter(pk=msg.pk).update(created_at=backdated)

            # Set read_at for read messages
            if msg_def["status"] == "read":
                read_time = backdated + timedelta(hours=random.randint(1, 12))
                StaffMessage.objects.filter(pk=msg.pk).update(read_at=read_time)

            created += 1

        self.stdout.write(f"  Staff messages: {created} created.")
