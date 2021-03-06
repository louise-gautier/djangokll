from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.forms import ChoiceField, PasswordInput

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
    ('Orange', "Orange"),
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
    new_episode = forms.IntegerField(label='new_episode')


class ActivateChoiceForm(forms.Form):
    pass


class MailAdminForm(forms.Form):
    sujet = forms.CharField(label='sujet', max_length=999)
    corps = forms.CharField(label='corps', max_length=99999)
    admin = forms.BooleanField(required=False)
    users = forms.BooleanField(required=False)


class NotifAdminForm(forms.Form):
    message = forms.CharField(label='corps', max_length=9999)
    lien = forms.CharField(label='lien', max_length=999)


class ModifierRegleForm(forms.Form):
    regle_a_modifier = forms.IntegerField(label='sujet')


class PronoAdminForm(forms.Form):
    prono_choisi = forms.IntegerField(label='prono_choisi')


class AjouterQuestionForm(forms.Form):
    enonce = forms.CharField(label='enonce', max_length=999)
    propositions = forms.CharField(label='propositions', max_length=999)
    episode = forms.IntegerField(label='episode')
    bonus = forms.IntegerField(label='bonus')
    malus = forms.IntegerField(label='malus')
    is_mail = forms.BooleanField(required=False)


class CreerRegleForm(forms.Form):
    contenu = forms.CharField(label='contenu', max_length=999)
    points_1 = forms.IntegerField(required=True)
    points_2 = forms.IntegerField(required=True)
    points_3 = forms.IntegerField(required=True)


liste_typage = (
    ('1', "Poulain seul"),
    ('2', "Podium seul"),
    ('3', "Gagnant"),
    ('12', "Poulain et Podium"),
    ('13', "Poulain et Gagnant"),
    ('23', "Podium et Gagnant"),
    ('123', "Poulain, Podium et Gagnant")
)


class AjouterEvenementForm(forms.Form):
    episode = forms.IntegerField(required=True)
    typage = ChoiceField(choices=liste_typage, required=True)


class MessageMurForm(forms.Form):
    nouveau_parent = forms.CharField(label='corps', max_length=9999)


class PictoForm(forms.Form):
    pass


class ProfilMailForm(forms.Form):
    mail = forms.BooleanField(required=False)


class ChangerIdentifiantForm(forms.Form):
    new_username = forms.CharField(label='nom', max_length=100)


class ReinitailiserMdpForm(forms.Form):
    email = forms.CharField(label='email')


class PronosGuessForm(forms.Form):
    pass
