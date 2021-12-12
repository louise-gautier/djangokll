from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from dkllapp.models import Candidat


class NewUserForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def save(self, commit=True):
        user = super(NewUserForm, self).save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user


class MailForm(forms.Form):
    sujet = forms.CharField(label='sujet', max_length=100)
    corps = forms.CharField(label='corps', max_length=100)


class LigueCreationForm(forms.Form):
    nom = forms.CharField(label='nom', max_length=100)


class LigueJoinForm(forms.Form):
    ligue_id = forms.CharField(label='ligue_id', max_length=100)


class ChoixCreationForm(forms.Form):
    pass


class EquipeCreationForm(forms.Form):
    propagation = forms.BooleanField(required=False)
