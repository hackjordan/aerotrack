from django.urls import path

from . import views

app_name = "comptes"

urlpatterns = [
    path("connexion/", views.ConnexionView.as_view(), name="connexion"),
    path("deconnexion/", views.DeconnexionView.as_view(), name="deconnexion"),
    path("mot-de-passe/", views.ChangementMotDePasseView.as_view(), name="mot_de_passe"),

    path("utilisateurs/", views.liste_utilisateurs, name="utilisateurs"),
    path("utilisateurs/ajouter/", views.ajouter_utilisateur, name="ajouter"),
    path("utilisateurs/<int:pk>/modifier/", views.modifier_utilisateur, name="modifier"),
    path("utilisateurs/<int:pk>/mot-de-passe/", views.reinitialiser_mot_de_passe, name="reinitialiser"),
    path("utilisateurs/<int:pk>/activation/", views.basculer_activation, name="activation"),
]
