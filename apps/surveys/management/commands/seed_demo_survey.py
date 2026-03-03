"""Seed a 'Program Feedback' demo survey for the konote-dev demo site.

Creates a survey with five questions that showcase different question types
(rating_scale, yes_no, multiple_choice, single_choice, short_text) and
generates a shareable link.

Run with: python manage.py seed_demo_survey

Idempotent — if the survey already exists it is updated, not duplicated.
"""

from django.core.management.base import BaseCommand

from apps.surveys.models import (
    Survey,
    SurveyLink,
    SurveyQuestion,
    SurveySection,
)


class Command(BaseCommand):
    help = "Create or update the demo 'Program Feedback' survey with a shareable link."

    # Fixed token so the konote-website demo page can embed it
    DEMO_TOKEN = "demo-program-feedback"

    def handle(self, *args, **options):
        survey = self._create_survey()
        section = self._create_section(survey)
        self._create_questions(section)
        link = self._create_link(survey)

        self.stdout.write(self.style.SUCCESS(
            f"Demo survey ready. Shareable link: /s/{link.token}/"
        ))

    def _create_survey(self):
        survey, created = Survey.objects.update_or_create(
            name="Program Feedback",
            defaults={
                "name_fr": "Rétroaction sur le programme",
                "description": (
                    "We'd love to hear how the program is going for you. "
                    "Your answers help us improve."
                ),
                "description_fr": (
                    "Nous aimerions savoir comment le programme se passe pour vous. "
                    "Vos réponses nous aident à nous améliorer."
                ),
                "status": "active",
                "is_anonymous": True,
                "show_scores_to_participant": False,
                "portal_visible": False,
            },
        )
        action = "Created" if created else "Updated"
        self.stdout.write(f"  {action} survey: {survey.name}")
        return survey

    def _create_section(self, survey):
        section, _ = SurveySection.objects.update_or_create(
            survey=survey,
            sort_order=0,
            defaults={
                "title": "Your Feedback",
                "title_fr": "Vos commentaires",
                "instructions": "",
                "instructions_fr": "",
                "scoring_method": "none",
                "is_active": True,
            },
        )
        return section

    def _create_questions(self, section):
        # Delete existing questions for this section to avoid duplicates
        section.questions.all().delete()

        questions = [
            {
                "question_text": "Overall, how satisfied are you with the program?",
                "question_text_fr": "Dans l'ensemble, êtes-vous satisfait(e) du programme\u00a0?",
                "question_type": "rating_scale",
                "sort_order": 1,
                "required": True,
                "min_value": 1,
                "max_value": 5,
                "options_json": [
                    {"value": "1", "label": "Very unsatisfied", "label_fr": "Très insatisfait(e)", "score": 1},
                    {"value": "2", "label": "Unsatisfied", "label_fr": "Insatisfait(e)", "score": 2},
                    {"value": "3", "label": "Neutral", "label_fr": "Neutre", "score": 3},
                    {"value": "4", "label": "Satisfied", "label_fr": "Satisfait(e)", "score": 4},
                    {"value": "5", "label": "Very satisfied", "label_fr": "Très satisfait(e)", "score": 5},
                ],
            },
            {
                "question_text": "Do you feel more confident in your abilities since starting the program?",
                "question_text_fr": "Vous sentez-vous plus confiant(e) dans vos capacités depuis le début du programme\u00a0?",
                "question_type": "yes_no",
                "sort_order": 2,
                "required": True,
                "options_json": [],
            },
            {
                "question_text": "Which aspects of the program were most helpful?",
                "question_text_fr": "Quels aspects du programme ont été les plus utiles\u00a0?",
                "question_type": "multiple_choice",
                "sort_order": 3,
                "required": True,
                "options_json": [
                    {"value": "workshops", "label": "Workshops", "label_fr": "Ateliers"},
                    {"value": "one_on_one", "label": "One-on-one support", "label_fr": "Soutien individuel"},
                    {"value": "group_sessions", "label": "Group sessions", "label_fr": "Séances de groupe"},
                    {"value": "resources", "label": "Resources & materials", "label_fr": "Ressources et matériel"},
                ],
            },
            {
                "question_text": "How connected do you feel to the people in the program?",
                "question_text_fr": "À quel point vous sentez-vous lié(e) aux personnes du programme\u00a0?",
                "question_type": "single_choice",
                "sort_order": 4,
                "required": True,
                "options_json": [
                    {"value": "not_at_all", "label": "Not at all connected", "label_fr": "Pas du tout lié(e)"},
                    {"value": "slightly", "label": "Slightly connected", "label_fr": "Un peu lié(e)"},
                    {"value": "somewhat", "label": "Somewhat connected", "label_fr": "Assez lié(e)"},
                    {"value": "very", "label": "Very connected", "label_fr": "Très lié(e)"},
                ],
            },
            {
                "question_text": "Anything you'd change about the program?",
                "question_text_fr": "Y a-t-il quelque chose que vous changeriez dans le programme\u00a0?",
                "question_type": "short_text",
                "sort_order": 5,
                "required": False,
                "options_json": [],
            },
        ]

        for q_data in questions:
            SurveyQuestion.objects.create(section=section, **q_data)

        self.stdout.write(f"  Created {len(questions)} questions")

    def _create_link(self, survey):
        link, created = SurveyLink.objects.update_or_create(
            survey=survey,
            token=self.DEMO_TOKEN,
            defaults={
                "is_active": True,
                "collect_name": True,
            },
        )
        action = "Created" if created else "Updated"
        self.stdout.write(f"  {action} shareable link: /s/{link.token}/")
        return link
