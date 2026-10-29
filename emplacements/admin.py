from django.contrib import admin

from .models import Emplacement


@admin.register(Emplacement)
class EmplacementAdmin(admin.ModelAdmin):
    list_display = ["batiment", "zone"]
    list_filter = ["batiment"]
    search_fields = ["batiment", "zone"]
