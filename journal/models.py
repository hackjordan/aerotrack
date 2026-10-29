"""
Traçabilité (cahier des charges § 7) : qui a fait quoi, et quand.

Le remplissage automatique du journal sera mis en place à l'étape 6.
"""
from django.conf import settings
from django.db import models


class JournalAction(models.Model):
    class Action(models.TextChoices):
        CREATION = "CREATION", "Création"
        MODIFICATION = "MODIFICATION", "Modification"
        SUPPRESSION = "SUPPRESSION", "Suppression"

    date = models.DateTimeField(auto_now_add=True)
    auteur = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="+",
    )
    action = models.CharField(max_length=20, choices=Action.choices)
    objet_type = models.CharField("type d'objet", max_length=100)
    objet_id = models.CharField("identifiant de l'objet", max_length=50)
    objet_libelle = models.CharField("objet", max_length=255)
    details = models.TextField("détails", blank=True)

    class Meta:
        verbose_name = "action"
        verbose_name_plural = "journal des actions"
        ordering = ["-date"]
        indexes = [models.Index(fields=["date"])]

    def __str__(self):
        return f"{self.date:%d/%m/%Y %H:%M} – {self.get_action_display()} – {self.objet_libelle}"
