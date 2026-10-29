from django import forms

from aerotrack.forms import BootstrapMixin

from .models import Emplacement


class EmplacementForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Emplacement
        fields = ["batiment", "zone"]
