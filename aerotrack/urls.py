"""Routes principales d'AéroTrack."""
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "AéroTrack – Administration"
admin.site.site_title = "AéroTrack"
admin.site.index_title = "Gestion des données"

urlpatterns = [
    path("", include("tableau_bord.urls")),
    path("equipements/", include("equipements.urls")),
    path("interventions/", include("interventions.urls")),
    path("emplacements/", include("emplacements.urls")),
    path("referentiels/", include("referentiels.urls")),
    path("comptes/", include("comptes.urls")),
    path("admin/", admin.site.urls),
]
