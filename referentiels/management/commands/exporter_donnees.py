"""
Exporte les techniciens, leurs comptes et les interventions dans un fichier JSON,
à charger ensuite chez l'hébergeur avec charger_donnees.

Utilisation :  python manage.py exporter_donnees

ATTENTION : le fichier contient des noms et des mots de passe chiffrés. Il est exclu
de Git : envoyez-le directement sur le serveur et supprimez-le après le chargement.
"""
import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from comptes.roles import role_de
from interventions.models import Intervention
from referentiels.models import Technicien

FICHIER_DEFAUT = settings.BASE_DIR / "donnees_hebergeur.json"


def compte_de(user):
    """Compte à recréer sur le serveur. Le mot de passe reste sous sa forme chiffrée."""
    return {
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "password": user.password,
        "is_active": user.is_active,
        "role": role_de(user),
    }


class Command(BaseCommand):
    help = "Exporte les techniciens, leurs comptes et les interventions pour l'hébergeur."

    def add_arguments(self, parser):
        parser.add_argument("--fichier", default=FICHIER_DEFAUT, help="Fichier à créer.")

    def handle(self, *args, **options):
        techniciens = [
            {
                "nom": technicien.nom,
                "prenom": technicien.prenom,
                "unite": technicien.unite,
                "compte": compte_de(technicien.utilisateur) if technicien.utilisateur else None,
            }
            for technicien in Technicien.objects.select_related("utilisateur")
        ]
        interventions = [
            {
                "date": intervention.date.isoformat(),
                "equipement": intervention.equipement.numero_serie,
                "type": intervention.type.libelle,
                "technicien": [intervention.technicien.nom, intervention.technicien.prenom],
                "commentaire": intervention.commentaire,
                "panne_resolue": intervention.panne_resolue,
                "saisie_par": intervention.cree_par.username if intervention.cree_par else None,
            }
            for intervention in Intervention.objects.select_related(
                "equipement", "type", "technicien", "cree_par"
            ).order_by("date", "cree_le")
        ]

        chemin = Path(options["fichier"])
        chemin.write_text(
            json.dumps({"techniciens": techniciens, "interventions": interventions},
                       ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        self.stdout.write(self.style.SUCCESS(
            f"{len(techniciens)} technicien(s) et {len(interventions)} intervention(s) "
            f"exporté(s) dans {chemin}."
        ))
        self.stdout.write(self.style.WARNING(
            "Ce fichier contient des mots de passe chiffrés : ne le mettez pas sur GitHub."
        ))
