from django import forms
from django.utils import timezone

from aerotrack.forms import BootstrapMixin

from .models import Intervention


class InterventionForm(BootstrapMixin, forms.ModelForm):
    """
    Saisie et modification d'une intervention (F4.1, F4.2).

    Un technicien saisit toujours en son nom : le champ « technicien » n'est
    proposé qu'à l'administrateur.
    """

    class Meta:
        model = Intervention
        fields = ["date", "equipement", "type", "technicien", "commentaire", "panne_resolue"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "commentaire": forms.Textarea(attrs={
                "rows": 4, "placeholder": "Travaux réalisés, pièces changées, observations…",
            }),
        }
        # L'explication de « panne résolue » est déjà affichée en haut du formulaire.
        help_texts = {"panne_resolue": ""}

    def __init__(self, *args, choix_technicien=True, **kwargs):
        super().__init__(*args, **kwargs)
        if not choix_technicien:
            del self.fields["technicien"]
        self.fields["equipement"].queryset = self.fields["equipement"].queryset.select_related("type")

    def clean_date(self):
        date = self.cleaned_data["date"]
        if date > timezone.localdate():
            raise forms.ValidationError("La date d'une intervention ne peut pas être dans le futur.")
        return date

    def clean(self):
        donnees = super().clean()
        type_intervention = donnees.get("type")
        # « Panne résolue » n'a de sens que pour une intervention corrective.
        if type_intervention and not type_intervention.est_corrective:
            donnees["panne_resolue"] = False
        return donnees
