from django import forms
from django.contrib.auth import get_user_model

from aerotrack.forms import BootstrapMixin

from .models import Categorie, Fournisseur, Technicien, TypeEquipement, TypeIntervention


class CategorieForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Categorie
        fields = ["code", "libelle", "ordre"]


class TypeEquipementForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = TypeEquipement
        fields = ["libelle", "categorie"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["categorie"].required = True  # RG7


class TypeInterventionForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = TypeIntervention
        fields = ["libelle", "est_corrective"]


class FournisseurForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Fournisseur
        fields = ["nom", "telephone", "email"]


class CompteChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, user):
        nom = user.get_full_name()
        return f"{user.username} ({nom})" if nom else user.username


class TechnicienForm(BootstrapMixin, forms.ModelForm):
    """
    F5.4 : le lien avec un compte permet au technicien de saisir ses
    interventions et de modifier uniquement les siennes (F4.1, F4.2).
    """

    utilisateur = CompteChoiceField(
        label="Compte utilisateur", queryset=get_user_model().objects.none(), required=False,
        help_text="Compte avec lequel ce technicien se connecte. Chaque compte ne peut être relié "
                  "qu'à une seule fiche.",
    )

    class Meta:
        model = Technicien
        fields = ["nom", "prenom", "unite", "utilisateur"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Comptes actifs pas encore reliés à une autre fiche
        comptes = get_user_model().objects.filter(is_active=True, technicien__isnull=True)
        if self.instance.utilisateur_id:
            comptes = comptes | get_user_model().objects.filter(pk=self.instance.utilisateur_id)
        self.fields["utilisateur"].queryset = comptes.order_by("username")
