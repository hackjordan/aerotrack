"""Module 1 : authentification et gestion des utilisateurs."""
from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth import views as auth_views
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST

from .forms import (
    ChangementMotDePasseForm,
    ConnexionForm,
    DefinirMotDePasseForm,
    UtilisateurCreationForm,
    UtilisateurModificationForm,
)
from .roles import ADMINISTRATEUR, role_de, role_requis

User = get_user_model()


# --- F1.1, F1.2, F1.3 : connexion, déconnexion, mot de passe ----------------

class ConnexionView(auth_views.LoginView):
    template_name = "comptes/connexion.html"
    authentication_form = ConnexionForm
    redirect_authenticated_user = True


class DeconnexionView(auth_views.LogoutView):
    """La déconnexion se fait uniquement par un formulaire POST (protection CSRF)."""


class ChangementMotDePasseView(auth_views.PasswordChangeView):
    template_name = "comptes/mot_de_passe.html"
    form_class = ChangementMotDePasseForm
    success_url = reverse_lazy("tableau_bord:accueil")

    def form_valid(self, form):
        messages.success(self.request, "Votre mot de passe a été modifié.")
        return super().form_valid(form)


# --- F1.4, F1.5 : gestion des comptes (administrateur) ----------------------

@role_requis(ADMINISTRATEUR)
def liste_utilisateurs(request):
    recherche = request.GET.get("q", "").strip()
    utilisateurs = User.objects.prefetch_related("groups").order_by("username")
    if recherche:
        utilisateurs = utilisateurs.filter(
            Q(username__icontains=recherche)
            | Q(first_name__icontains=recherche)
            | Q(last_name__icontains=recherche)
        )

    page = Paginator(utilisateurs, 20).get_page(request.GET.get("page"))
    for utilisateur in page:
        utilisateur.role = role_de(utilisateur)

    return render(request, "comptes/utilisateurs.html", {"page": page, "recherche": recherche})


@role_requis(ADMINISTRATEUR)
def ajouter_utilisateur(request):
    form = UtilisateurCreationForm(request.POST or None)
    if form.is_valid():
        utilisateur = form.save()
        messages.success(request, f"Le compte « {utilisateur.username} » a été créé.")
        return redirect("comptes:utilisateurs")
    return render(request, "comptes/utilisateur_form.html", {"form": form, "titre": "Nouveau compte"})


@role_requis(ADMINISTRATEUR)
def modifier_utilisateur(request, pk):
    utilisateur = get_object_or_404(User, pk=pk)
    form = UtilisateurModificationForm(
        request.POST or None, instance=utilisateur, utilisateur_connecte=request.user
    )
    if form.is_valid():
        form.save()
        messages.success(request, f"Le compte « {utilisateur.username} » a été modifié.")
        return redirect("comptes:utilisateurs")
    return render(request, "comptes/utilisateur_form.html", {
        "form": form,
        "titre": f"Modifier le compte « {utilisateur.username} »",
        "utilisateur": utilisateur,
    })


@role_requis(ADMINISTRATEUR)
def reinitialiser_mot_de_passe(request, pk):
    utilisateur = get_object_or_404(User, pk=pk)
    form = DefinirMotDePasseForm(utilisateur, request.POST or None)
    if form.is_valid():
        form.save()
        if utilisateur.pk == request.user.pk:
            update_session_auth_hash(request, utilisateur)
        messages.success(request, f"Le mot de passe de « {utilisateur.username} » a été réinitialisé.")
        return redirect("comptes:utilisateurs")
    return render(request, "comptes/utilisateur_form.html", {
        "form": form,
        "titre": f"Nouveau mot de passe pour « {utilisateur.username} »",
        "utilisateur": utilisateur,
    })


@require_POST
@role_requis(ADMINISTRATEUR)
def basculer_activation(request, pk):
    utilisateur = get_object_or_404(User, pk=pk)
    if utilisateur.pk == request.user.pk:
        messages.error(request, "Vous ne pouvez pas désactiver votre propre compte.")
    else:
        utilisateur.is_active = not utilisateur.is_active
        utilisateur.save(update_fields=["is_active"])
        etat = "réactivé" if utilisateur.is_active else "désactivé"
        messages.success(request, f"Le compte « {utilisateur.username} » a été {etat}.")
    return redirect("comptes:utilisateurs")
