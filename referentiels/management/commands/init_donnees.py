"""
Crée les données de départ : catégories, types d'équipements, types d'intervention
et emplacements.

Utilisation :  python manage.py init_donnees
La commande peut être relancée sans risque : elle ne crée que ce qui manque.
Les emplacements sont des exemples, à adapter à l'inventaire réel.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from emplacements.models import Emplacement
from referentiels.models import Categorie, TypeEquipement, TypeIntervention

# 6 catégories (classement CNS de l'aviation, plus météo, informatique et énergie),
# chacune avec ses 2 types d'équipements les plus importants.
# (code, libellé, [types])
CATEGORIES = [
    ("COM", "Communication", ["Radio VHF", "Système de commutation vocale (VCS)"]),
    ("NAV", "Navigation", ["ILS", "VOR/DME"]),
    ("SURV", "Surveillance", ["Radar", "ADS-B"]),
    ("MET", "Météo", ["Station météo automatique", "Transmissomètre (RVR)"]),
    ("RSI", "Informatique et réseau", ["Serveur", "Switch"]),
    ("ENR", "Énergie", ["Onduleur", "Groupe électrogène"]),
]

# (libellé, corrective ?)
TYPES_INTERVENTION = [
    ("Préventive", False),
    ("Corrective", True),
    ("Installation", False),
]

# (bâtiment, zone)
EMPLACEMENTS = [
    ("Tour de contrôle", "Vigie"),
    ("Tour de contrôle", "Salle technique"),
    ("Bloc technique", "Salle serveurs"),
    ("Bloc technique", "Salle énergie"),
    ("Site radar", "Abri radar"),
    ("Site VOR/DME", "Shelter"),
    ("Piste", "Bout de piste 12"),
    ("Parc météo", "Instruments"),
    ("Centrale électrique", "Groupes électrogènes"),
]


class Command(BaseCommand):
    help = ("Crée les catégories, les types d'équipements, les types d'intervention "
            "et des emplacements de départ.")

    @transaction.atomic
    def handle(self, *args, **options):
        crees = 0

        for ordre, (code, libelle, types) in enumerate(CATEGORIES, start=1):
            categorie, cree = Categorie.objects.get_or_create(
                code=code, defaults={"libelle": libelle, "ordre": ordre}
            )
            crees += cree
            for libelle_type in types:
                type_equipement = TypeEquipement.objects.filter(libelle__iexact=libelle_type).first()
                if type_equipement is None:
                    TypeEquipement.objects.create(libelle=libelle_type, categorie=categorie)
                    crees += 1
                elif type_equipement.categorie_id is None:
                    type_equipement.categorie = categorie
                    type_equipement.save(update_fields=["categorie"])

        for libelle, corrective in TYPES_INTERVENTION:
            if not TypeIntervention.objects.filter(libelle__iexact=libelle).exists():
                TypeIntervention.objects.create(libelle=libelle, est_corrective=corrective)
                crees += 1

        for batiment, zone in EMPLACEMENTS:
            if not Emplacement.objects.filter(batiment__iexact=batiment, zone__iexact=zone).exists():
                Emplacement.objects.create(batiment=batiment, zone=zone)
                crees += 1

        self.stdout.write(self.style.SUCCESS(f"{crees} élément(s) créé(s)."))
