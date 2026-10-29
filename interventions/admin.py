from django.contrib import admin

from .models import Intervention


@admin.register(Intervention)
class InterventionAdmin(admin.ModelAdmin):
    list_display = ["date", "equipement", "type", "technicien", "panne_resolue"]
    list_filter = ["type", "technicien", "panne_resolue"]
    search_fields = ["equipement__nom", "equipement__numero_serie", "commentaire"]
    date_hierarchy = "date"
    readonly_fields = ["cree_par", "cree_le", "modifie_le"]
