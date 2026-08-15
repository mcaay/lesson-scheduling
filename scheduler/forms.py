from django import forms

from .spec_limits import MAX_RAW_SPEC_BYTES


class RawSpecForm(forms.Form):
    raw_spec = forms.CharField(widget=forms.Textarea, strip=False)

    def clean_raw_spec(self):
        raw_spec = self.cleaned_data["raw_spec"]
        if len(raw_spec.encode("utf-8")) > MAX_RAW_SPEC_BYTES:
            raise forms.ValidationError(
                f"The specification cannot exceed {MAX_RAW_SPEC_BYTES // 1000} KB."
            )
        return raw_spec
