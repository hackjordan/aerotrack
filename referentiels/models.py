"""
Module 5 : référentiels.

Listes de base utilisées dans les formulaires : catégories et types d'équipements,
types d'intervention, fournisseurs et techniciens.

RG7 : un type d'équipement appartient à une seule catégorie ;
      une catégorie regroupe plusieurs types.
"""
from django.conf import settings
from django.db import models
from django.db.models.functions import Lower


class Categorie(models.Model):
    """Grande famille d'équipements, classée comme dans l'aviation : COM, NAV, SURV, MET, RSI, ENR."""

    code = models.CharField(max_length=10, unique=True, help_text="Code court, par exemple COM ou NAV.")
    libelle = models.CharField("libellé", max_length=100, unique=True)
    ordre = models.PositiveSmallIntegerField("ordre d'affichage", default=0)

    class Meta:
        verbose_name = "catégorie"
        ordering = ["ordre", "libelle"]

    def __str__(self):
        return self.libelle


class TypeEquipement(models.Model):
    """Type d'équipement : Radio VHF, ILS, Radar, Onduleur, Serveur…"""

    libelle = models.CharField("libellé", max_length=100)
    # null=True seulement pour les types créés avant l'ajout des catégories ;
    # les formulaires l'exigent (blank=False).
    categorie = models.ForeignKey(
        Categorie, on_delete=models.PROTECT, null=True,
        related_name="types", verbose_name="catégorie",
    )

    class Meta:
        verbose_name = "type d'équipement"
        verbose_name_plural = "types d'équipements"
        ordering = ["categorie__ordre", "libelle"]
        constraints = [
            models.UniqueConstraint(
                Lower("libelle"), name="type_equipement_libelle_unique",
                violation_error_message="Ce type d'équipement existe déjà.",
            ),
        ]

    def __str__(self):
        return self.libelle


class TypeIntervention(models.Model):
    """Nature d'une intervention : Préventive, Corrective, Installation…"""

    libelle = models.CharField("libellé", max_length=100)
    est_corrective = models.BooleanField(
        "intervention corrective", default=False,
        help_text="Cochée : l'intervention répare une panne et met à jour "
                  "automatiquement le statut de l'équipement (F4.5).",
    )

    class Meta:
        verbose_name = "type d'intervention"
        verbose_name_plural = "types d'intervention"
        ordering = ["libelle"]
        constraints = [
            models.UniqueConstraint(
                Lower("libelle"), name="type_intervention_libelle_unique",
                violation_error_message="Ce type d'intervention existe déjà.",
            ),
        ]

    def __str__(self):
        return self.libelle


class Fournisseur(models.Model):
    nom = models.CharField(max_length=150)
    telephone = models.CharField("téléphone", max_length=30, blank=True)
    email = models.EmailField("e-mail", blank=True)

    class Meta:
        verbose_name = "fournisseur"
        ordering = ["nom"]
        constraints = [
            models.UniqueConstraint(
                Lower("nom"), name="fournisseur_nom_unique",
                violation_error_message="Ce fournisseur existe déjà.",
            ),
        ]

    def __str__(self):
        return self.nom


class Technicien(models.Model):
    """
    Agent de maintenance IRE / RSI.

    Le lien vers un compte utilisateur permet de savoir quelles interventions
    un technicien connecté a le droit de modifier (F4.2).
    """

    nom = models.CharField(max_length=100)
    prenom = models.CharField("prénom", max_length=100)
    unite = models.CharField("unité", max_length=100, help_text="Exemple : IRE, RSI")
    utilisateur = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="technicien",
        verbose_name="compte utilisateur",
    )

    class Meta:
        verbose_name = "technicien"
        ordering = ["nom", "prenom"]

    def __str__(self):
        return f"{self.nom.upper()} {self.prenom}"
