"""Module 4 : gestion des interventions de maintenance."""
from datetime import date

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from aerotrack.filtres import puce
from comptes.roles import ADMINISTRATEUR, TECHNICIEN, a_un_role, role_requis
from equipements.models import Equipement
from referentiels.models import Technicien, TypeIntervention

from .forms import InterventionForm
from .models import Intervention
from .services import appliquer_statut

TOUS_LES_ROLES = (ADMINISTRATEUR, TECHNICIEN)


def technicien_du_compte(user):
    """Fiche Technicien reliée au compte connecté, ou None."""
    return Technicien.objects.filter(utilisateur=user).first()


def peut_modifier(user, intervention):
    """F4.2 : l'administrateur modifie tout, le technicien seulement ses interventions."""
    if a_un_role(user, ADMINISTRATEUR):
        return True
    return (
        a_un_role(user, TECHNICIEN)
        and intervention.technicien.utilisateur_id is not None
        and intervention.technicien.utilisateur_id == user.pk
    )


def lire_date(valeur):
    try:
        return date.fromisoformat(valeur)
    except (TypeError, ValueError):
        return None


@role_requis(*TOUS_LES_ROLES)
def liste(request):
    """F4.3 : liste filtrée par période, technicien, type ou équipement."""
    filtres = {
        "q": request.GET.get("q", "").strip(),
        "du": request.GET.get("du", ""),
        "au": request.GET.get("au", ""),
        "technicien": request.GET.get("technicien", ""),
        "type": request.GET.get("type", ""),
        "equipement": request.GET.get("equipement", ""),
    }

    techniciens = Technicien.objects.all()
    types = TypeIntervention.objects.all()
    interventions = Intervention.objects.select_related(
        "equipement", "technicien", "type", "equipement__emplacement"
    )
    puces = []

    if filtres["q"]:
        interventions = interventions.filter(
            Q(equipement__nom__icontains=filtres["q"])
            | Q(equipement__numero_serie__icontains=filtres["q"])
            | Q(commentaire__icontains=filtres["q"])
        )
    equipement_filtre = None
    if filtres["equipement"].isdigit() and (
        equipement_filtre := Equipement.objects.filter(pk=filtres["equipement"]).first()
    ):
        interventions = interventions.filter(equipement=equipement_filtre)
        puces.append(puce(request, "Équipement", equipement_filtre.nom, "equipement"))
    if du := lire_date(filtres["du"]):
        interventions = interventions.filter(date__gte=du)
        puces.append(puce(request, "Depuis le", f"{du:%d/%m/%Y}", "du"))
    if au := lire_date(filtres["au"]):
        interventions = interventions.filter(date__lte=au)
        puces.append(puce(request, "Jusqu'au", f"{au:%d/%m/%Y}", "au"))
    if filtres["technicien"].isdigit() and (choix := techniciens.filter(pk=filtres["technicien"]).first()):
        interventions = interventions.filter(technicien=choix)
        puces.append(puce(request, "Technicien", choix, "technicien"))
    if filtres["type"].isdigit() and (choix := types.filter(pk=filtres["type"]).first()):
        interventions = interventions.filter(type=choix)
        puces.append(puce(request, "Type", choix, "type"))

    page = Paginator(interventions, 20).get_page(request.GET.get("page"))
    for intervention in page:
        intervention.modifiable = peut_modifier(request.user, intervention)

    return render(request, "interventions/liste.html", {
        "page": page,
        "filtres": filtres,
        "filtre_actif": bool(filtres["q"] or puces),
        "puces": puces,
        "equipement_filtre": equipement_filtre,
        "techniciens": techniciens,
        "types": types,
        "peut_saisir": a_un_role(request.user, ADMINISTRATEUR, TECHNICIEN),
    })


@role_requis(*TOUS_LES_ROLES)
def detail(request, pk):
    intervention = get_object_or_404(
        Intervention.objects.select_related("equipement", "technicien", "type", "cree_par"), pk=pk
    )
    return render(request, "interventions/detail.html", {
        "intervention": intervention,
        "modifiable": peut_modifier(request.user, intervention),
    })


@role_requis(ADMINISTRATEUR, TECHNICIEN)
def ajouter(request):
    """F4.1 : saisie d'une intervention, puis mise à jour du statut (F4.5)."""
    est_admin = a_un_role(request.user, ADMINISTRATEUR)
    technicien = None
    if not est_admin:
        technicien = technicien_du_compte(request.user)
        if technicien is None:
            messages.error(
                request,
                "Votre compte n'est relié à aucune fiche technicien. "
                "Demandez à l'administrateur de faire ce lien avant de saisir une intervention.",
            )
            return redirect("interventions:liste")

    initial = {}
    if request.GET.get("equipement", "").isdigit():
        initial["equipement"] = request.GET["equipement"]
    if est_admin:
        initial["technicien"] = technicien_du_compte(request.user)

    form = InterventionForm(request.POST or None, initial=initial, choix_technicien=est_admin)
    if form.is_valid():
        with transaction.atomic():
            intervention = form.save(commit=False)
            if technicien is not None:
                intervention.technicien = technicien
            intervention.cree_par = request.user
            intervention.save()
            changement = appliquer_statut(intervention, request.user)
        messages.success(request, "L'intervention a été enregistrée.")
        if changement:
            messages.info(
                request,
                f"Statut de « {intervention.equipement.nom} » mis à jour : "
                f"{intervention.equipement.get_statut_display()}.",
            )
        return redirect("interventions:detail", pk=intervention.pk)

    return render(request, "interventions/form.html", {
        "form": form,
        "titre": "Nouvelle intervention",
        "technicien": technicien,
        "types_correctifs": types_correctifs(),
    })


@role_requis(ADMINISTRATEUR, TECHNICIEN)
def modifier(request, pk):
    """F4.2 : modification (technicien : uniquement les siennes)."""
    intervention = get_object_or_404(Intervention.objects.select_related("technicien"), pk=pk)
    if not peut_modifier(request.user, intervention):
        raise PermissionDenied

    est_admin = a_un_role(request.user, ADMINISTRATEUR)
    form = InterventionForm(request.POST or None, instance=intervention, choix_technicien=est_admin)
    if form.is_valid():
        with transaction.atomic():
            intervention = form.save()
            changement = appliquer_statut(intervention, request.user)
        messages.success(request, "L'intervention a été modifiée.")
        if changement:
            messages.info(
                request,
                f"Statut de « {intervention.equipement.nom} » mis à jour : "
                f"{intervention.equipement.get_statut_display()}.",
            )
        return redirect("interventions:detail", pk=intervention.pk)

    return render(request, "interventions/form.html", {
        "form": form,
        "titre": "Modifier l'intervention",
        "intervention": intervention,
        "technicien": None if est_admin else intervention.technicien,
        "types_correctifs": types_correctifs(),
    })


def types_correctifs():
    """Identifiants des types correctifs, pour afficher la case « panne résolue » au bon moment."""
    return list(TypeIntervention.objects.filter(est_corrective=True).values_list("pk", flat=True))
