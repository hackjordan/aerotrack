from django import forms
from django.db.models import F

from aerotrack.forms import BootstrapMixin
from referentiels.models import TypeEquipement

from .models import Equipement, Statut


class EquipementForm(BootstrapMixin, forms.ModelForm):
    """Ajout et modification d'un équipement (F2.1, F2.2)."""

    class Meta:
        model = Equipement
        fields = [
            "nom", "numero_serie", "marque", "type", "emplacement",
            "fournisseur", "date_installation", "statut",
        ]
        widgets = {
            "date_installation": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Liste des types regroupée par catégorie (Communication, Navigation…)
        types = TypeEquipement.objects.select_related("categorie").order_by(
            F("categorie__ordre").asc(nulls_last=True), "libelle"
        )
        groupes = {}
        for t in types:
            groupes.setdefault(str(t.categorie or "Non classé"), []).append((t.pk, t.libelle))
        self.fields["type"].choices = [("", "---------"), *groupes.items()]

    def clean_numero_serie(self):
        """RG6 : message clair sur le champ si le numéro de série existe déjà."""
        numero = self.cleaned_data["numero_serie"].strip()
        doublons = Equipement.objects.filter(numero_serie__iexact=numero)
        if self.instance.pk:
            doublons = doublons.exclude(pk=self.instance.pk)
        existant = doublons.first()
        if existant:
            raise forms.ValidationError(
                f"Ce numéro de série est déjà utilisé par l'équipement « {existant.nom} »."
            )
        return numero


class ChangementStatutForm(BootstrapMixin, forms.Form):
    """Changement rapide du statut depuis la fiche (F2.7)."""

    statut = forms.ChoiceField(label="Nouveau statut", choices=[("", "— Choisir —"), *Statut.choices])
    commentaire = forms.CharField(
        label="Commentaire", required=False, max_length=255,
        widget=forms.TextInput(attrs={"placeholder": "Exemple : perte de signal constatée à 14 h"}),
    )

    def __init__(self, *args, equipement, **kwargs):
        super().__init__(*args, **kwargs)
        self.equipement = equipement

    def clean_statut(self):
        statut = self.cleaned_data["statut"]
        if statut == self.equipement.statut:
            raise forms.ValidationError(
                f"L'équipement est déjà « {self.equipement.get_statut_display()} »."
            )
        return statut
