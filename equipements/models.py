"""
Module 2 : équipements.

Règles de gestion appliquées ici :
  RG1 : un équipement appartient à un seul type ;
  RG2 : un équipement se trouve dans un seul emplacement ;
  RG3 : un équipement est fourni par un seul fournisseur ;
  RG6 : le numéro de série est unique (sans tenir compte des majuscules).
"""
from django.conf import settings
from django.db import models
from django.db.models import Q
from django.db.models.functions import Upper

from emplacements.models import Emplacement
from referentiels.models import Fournisseur, TypeEquipement


class Statut(models.TextChoices):
    FONCTIONNEL = "FONCTIONNEL", "Fonctionnel"
    EN_PANNE = "EN_PANNE", "En panne"
    EN_MAINTENANCE = "EN_MAINTENANCE", "En maintenance"


class EquipementQuerySet(models.QuerySet):
    def recherche(self, texte):
        """Recherche par nom, n° de série ou marque (liste F2.5 et recherche globale)."""
        return self.filter(Q(nom__icontains=texte) | Q(numero_serie__icontains=texte) | Q(marque__icontains=texte))


class Equipement(models.Model):
    nom = models.CharField(max_length=150)
    numero_serie = models.CharField("numéro de série", max_length=100)
    marque = models.CharField(max_length=100)
    type = models.ForeignKey(
        TypeEquipement, on_delete=models.PROTECT,
        related_name="equipements", verbose_name="type",
    )
    emplacement = models.ForeignKey(
        Emplacement, on_delete=models.PROTECT,
        related_name="equipements",
    )
    fournisseur = models.ForeignKey(
        Fournisseur, on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="equipements",
        help_text="Laisser vide si le fournisseur n'est pas connu.",
    )
    date_installation = models.DateField("date d'installation", null=True, blank=True)
    statut = models.CharField(max_length=20, choices=Statut.choices, default=Statut.FONCTIONNEL)

    cree_le = models.DateTimeField("créé le", auto_now_add=True)
    modifie_le = models.DateTimeField("modifié le", auto_now=True)

    objects = EquipementQuerySet.as_manager()

    class Meta:
        verbose_name = "équipement"
        ordering = ["nom"]
        constraints = [
            models.UniqueConstraint(
                Upper("numero_serie"), name="equipement_numero_serie_unique",
                violation_error_message="Un équipement possède déjà ce numéro de série.",
            ),
        ]
        indexes = [models.Index(fields=["statut"])]

    def __str__(self):
        return f"{self.nom} ({self.numero_serie})"

    def save(self, *args, **kwargs):
        self.numero_serie = self.numero_serie.strip()
        super().save(*args, **kwargs)


class HistoriqueStatut(models.Model):
    """
    Trace de chaque changement de statut d'un équipement.

    Sert à l'historique des pannes (F4.4) et à la courbe des pannes par mois (F6.3).
    """

    equipement = models.ForeignKey(
        Equipement, on_delete=models.CASCADE, related_name="historique_statuts",
        verbose_name="équipement",
    )
    ancien_statut = models.CharField(max_length=20, choices=Statut.choices, blank=True)
    nouveau_statut = models.CharField(max_length=20, choices=Statut.choices)
    date = models.DateTimeField(auto_now_add=True)
    auteur = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="+",
    )
    commentaire = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "changement de statut"
        verbose_name_plural = "historique des statuts"
        ordering = ["-date", "-pk"]
        indexes = [models.Index(fields=["nouveau_statut", "date"])]

    def __str__(self):
        return f"{self.equipement} : {self.get_ancien_statut_display() or '—'} → {self.get_nouveau_statut_display()}"
