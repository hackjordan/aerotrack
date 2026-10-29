from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
    SetPasswordForm,
    UserCreationForm,
)

from aerotrack.forms import BootstrapMixin

from .roles import ROLE_CHOICES, definir_role, role_de

User = get_user_model()


class ConnexionForm(BootstrapMixin, AuthenticationForm):
    error_messages = {
        "invalid_login": "Identifiant ou mot de passe incorrect.",
        "inactive": "Ce compte est désactivé. Contactez l'administrateur.",
    }


class ChangementMotDePasseForm(BootstrapMixin, PasswordChangeForm):
    pass


class DefinirMotDePasseForm(BootstrapMixin, SetPasswordForm):
    pass


class UtilisateurCreationForm(BootstrapMixin, UserCreationForm):
    """Création d'un compte par l'administrateur (F1.4, F1.5)."""

    role = forms.ChoiceField(label="Rôle", choices=ROLE_CHOICES)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ["username", "last_name", "first_name", "email"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Formulaire épuré : pas de texte d'aide sous les champs.
        # Les règles (identifiant, mot de passe) restent contrôlées et
        # s'affichent seulement en cas d'erreur.
        for champ in self.fields.values():
            champ.help_text = ""

    def save(self, commit=True):
        # Le compte doit exister en base avant de lui attribuer un groupe.
        user = super().save(commit=True)
        definir_role(user, self.cleaned_data["role"])
        return user


class UtilisateurModificationForm(BootstrapMixin, forms.ModelForm):
    """
    Modification d'un compte par l'administrateur (F1.4, F1.5).

    Un administrateur ne peut ni changer son propre rôle ni désactiver son
    propre compte : il risquerait de ne plus pouvoir administrer l'application.
    """

    role = forms.ChoiceField(label="Rôle", choices=ROLE_CHOICES)

    class Meta:
        model = User
        fields = ["last_name", "first_name", "email", "is_active"]
        labels = {"is_active": "Compte actif"}
        help_texts = {"is_active": "Décochez pour empêcher la connexion sans supprimer le compte."}

    def __init__(self, *args, utilisateur_connecte=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["role"].initial = role_de(self.instance)
        if self.instance.is_superuser:
            self.fields["role"].disabled = True
            self.fields["role"].help_text = "Superutilisateur : toujours Administrateur."
        if utilisateur_connecte is not None and self.instance.pk == utilisateur_connecte.pk:
            for nom in ("role", "is_active"):
                self.fields[nom].disabled = True
                self.fields[nom].help_text = "Vous ne pouvez pas modifier ce champ sur votre propre compte."

    def save(self, commit=True):
        user = super().save(commit=commit)
        if not self.fields["role"].disabled:
            definir_role(user, self.cleaned_data["role"])
        return user
