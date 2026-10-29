"""Module 3 : gestion des emplacements."""
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, ProtectedError, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from comptes.roles import ADMINISTRATEUR, TECHNICIEN, role_requis
from equipements.models import Statut

from .forms import EmplacementForm
from .models import Emplacement

TOUS_LES_ROLES = (ADMINISTRATEUR, TECHNICIEN)


@role_requis(*TOUS_LES_ROLES)
def liste(request):
    """F3.2 : liste des emplacements avec le nombre d'équipements."""
    recherche = request.GET.get("q", "").strip()
    emplacements = Emplacement.objects.annotate(
        nb_equipements=Count("equipements"),
        nb_pannes=Count("equipements", filter=Q(equipements__statut=Statut.EN_PANNE)),
    ).order_by("batiment", "zone")  # annotate() ignore Meta.ordering
    if recherche:
        emplacements = emplacements.filter(Q(batiment__icontains=recherche) | Q(zone__icontains=recherche))
    return render(request, "emplacements/liste.html", {
        "page": Paginator(emplacements, 30).get_page(request.GET.get("page")),
        "recherche": recherche,
    })


@role_requis(*TOUS_LES_ROLES)
def detail(request, pk):
    """F3.3 : équipements présents dans un emplacement."""
    emplacement = get_object_or_404(Emplacement, pk=pk)
    equipements = emplacement.equipements.select_related("type")
    compteurs = {code: 0 for code in Statut.values}
    for ligne in equipements.values("statut").annotate(n=Count("pk")):
        compteurs[ligne["statut"]] = ligne["n"]
    return render(request, "emplacements/detail.html", {
        "emplacement": emplacement,
        "page": Paginator(equipements, 20).get_page(request.GET.get("page")),
        "compteurs": [(code, libelle, compteurs[code]) for code, libelle in Statut.choices],
    })


@role_requis(ADMINISTRATEUR)
def ajouter(request):
    """F3.1"""
    form = EmplacementForm(request.POST or None)
    if form.is_valid():
        emplacement = form.save()
        messages.success(request, f"L'emplacement « {emplacement} » a été ajouté.")
        return redirect("emplacements:liste")
    return render(request, "emplacements/form.html", {"form": form, "titre": "Nouvel emplacement"})


@role_requis(ADMINISTRATEUR)
def modifier(request, pk):
    """F3.1"""
    emplacement = get_object_or_404(Emplacement, pk=pk)
    libelle_initial = str(emplacement)
    form = EmplacementForm(request.POST or None, instance=emplacement)
    if form.is_valid():
        form.save()
        messages.success(request, f"L'emplacement « {emplacement} » a été modifié.")
        return redirect("emplacements:detail", pk=pk)
    return render(request, "emplacements/form.html", {
        "form": form, "titre": f"Modifier « {libelle_initial} »", "emplacement": emplacement,
    })


@role_requis(ADMINISTRATEUR)
def supprimer(request, pk):
    """F3.1 : suppression refusée si des équipements s'y trouvent encore."""
    emplacement = get_object_or_404(Emplacement, pk=pk)
    if request.method == "POST":
        try:
            emplacement.delete()
        except ProtectedError:
            messages.error(request, "Cet emplacement contient encore des équipements : déplacez-les d'abord.")
            return redirect("emplacements:detail", pk=pk)
        messages.success(request, f"L'emplacement « {emplacement} » a été supprimé.")
        return redirect("emplacements:liste")
    nb = emplacement.equipements.count()
    return render(request, "confirmer_suppression.html", {
        "objet": emplacement,
        "nature": "l'emplacement",
        "message_blocage": (
            f"Cet emplacement contient {nb} équipement(s). "
            "Déplacez-les vers un autre emplacement avant de le supprimer."
        ) if nb else "",
        "url_annuler": reverse("emplacements:detail", args=[pk]),
    })
