from django.contrib.auth.forms import UserCreationForm
from django import forms
from django.utils import timezone

from .models import Institution, Cabinet


class SignUpForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        fields = ("username",)
        labels = {"username": "Ник"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].help_text = (
            "Используйте вымышленный ник без ФИО и контактных данных."
        )


class ForecastForm(forms.Form):
    institution_id = forms.ModelChoiceField(
        label="Учреждение",
        queryset=Institution.objects.none(),
        empty_label="Выберите учреждение",
        widget=forms.Select(attrs={"id": "institution_id"}),
    )
    cabinet_id = forms.ModelChoiceField(
        label="Кабинет — необязательно",
        queryset=Cabinet.objects.none(),
        required=False,
        empty_label="Без указания кабинета",
        widget=forms.Select(attrs={
            "id": "cabinet_id",
            "aria-describedby": "cabinet-hint",
        }),
    )
    visit_date = forms.DateField(
        label="Дата планового посещения",
        initial=timezone.localdate,
        input_formats=["%Y-%m-%d"],
        widget=forms.DateInput(
            format="%Y-%m-%d",
            attrs={"type": "date"},
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["institution_id"].queryset = (
            Institution.objects.order_by("name")
        )
        self.fields["visit_date"].widget.attrs["min"] = (
            timezone.localdate().isoformat()
        )

        institution_id = self.data.get("institution_id", "")
        cabinet_id = self.data.get("cabinet_id", "")

        try:
            institution_id = int(institution_id)
        except (ValueError, TypeError):
            institution_id = None

        if institution_id is not None:
            self.fields["cabinet_id"].queryset = (
                Cabinet.objects.filter(
                    institution_id=institution_id
                ).order_by("name")
            )

        self.fields["cabinet_id"].widget.attrs[
            "data-selected-cabinet"
        ] = cabinet_id

    def clean_visit_date(self):
        visit_date = self.cleaned_data["visit_date"]

        if visit_date < timezone.localdate():
            raise forms.ValidationError(
                "Выберите сегодняшнюю или будущую дату."
            )

        return visit_date