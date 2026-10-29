from django.contrib import admin

from .models import JournalAction


@admin.register(JournalAction)
class JournalActionAdmin(admin.ModelAdmin):
    """Journal en lecture seule : personne ne peut le modifier."""

    list_display = ["date", "auteur", "action", "objet_type", "objet_libelle"]
    list_filter = ["action", "objet_type"]
    search_fields = ["objet_libelle", "details"]
    date_hierarchy = "date"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
