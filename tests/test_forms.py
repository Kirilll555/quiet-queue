from datetime import timedelta

from pages.forms import ForecastForm, SignUpForm
from pages.models import Cabinet, Institution


def test_signup_fields():
    form = SignUpForm()
    assert list(form.fields) == ["username", "password1", "password2"]
    assert "вымышленный ник" in form.fields["username"].help_text


def test_forecast_choice_scope(place, room, now):
    other = Institution.objects.create(name="Архив", category="Другое")
    foreign = Cabinet.objects.create(institution=other, name="Зал")
    empty = ForecastForm()
    assert list(empty.fields["institution_id"].queryset) == [other, place]
    assert not empty.fields["cabinet_id"].queryset.exists()
    assert empty.fields["visit_date"].widget.attrs["min"] == now.date().isoformat()
    fields = {"institution_id": place.pk, "visit_date": now.date() + timedelta(days=1)}
    form = ForecastForm({**fields, "cabinet_id": foreign.pk})
    assert list(form.fields["cabinet_id"].queryset) == [room]
    assert set(form.errors) == {"cabinet_id"}
    general = ForecastForm(fields)
    assert general.is_valid()
    assert general.cleaned_data["cabinet_id"] is None
