from django.contrib.auth.forms import UserCreationForm


class SignUpForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        fields = ("username",)
        labels = {"username": "Ник"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].help_text = (
            "Используйте вымышленный ник без ФИО и контактных данных."
        )