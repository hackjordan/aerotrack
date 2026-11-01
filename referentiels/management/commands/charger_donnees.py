"""
Charge sur le serveur les techniciens, les comptes et les interventions du fichier
créé par exporter_donnees.

Utilisation :  python manage.py charger_donnees
Les équipements et les types d'intervention doivent déjà exister (init_donnees et
init_demo, ou base importée). En cas d'absence, rien n'est chargé.

La commande peut être relancée : ce qui existe déjà est ignoré, et un compte existant
garde son mot de passe. Le statut des équipements ne change pas : ces interventions
sont passées, et l'historique daterait le changement du jour du chargement.
"""
import json
from datetime import date
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from comptes.roles import definir_role
from equipements.models import Equipement
from interventions.models import Intervention
from referentiels.models import Technicien, TypeIntervention

from .exporter_donnees import FICHIER_DEFAUT


def technicien_nomme(nom, prenom):
    return Technicien.objects.filter(nom__iexact=nom, prenom__iexact=prenom).first()


class Command(BaseCommand):
    help = "Charge le fichier créé par exporter_donnees : techniciens, comptes et interventions."

    def add_arguments(self, parser):
        parser.add_argument("--fichier", default=FICHIER_DEFAUT, help="Fichier à charger.")

    @transaction.atomic
    def handle(self, *args, **options):
        chemin = Path(options["fichier"])
        if not chemin.exists():
            raise CommandError(f"Fichier introuvable : {chemin}. Envoyez-le d'abord sur le serveur.")
        donnees = json.loads(chemin.read_text(encoding="utf-8"))

        User = get_user_model()
        techniciens = comptes = interventions = 0

        for ligne in donnees["techniciens"]:
            technicien = technicien_nomme(ligne["nom"], ligne["prenom"])
            if technicien is None:
                technicien = Technicien.objects.create(
                    nom=ligne["nom"], prenom=ligne["prenom"], unite=ligne["unite"]
                )
                techniciens += 1

            compte = ligne["compte"]
            if compte is None:
                continue
            user = User.objects.filter(username=compte["username"]).first()
            if user is None:
                # create() et non create_user() : le mot de passe est déjà chiffré.
                user = User.objects.create(
                    username=compte["username"], password=compte["password"],
                    first_name=compte["first_name"], last_name=compte["last_name"],
                    email=compte["email"], is_active=compte["is_active"],
                )
                if compte["role"]:
                    definir_role(user, compte["role"])
                comptes += 1
            if technicien.utilisateur_id is None:
                if Technicien.objects.filter(utilisateur=user).exists():
                    raise CommandError(
                        f"Le compte {user.username} est déjà relié à un autre technicien : "
                        "rien n'a été chargé."
                    )
                technicien.utilisateur = user
                technicien.save(update_fields=["utilisateur"])

        for ligne in donnees["interventions"]:
            equipement = Equipement.objects.filter(numero_serie__iexact=ligne["equipement"]).first()
            type_intervention = TypeIntervention.objects.filter(libelle__iexact=ligne["type"]).first()
            if equipement is None or type_intervention is None:
                raise CommandError(
                    f"Équipement « {ligne['equipement']} » ou type « {ligne['type']} » absent du serveur : "
                    "rien n'a été chargé. Lancez d'abord init_donnees et init_demo."
                )
            valeurs = {
                "date": date.fromisoformat(ligne["date"]),
                "equipement": equipement,
                "technicien": technicien_nomme(*ligne["technicien"]),
                "type": type_intervention,
                "commentaire": ligne["commentaire"],
            }
            if not Intervention.objects.filter(**valeurs).exists():
                Intervention.objects.create(
                    **valeurs,
                    panne_resolue=ligne["panne_resolue"],
                    cree_par=User.objects.filter(username=ligne["saisie_par"]).first(),
                )
                interventions += 1

        self.stdout.write(self.style.SUCCESS(
            f"{techniciens} technicien(s), {comptes} compte(s) et {interventions} intervention(s) créé(s)."
        ))
        self.stdout.write(self.style.WARNING(
            f"Supprimez maintenant {chemin.name} du serveur : il contient des mots de passe chiffrés."
        ))
