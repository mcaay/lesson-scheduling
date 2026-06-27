from django import forms


class RawSpecForm(forms.Form):
    raw_spec = forms.CharField(widget=forms.Textarea, strip=False)
