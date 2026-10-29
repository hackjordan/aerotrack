"""Module 3 : emplacements (zone et bâtiment)."""
from django.db import models
from django.db.models.functions import Lower


class Emplacement(models.Model):
    zone = models.CharField(max_length=100, help_text="Exemple : Salle technique, Vigie")
    batiment = models.CharField("bâtiment", max_length=100, help_text="Exemple : Tour de contrôle")

    class Meta:
        verbose_name = "emplacement"
        ordering = ["batiment", "zone"]
        constraints = [
            models.UniqueConstraint(
                Lower("batiment"), Lower("zone"), name="emplacement_unique",
                violation_error_message="Cet emplacement existe déjà dans ce bâtiment.",
            ),
        ]

    def __str__(self):
        return f"{self.batiment} – {self.zone}"
