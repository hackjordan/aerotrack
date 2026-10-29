"""Supprime le rôle Consultant : AéroTrack n'a plus que deux rôles."""
from django.db import migrations


def supprimer_consultant(apps, schema_editor):
    # Un ancien consultant garde son compte mais n'a plus de rôle : il ne peut
    # plus rien ouvrir tant que l'administrateur ne lui en attribue pas un.
    apps.get_model("auth", "Group").objects.filter(name="Consultant").delete()


def recreer_consultant(apps, schema_editor):
    apps.get_model("auth", "Group").objects.get_or_create(name="Consultant")


class Migration(migrations.Migration):
    dependencies = [("comptes", "0001_groupes_roles")]

    operations = [migrations.RunPython(supprimer_consultant, recreer_consultant)]
