"""Crée les trois groupes correspondant aux rôles d'AéroTrack."""
from django.db import migrations

ROLES = ["Administrateur", "Technicien", "Consultant"]


def creer_groupes(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    for nom in ROLES:
        Group.objects.get_or_create(name=nom)


def supprimer_groupes(apps, schema_editor):
    apps.get_model("auth", "Group").objects.filter(name__in=ROLES).delete()


class Migration(migrations.Migration):
    dependencies = [("auth", "0012_alter_user_first_name_max_length")]

    operations = [migrations.RunPython(creer_groupes, supprimer_groupes)]
