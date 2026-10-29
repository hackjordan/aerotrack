"""
Crée les 6 catégories et y rattache les types d'équipements déjà enregistrés.

Les types inconnus restent sans catégorie : l'administrateur les classe
ensuite dans Référentiels > Types d'équipements.
"""
from django.db import migrations

CATEGORIES = [
    ("COM", "Communication", 1),
    ("NAV", "Navigation", 2),
    ("SURV", "Surveillance", 3),
    ("MET", "Météo", 4),
    ("RSI", "Informatique et réseau", 5),
    ("ENR", "Énergie", 6),
]

# Libellés (en minuscules) des types existants → code de catégorie
CLASSEMENT = {
    "radio vhf": "COM", "vhf": "COM", "radio hf": "COM",
    "système de commutation vocale (vcs)": "COM", "vcs": "COM",
    "ils": "NAV", "vor/dme": "NAV", "vor": "NAV", "dme": "NAV", "ndb": "NAV",
    "balise de radionavigation": "NAV",
    "radar": "SURV", "ads-b": "SURV",
    "station météo automatique": "MET", "transmissomètre (rvr)": "MET",
    "serveur": "RSI", "switch": "RSI", "routeur": "RSI", "pare-feu": "RSI",
    "poste de travail": "RSI", "pc": "RSI", "imprimante": "RSI",
    "onduleur": "ENR", "groupe électrogène": "ENR", "climatiseur": "ENR",
}


def creer_et_classer(apps, schema_editor):
    Categorie = apps.get_model("referentiels", "Categorie")
    TypeEquipement = apps.get_model("referentiels", "TypeEquipement")

    par_code = {}
    for code, libelle, ordre in CATEGORIES:
        par_code[code], _ = Categorie.objects.get_or_create(
            code=code, defaults={"libelle": libelle, "ordre": ordre}
        )

    for type_equipement in TypeEquipement.objects.filter(categorie__isnull=True):
        code = CLASSEMENT.get(type_equipement.libelle.strip().lower())
        if code:
            type_equipement.categorie = par_code[code]
            type_equipement.save(update_fields=["categorie"])


def annuler(apps, schema_editor):
    apps.get_model("referentiels", "TypeEquipement").objects.update(categorie=None)
    apps.get_model("referentiels", "Categorie").objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [("referentiels", "0002_categories")]

    operations = [migrations.RunPython(creer_et_classer, annuler)]
