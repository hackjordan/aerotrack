"""
Crée 12 équipements de DÉMONSTRATION : 2 par catégorie (un par type).

Utilisation :  python manage.py init_demo
Lance d'abord init_donnees (la commande le fait si nécessaire).

ATTENTION : noms, marques et numéros de série sont fictifs. Ces données servent
à la démonstration et aux captures du rapport, jamais à la base de production.
La commande peut être relancée : un numéro de série déjà présent est ignoré.
"""
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

from emplacements.models import Emplacement
from equipements.models import Equipement, Statut
from equipements.services import enregistrer_changement_statut
from referentiels.models import TypeEquipement

# (nom, type, marque, n° de série, (bâtiment, zone), statut)
EQUIPEMENTS_DEMO = [
    # Communication
    ("VHF Vigie Principal 118.1", "Radio VHF", "Park Air", "VHF-0001", ("Tour de contrôle", "Vigie"), Statut.FONCTIONNEL),
    ("VCS Vigie", "Système de commutation vocale (VCS)", "Frequentis", "VCS-0001", ("Tour de contrôle", "Vigie"), Statut.FONCTIONNEL),
    # Navigation
    ("ILS Localizer piste 12", "ILS", "Thales", "ILS-LOC-01", ("Piste", "Bout de piste 12"), Statut.EN_MAINTENANCE),
    ("VOR/DME Douala", "VOR/DME", "Indra", "VOR-0001", ("Site VOR/DME", "Shelter"), Statut.FONCTIONNEL),
    # Surveillance
    ("Radar secondaire SSR", "Radar", "Thales", "RAD-SSR-01", ("Site radar", "Abri radar"), Statut.FONCTIONNEL),
    ("Station ADS-B", "ADS-B", "Thales", "ADSB-0001", ("Site radar", "Abri radar"), Statut.FONCTIONNEL),
    # Météo
    ("Station météo automatique", "Station météo automatique", "Vaisala", "MET-AWS-01", ("Parc météo", "Instruments"), Statut.FONCTIONNEL),
    ("Transmissomètre RVR piste 12", "Transmissomètre (RVR)", "Vaisala", "MET-RVR-01", ("Piste", "Bout de piste 12"), Statut.EN_PANNE),
    # Informatique et réseau
    ("Serveur messagerie", "Serveur", "Dell", "SRV-0002", ("Bloc technique", "Salle serveurs"), Statut.EN_PANNE),
    ("Switch étage vigie", "Switch", "Cisco", "SW-0005", ("Tour de contrôle", "Vigie"), Statut.FONCTIONNEL),
    # Énergie
    ("Onduleur salle technique 1", "Onduleur", "APC", "OND-0003", ("Tour de contrôle", "Salle technique"), Statut.FONCTIONNEL),
    ("Groupe électrogène principal", "Groupe électrogène", "SDMO", "GE-0001", ("Centrale électrique", "Groupes électrogènes"), Statut.EN_MAINTENANCE),
]


class Command(BaseCommand):
    help = "Crée 12 équipements fictifs de démonstration (2 par catégorie). Ne pas utiliser en production."

    @transaction.atomic
    def handle(self, *args, **options):
        call_command("init_donnees", stdout=self.stdout)

        crees = 0
        for nom, libelle_type, marque, numero, (batiment, zone), statut in EQUIPEMENTS_DEMO:
            if Equipement.objects.filter(numero_serie__iexact=numero).exists():
                continue
            equipement = Equipement.objects.create(
                nom=nom, marque=marque, numero_serie=numero, statut=statut,
                type=TypeEquipement.objects.get(libelle__iexact=libelle_type),
                emplacement=Emplacement.objects.get(batiment__iexact=batiment, zone__iexact=zone),
            )
            enregistrer_changement_statut(equipement, "", None, "Données de démonstration")
            crees += 1

        self.stdout.write(self.style.SUCCESS(f"{crees} équipement(s) de démonstration créé(s)."))
        self.stdout.write(self.style.WARNING("Données fictives : à ne pas utiliser en production."))
