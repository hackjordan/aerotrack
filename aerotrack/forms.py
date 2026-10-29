"""Outils de formulaire communs à tous les modules."""
from django import forms


class BootstrapMixin:
    """
    Ajoute les classes Bootstrap 5 aux champs d'un formulaire,
    et la classe « is-invalid » aux champs en erreur après validation.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for champ in self.fields.values():
            widget = champ.widget
            if isinstance(widget, forms.CheckboxInput):
                classe = "form-check-input"
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                classe = "form-select"
            else:
                classe = "form-control"
            widget.attrs["class"] = f"{widget.attrs.get('class', '')} {classe}".strip()

    def full_clean(self):
        super().full_clean()
        for nom in self.errors:
            if nom in self.fields:
                widget = self.fields[nom].widget
                widget.attrs["class"] = f"{widget.attrs.get('class', '')} is-invalid".strip()
