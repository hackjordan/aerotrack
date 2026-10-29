"""Module 2 : gestion des équipements."""
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import ProtectedError, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from aerotrack.filtres import puce
from comptes.roles import ADMINISTRATEUR, TECHNICIEN, role_requis
from emplacements.models import Emplacement
from referentiels.models import Categorie, TypeEquipement

from .forms import ChangementStatutForm, EquipementForm
from .models import Equipement, Statut
from .services import changer_statut, enregistrer_changement_statut

TOUS_LES_ROLES = (ADMINISTRATEUR, TECHNICIEN)


@role_requis(*TOUS_LES_ROLES)
def liste(request):
    """F2.4, F2.5 : liste paginée avec recherche et filtres."""
    filtres = {
        "q": request.GET.get("q", "").strip(),
        "categorie": request.GET.get("categorie", ""),
        "type": request.GET.get("type", ""),
        "emplacement": request.GET.get("emplacement", ""),
        "statut": request.GET.get("statut", ""),
    }

    categories = Categorie.objects.all()
    types = TypeEquipement.objects.all()
    emplacements = Emplacement.objects.all()
    equipements = Equipement.objects.select_related("type__categorie", "emplacement")
    puces = []

    if filtres["q"]:
        equipements = equipements.filter(
            Q(nom__icontains=filtres["q"])
            | Q(numero_serie__icontains=filtres["q"])
            | Q(marque__icontains=filtres["q"])
        )
    if filtres["categorie"].isdigit() and (choix := categories.filter(pk=filtres["categorie"]).first()):
        equipements = equipements.filter(type__categorie=choix)
        puces.append(puce(request, "Catégorie", choix, "categorie"))
    if filtres["type"].isdigit() and (choix := types.filter(pk=filtres["type"]).first()):
        equipements = equipements.filter(type=choix)
        puces.append(puce(request, "Type", choix, "type"))
    if filtres["emplacement"].isdigit() and (choix := emplacements.filter(pk=filtres["emplacement"]).first()):
        equipements = equipements.filter(emplacement=choix)
        puces.append(puce(request, "Emplacement", choix, "emplacement"))
    if filtres["statut"] in Statut.values:
        equipements = equipements.filter(statut=filtres["statut"])
        puces.append(puce(request, "Statut", Statut(filtres["statut"]).label, "statut"))

    return render(request, "equipements/liste.html", {
        "page": Paginator(equipements, 20).get_page(request.GET.get("page")),
        "filtres": filtres,
        "filtre_actif": bool(filtres["q"] or puces),
        "puces": puces,
        "categories": categories,
        "types": types,
        "emplacements": emplacements,
        "statuts": Statut.choices,
    })


@role_requis(*TOUS_LES_ROLES)
def detail(request, pk):
    """F2.6 : fiche détaillée avec historique."""
    equipement = get_object_or_404(
        Equipement.objects.select_related("type__categorie", "emplacement", "fournisseur"), pk=pk
    )
    interventions = equipement.interventions.select_related("type", "technicien")
    return render(request, "equipements/detail.html", {
        "equipement": equipement,
        "interventions": interventions[:10],
        "nb_interventions": interventions.count(),
        # F4.4 : historique des pannes
        "nb_pannes": equipement.historique_statuts.filter(nouveau_statut=Statut.EN_PANNE).count(),
        "derniere_panne": equipement.historique_statuts.filter(nouveau_statut=Statut.EN_PANNE).first(),
        "nb_correctives": interventions.filter(type__est_corrective=True).count(),
        "historique": equipement.historique_statuts.select_related("auteur")[:50],
        "form_statut": ChangementStatutForm(equipement=equipement),
    })


@role_requis(ADMINISTRATEUR)
def ajouter(request):
    """F2.1"""
    form = EquipementForm(request.POST or None)
    if form.is_valid():
        with transaction.atomic():
            equipement = form.save()
            enregistrer_changement_statut(equipement, "", request.user, "Ajout au parc")
        messages.success(request, f"L'équipement « {equipement.nom} » a été ajouté.")
        return redirect("equipements:detail", pk=equipement.pk)
    return render(request, "equipements/form.html", {"form": form, "titre": "Nouvel équipement"})


@role_requis(ADMINISTRATEUR)
def modifier(request, pk):
    """F2.2"""
    equipement = get_object_or_404(Equipement, pk=pk)
    # Le formulaire modifie l'instance pendant la validation : on retient les valeurs d'origine avant.
    ancien_statut = equipement.statut
    nom_initial = equipement.nom
    form = EquipementForm(request.POST or None, instance=equipement)
    if form.is_valid():
        with transaction.atomic():
            form.save()
            enregistrer_changement_statut(equipement, ancien_statut, request.user, "Modification de la fiche")
        messages.success(request, f"L'équipement « {equipement.nom} » a été modifié.")
        return redirect("equipements:detail", pk=equipement.pk)
    return render(request, "equipements/form.html", {
        "form": form,
        "titre": f"Modifier « {nom_initial} »",
        "equipement": equipement,
    })


@role_requis(ADMINISTRATEUR)
def supprimer(request, pk):
    """F2.3 : suppression après confirmation."""
    equipement = get_object_or_404(Equipement, pk=pk)
    if request.method == "POST":
        try:
            equipement.delete()
        except ProtectedError:
            messages.error(
                request,
                "Cet équipement ne peut pas être supprimé : il possède des interventions "
                "enregistrées. Son historique doit être conservé.",
            )
            return redirect("equipements:detail", pk=pk)
        messages.success(request, f"L'équipement « {equipement.nom} » a été supprimé.")
        return redirect("equipements:liste")
    return render(request, "equipements/confirmer_suppression.html", {
        "equipement": equipement,
        "nb_interventions": equipement.interventions.count(),
    })


@require_POST
@role_requis(ADMINISTRATEUR, TECHNICIEN)
def modifier_statut(request, pk):
    """F2.7 : changement de statut depuis la fiche."""
    equipement = get_object_or_404(Equipement, pk=pk)
    form = ChangementStatutForm(request.POST, equipement=equipement)
    if form.is_valid():
        changer_statut(equipement, form.cleaned_data["statut"], request.user, form.cleaned_data["commentaire"])
        messages.success(request, f"Statut mis à jour : {equipement.get_statut_display()}.")
    else:
        for erreurs in form.errors.values():
            for erreur in erreurs:
                messages.error(request, erreur)
    return redirect("equipements:detail", pk=pk)
