"""Seed default Serious Reportable Event (SRE) categories.

Categories follow Canadian nonprofit requirements (MCCSS, PHIPA, OHSA,
accreditation standards). Idempotent — safe to run multiple times.
"""
from django.core.management.base import BaseCommand

from apps.events.models import SRECategory


DEFAULTS = [
    {
        "name": "Death of a participant",
        "name_fr": "Décès d'un participant",
        "description": "Expected or unexpected death of a participant while receiving services.",
        "description_fr": "Décès attendu ou inattendu d'un participant pendant qu'il recevait des services.",
        "severity": 1,
        "display_order": 1,
    },
    {
        "name": "Serious injury requiring emergency medical care",
        "name_fr": "Blessure grave nécessitant des soins médicaux d'urgence",
        "description": "Injury requiring transport to hospital or emergency medical intervention.",
        "description_fr": "Blessure nécessitant un transport à l'hôpital ou une intervention médicale d'urgence.",
        "severity": 1,
        "display_order": 2,
    },
    {
        "name": "Allegation or disclosure of abuse or neglect",
        "name_fr": "Allégation ou divulgation de mauvais traitements ou de négligence",
        "description": "Any allegation or disclosure of physical, sexual, emotional abuse, or neglect.",
        "description_fr": "Toute allégation ou divulgation de mauvais traitements physiques, sexuels, émotionnels ou de négligence.",
        "severity": 1,
        "display_order": 3,
    },
    {
        "name": "Use of physical restraint or seclusion",
        "name_fr": "Utilisation de contention physique ou d'isolement",
        "description": "Any use of physical restraint, mechanical restraint, or seclusion.",
        "description_fr": "Toute utilisation de contention physique, mécanique ou d'isolement.",
        "severity": 2,
        "display_order": 4,
    },
    {
        "name": "Missing person / elopement",
        "name_fr": "Personne disparue / fugue",
        "description": "Participant absent without authorisation, including youth leaving care.",
        "description_fr": "Participant absent sans autorisation, y compris les jeunes quittant les services.",
        "severity": 1,
        "display_order": 5,
    },
    {
        "name": "Suicide attempt or self-harm requiring intervention",
        "name_fr": "Tentative de suicide ou automutilation nécessitant une intervention",
        "description": "Suicide attempt or self-harm requiring medical or crisis intervention.",
        "description_fr": "Tentative de suicide ou automutilation nécessitant une intervention médicale ou de crise.",
        "severity": 1,
        "display_order": 6,
    },
    {
        "name": "Medication error with adverse outcome",
        "name_fr": "Erreur de médication avec effet indésirable",
        "description": "Medication administration error resulting in adverse effects or requiring medical attention.",
        "description_fr": "Erreur d'administration de médicaments entraînant des effets indésirables ou nécessitant des soins médicaux.",
        "severity": 2,
        "display_order": 7,
    },
    {
        "name": "Property damage or fire",
        "name_fr": "Dommages matériels ou incendie",
        "description": "Significant property damage or fire at a program location.",
        "description_fr": "Dommages matériels importants ou incendie dans un lieu de programme.",
        "severity": 2,
        "display_order": 8,
    },
    {
        "name": "Threat or assault involving participants or staff",
        "name_fr": "Menace ou agression impliquant des participants ou du personnel",
        "description": "Threats of violence or physical assault involving participants or staff members.",
        "description_fr": "Menaces de violence ou agression physique impliquant des participants ou du personnel.",
        "severity": 1,
        "display_order": 9,
    },
    {
        "name": "Police involvement or criminal incident",
        "name_fr": "Intervention policière ou incident criminel",
        "description": "Police called to a program location or criminal incident involving a participant.",
        "description_fr": "Appel de la police dans un lieu de programme ou incident criminel impliquant un participant.",
        "severity": 2,
        "display_order": 10,
    },
    {
        "name": "Communicable disease outbreak",
        "name_fr": "Éclosion de maladie transmissible",
        "description": "Outbreak of communicable disease at a program location requiring public health notification.",
        "description_fr": "Éclosion de maladie transmissible dans un lieu de programme nécessitant une notification de santé publique.",
        "severity": 2,
        "display_order": 11,
    },
    {
        "name": "Client rights violation",
        "name_fr": "Violation des droits du client",
        "description": "Violation of participant rights including privacy, dignity, or informed consent.",
        "description_fr": "Violation des droits du participant, y compris la vie privée, la dignité ou le consentement éclairé.",
        "severity": 3,
        "display_order": 12,
    },
]


class Command(BaseCommand):
    help = "Create default Serious Reportable Event (SRE) categories."

    def handle(self, *args, **options):
        created_count = 0
        for item in DEFAULTS:
            obj, created = SRECategory.objects.get_or_create(
                name=item["name"],
                defaults={
                    "name_fr": item["name_fr"],
                    "description": item["description"],
                    "description_fr": item["description_fr"],
                    "severity": item["severity"],
                    "display_order": item["display_order"],
                },
            )
            if created:
                created_count += 1
                self.stdout.write(f"  Created: {obj.name}")
            else:
                self.stdout.write(f"  Already exists: {obj.name}")
        self.stdout.write(self.style.SUCCESS(f"Done. {created_count} SRE category(ies) created."))
