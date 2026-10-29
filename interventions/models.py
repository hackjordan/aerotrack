"""
Module 4 : interventions de maintenance.

Règles de gestion appliquées ici :
  RG4 : une intervention concerne un seul équipement ;
  RG5 : une intervention est réalisée par un seul technicien et a un seul type.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone

from equipements.models import Equipement
from referentiels.models import Technicien, TypeIntervention


class Intervention(models.Model):
    date = models.DateField(default=timezone.localdate)
    equipement = models.ForeignKey(
        Equipement, on_delete=models.PROTECT,
        related_name="interventions", verbose_name="équipement",
    )
    technicien = models.ForeignKey(
        Technicien, on_delete=models.PROTECT, related_name="interventions",
    )
    type = models.ForeignKey(
        TypeIntervention, on_delete=models.PROTECT,
        related_name="interventions", verbose_name="type d'intervention",
    )
    commentaire = models.TextField(blank=True)
    panne_resolue = models.BooleanField(
        "panne résolue", default=False,
        help_text="Pour une intervention corrective : cochée, l'équipement repasse "
                  "« Fonctionnel » ; sinon il est mis « En maintenance » (F4.5).",
    )

    cree_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="+", verbose_name="saisie par",
    )
    cree_le = models.DateTimeField("créée le", auto_now_add=True)
    modifie_le = models.DateTimeField("modifiée le", auto_now=True)

    class Meta:
        verbose_name = "intervention"
        ordering = ["-date", "-cree_le"]
        indexes = [models.Index(fields=["date"])]

    def __str__(self):
        return f"{self.type} – {self.equipement} – {self.date:%d/%m/%Y}"
