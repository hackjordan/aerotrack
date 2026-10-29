from django.contrib import admin

from .models import Categorie, Fournisseur, Technicien, TypeEquipement, TypeIntervention


@admin.register(Categorie)
class CategorieAdmin(admin.ModelAdmin):
    list_display = ["libelle", "code", "ordre"]


@admin.register(TypeEquipement)
class TypeEquipementAdmin(admin.ModelAdmin):
    list_display = ["libelle", "categorie"]
    list_filter = ["categorie"]
    search_fields = ["libelle"]


@admin.register(TypeIntervention)
class TypeInterventionAdmin(admin.ModelAdmin):
    list_display = ["libelle", "est_corrective"]
    search_fields = ["libelle"]


@admin.register(Fournisseur)
class FournisseurAdmin(admin.ModelAdmin):
    list_display = ["nom", "telephone", "email"]
    search_fields = ["nom"]


@admin.register(Technicien)
class TechnicienAdmin(admin.ModelAdmin):
    list_display = ["nom", "prenom", "unite", "utilisateur"]
    list_filter = ["unite"]
    search_fields = ["nom", "prenom"]
