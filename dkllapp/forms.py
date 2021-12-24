from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.forms import ChoiceField

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


GROUPES_CHOICES = (
    ('Bleu', "Bleu"),
    ('Jaune', "Jaune"),
    ('Rouge', "Rouge"),
    ('Violet', "Violet"),
    ('Blanc', "Blanc"),
    ('Eliminés', "Eliminés")
)


class ChangerEquipeTVForm(forms.Form):
    groupes = ChoiceField(choices=GROUPES_CHOICES, required=True)


STATUTS_CHOICES = (
    ('En jeu', "En jeu"),
    ('Eliminé', "Eliminé")
)


class ChangerStatutForm(forms.Form):
    statuts = ChoiceField(choices=STATUTS_CHOICES, required=True)


class EquipeCreationForm(forms.Form):
    propagation = forms.BooleanField(required=False)


class EpisodeChangeForm(forms.Form):
    new_episode = forms.CharField(label='new_episode', max_length=100)


class ActivateChoiceForm(forms.Form):
    pass


class MailAdminForm(forms.Form):
    sujet = forms.CharField(label='sujet', max_length=999)
    corps = forms.CharField(label='corps', max_length=9999)
    admin = forms.BooleanField(required=False)
    users = forms.BooleanField(required=False)

