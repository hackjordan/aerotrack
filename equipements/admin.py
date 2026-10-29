from django.contrib import admin

from .models import Equipement, HistoriqueStatut


class HistoriqueStatutInline(admin.TabularInline):
    model = HistoriqueStatut
    extra = 0
    can_delete = False
    readonly_fields = ["date", "ancien_statut", "nouveau_statut", "auteur", "commentaire"]

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Equipement)
class EquipementAdmin(admin.ModelAdmin):
    list_display = ["nom", "numero_serie", "marque", "type", "emplacement", "statut"]
    list_filter = ["statut", "type", "emplacement"]
    search_fields = ["nom", "numero_serie", "marque"]
    inlines = [HistoriqueStatutInline]


@admin.register(HistoriqueStatut)
class HistoriqueStatutAdmin(admin.ModelAdmin):
    list_display = ["date", "equipement", "ancien_statut", "nouveau_statut", "auteur"]
    list_filter = ["nouveau_statut"]
    date_hierarchy = "date"
