from django.urls import path

from . import views

app_name = "referentiels"

urlpatterns = [
    path("", views.index, name="index"),
    path("<slug:cle>/", views.liste, name="liste"),
    path("<slug:cle>/ajouter/", views.ajouter, name="ajouter"),
    path("<slug:cle>/<int:pk>/modifier/", views.modifier, name="modifier"),
    path("<slug:cle>/<int:pk>/supprimer/", views.supprimer, name="supprimer"),
]
