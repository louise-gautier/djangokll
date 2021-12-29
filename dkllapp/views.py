import random

import requests
import os

from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.contrib.sites.shortcuts import get_current_site
from django.contrib import messages
from django.core.mail import send_mail
from django.db.models import Sum, Q
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseRedirect
from django.template.loader import render_to_string

from django.utils.encoding import force_bytes, force_text
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.conf import settings
from django.urls import reverse
from django.utils.timezone import now
from django.views import generic

from django.http.response import JsonResponse, HttpResponse
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
from django import forms

from webpush import send_user_notification
import json
from urllib.request import urlopen
from urllib.request import Request

from .forms import NewUserForm, MailForm, LigueCreationForm, EquipeCreationForm, LigueJoinForm, ChoixCreationForm, \
    EpisodeChangeForm, ActivateChoiceForm, ChangerEquipeTVForm, ChangerStatutForm, MailAdminForm, NotifAdminForm, \
    ModifierRegleForm, CreerRegleForm, AjouterEvenementForm, MessageMurForm, PronoAdminForm, AjouterQuestionForm
from .models import Candidat, Ligue, Mur, Notif, Choix, Episode, ActivationChoix, Membre, Equipe, Evenement, Points, \
    Regle, Blip, UserProfile, Question, Guess, Proposition, PointsFeu
from .token import account_activation_token


#v############################### FONCTIONS GENERIQUES #########################################
def is_admin(user_id):
    admins = [1, 2]
    bool_admin = False
    if user_id in admins:
        bool_admin = True
    return bool_admin


def episode_en_cours():
    ep = Episode.objects.values('valeur').latest('insert_datetime')
    return ep['valeur']


def is_poulains():
    etat = ActivationChoix.objects.filter(id=1).values().latest('insert_datetime')['etat']
    if etat == 1:
        activation_poulains = True
    else:
        activation_poulains = False
    return activation_poulains


def is_podium():
    etat = ActivationChoix.objects.filter(id=2).values().latest('insert_datetime')['etat']
    if etat == 1:
        activation_podium = True
    else:
        activation_podium = False
    return activation_podium


def is_gagnant():
    etat = ActivationChoix.objects.filter(id=3).values().latest('insert_datetime')['etat']
    if etat == 1:
        activation_gagnant = True
    else:
        activation_gagnant = False
    return activation_gagnant


def nbr_par_type(type_choix):
    if type_choix == '1':
        return 6
    elif type_choix == '2':
        return 3
    elif type_choix == '3':
        return 1
    else:
        return 0


def admin_activation_choix(type_activation, type_choix):
    all_ac = ActivationChoix.objects.all()
    print('0', all_ac)
    etat_a_changer = ActivationChoix.objects.filter(nom=type_choix).first()
    print('1', etat_a_changer)
    if type_activation == 'activate':
        etat_a_changer.etat = 1
    else:
        etat_a_changer.etat = 0
    print('2', etat_a_changer.nom, etat_a_changer.etat)
    etat_a_changer.save()


def points_ligue_episode(ligue_id, un_episode):
    membres = Membre.objects.filter(ligue_id=ligue_id).values('ligue_id', 'user_id', 'user__user__username', 'user__img')
    if int(un_episode) == 0:
        points = Points.objects.filter(ligue_id=ligue_id)\
            .values('ligue_id', 'user_id')\
            .annotate(Sum('somme_points_poulains')) \
            .annotate(Sum('somme_points_podium')) \
            .annotate(Sum('somme_points_gagnant')) \
            .annotate(Sum('somme_points_selon_types'))
    else:
        points = Points.objects.filter(ligue_id=ligue_id).filter(episode=un_episode)\
            .values('ligue_id', 'user_id')\
            .annotate(Sum('somme_points_poulains')) \
            .annotate(Sum('somme_points_podium')) \
            .annotate(Sum('somme_points_gagnant')) \
            .annotate(Sum('somme_points_selon_types'))
    membres_unsorted = []
    for membre in membres:
        marqueur = 'lost'
        for membre_points in points:
            if membre_points['user_id'] == membre['user_id']:
                membre_avec_points = {
                    'id': membre['user_id'],
                    'username': membre['user__user__username'],
                    'img': membre['user__img'],
                    'points_poulains': membre_points['somme_points_poulains__sum'],
                    'points_podium': membre_points['somme_points_podium__sum'],
                    'points_gagnant': membre_points['somme_points_gagnant__sum'],
                    'points_candidats': membre_points['somme_points_selon_types__sum']
                }
                membres_unsorted.append(membre_avec_points)
                marqueur = 'found'
            else:
                pass
        if marqueur == 'found':
            pass
        else:
            membre_avec_points = {
                'id': membre['user_id'],
                'username': membre['user__user__username'],
                'img': membre['user__img'],
                'points_poulains': 0,
                'points_podium': 0,
                'points_gagnant': 0,
                'points_candidats': 0
            }
            membres_unsorted.append(membre_avec_points)
    membres_sorted = sorted(membres_unsorted, key=lambda i: i['points_candidats'], reverse=True)
    rang = 1
    for joueur in membres_sorted:
        joueur['rang'] = rang
        rang = rang + 1
    return membres_sorted


##########################################REGISTRATION ET LOGIN################################
def register_request(request):
    if request.method == "POST":
        form = NewUserForm(request.POST)
        if form.is_valid():
            print('form.is_valid()')
            user = form.save()
            user.refresh_from_db()  # load the profile instance created by the signal
            user.userprofile.img = 'dkllapp/img/kitchen/default.png'
            user.userprofile.boolemail = True
            current_site = get_current_site(request)
            context = {
                'user': user,
                'domain': current_site.domain,
                'uidb64': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': account_activation_token.make_token(user), }
            #mail
            subject = "Activation de ton compte Pili Pili"
            message = render_to_string('dkllapp/account_activation_email.html', context)
            email_from = settings.EMAIL_HOST_USER
            recipient_list = [user.email]
            send_mail(subject, message, email_from, recipient_list)
            user.save()
            return redirect('dkllapp:account_activation_sent')

        messages.error(request, "Echec de la création du compte. Réessaye en respectant les critères.")
    form = NewUserForm()
    return render(request=request, template_name="dkllapp/register.html", context={"register_form": form})


def account_activation_sent(request):
    return render(request, 'dkllapp/account_activation_sent.html')


def activate(request, uidb64, token):
    try:
        uid = force_text(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.userprofile.email_confirmed = True
        user.save()
        login(request, user)
        return redirect('dkllapp:index')
    else:
        return render(request, 'account_activation_invalid.html')


def login_request(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                if user.userprofile.email_confirmed is True:
                    login(request, user)
                    return redirect("dkllapp:index")
                else:
                    messages.error(request, "Tu n'as pas confirmé ton e-mail.")
            else:
                messages.error(request, "Login ou mot de passe incorrect.")
        else:
            messages.error(request, "Login ou mot de passe incorrect.")
    form = AuthenticationForm()
    return render(request=request, template_name="dkllapp/login.html", context={"login_form": form})


@login_required
def logout_request(request):
    logout(request)
    return redirect("dkllapp:index")


def equipe_pour_une_ligue(user, ligue_id, episode, selected_candidat):
    lignes_equipe = Equipe.objects \
        .filter(user_id=user.id) \
        .filter(ligue_id=ligue_id) \
        .filter(episode=episode) \
        .filter(type=1) \
        .delete()
    for candidat_id in selected_candidat:
        nouvelle_ligne_equipe = Equipe()
        nouvelle_ligne_equipe.user_id = user.id
        nouvelle_ligne_equipe.ligue_id = ligue_id
        nouvelle_ligne_equipe.episode = episode
        nouvelle_ligne_equipe.candidat_id = candidat_id
        nouvelle_ligne_equipe.type = 1
        nouvelle_ligne_equipe.save()


def choix_pour_un_type(user, type, selected_candidat):
    lignes_equipe = Choix.objects \
        .filter(user_id=user.id) \
        .filter(type=type) \
        .delete()
    for candidat_id in selected_candidat:
        nouvelle_ligne_choix = Choix()
        nouvelle_ligne_choix.user_id = user.id
        nouvelle_ligne_choix.candidat_id = candidat_id
        nouvelle_ligne_choix.type = type
        nouvelle_ligne_choix.save()


##########################################FIN REGISTRATION ET LOGIN################################
######################################HOME - INDEX################################
@login_required
def index(request):
    poulains_ouvert = is_poulains()
    podium_ouvert = is_podium()
    gagnant_ouvert = is_gagnant()
    ligues = Membre.objects\
        .filter(user_id=request.user.id).order_by('insert_datetime')\
        .values('id', 'ligue_id', 'ligue__nom')
    episode_en_cours_ = episode_en_cours()
    notif = Notif.objects.latest('insert_datetime')
    choix_user = Choix.objects \
        .filter(user_id=request.user.id).order_by('candidat_id') \
        .values('id', 'type', 'candidat_id', 'candidat__nom', 'candidat__equipe_tv', 'candidat__chemin_img',
                'candidat__statut', 'candidat__statut_bool')
    lignes_equipes = []
    for ligue in ligues:
        bloc_equipe = Equipe.objects\
            .filter(user=request.user.id)\
            .filter(episode=episode_en_cours_)\
            .filter(ligue_id=ligue['ligue_id'])\
            .filter(type=1)\
            .order_by('candidat_id')\
            .values('id', 'type', 'candidat_id', 'candidat__nom', 'candidat__equipe_tv', 'candidat__chemin_img',
                    'candidat__statut', 'candidat__statut_bool')
        for ligne in bloc_equipe:
            ligne_equipe = {'id': ligue['ligue_id'], 'ligne': ligne}
            lignes_equipes.append(ligne_equipe)
    return render(request=request,
                  template_name="dkllapp/index.html",
                  context={'ligues': ligues, 'notif': notif, 'choix_user': choix_user, 'lignes_equipes': lignes_equipes,
                           'before_creation': 'index',
                           'poulains_ouvert': poulains_ouvert, 'podium_ouvert': podium_ouvert, 'gagnant_ouvert': gagnant_ouvert,
                           'isadmin': is_admin(request.user.id)})


##########################################Admin################################
@login_required
def admin(request):
    ligues = Membre.objects\
        .filter(user_id=request.user.id).order_by('insert_datetime')\
        .values('id', 'ligue_id', 'ligue__nom')
    episode_en_cours_ = episode_en_cours()
    regles = Regle.objects.all().order_by('insert_datetime')
    questions = Question.objects.all().order_by('episode').order_by('-insert_datetime')
    questions_plus = []
    for question in questions:
        propositions = Proposition.objects.filter(question_id=question.id)
        repondu = False
        for proposition in propositions:
            if proposition.pertinence:
                repondu = True
        questions_plus.append({'question': question, 'propositions': propositions, 'repondu': repondu})
    evenements = Evenement.objects.all().order_by('-insert_datetime').values('id', 'user__user__username', 'regle__contenu', 'candidat__nom',
                                                                             'candidat__chemin_img', 'episode', 'typage', 'insert_datetime')
    if request.method == 'POST':
        type_choix = 'activate' if '_activate_' in list(request.POST)[1] \
            else 'deactivate' if '_deactivate_' in list(request.POST)[1] else ''
        type_activation = 'poulains' if 'poulains' in list(request.POST)[1] \
            else 'podium' if 'podium' in list(request.POST)[1] \
            else 'gagnant' if 'gagnant' in list(request.POST)[1] else ''
        if (type_choix, type_activation) == ('', ''):
            form_mail = MailAdminForm(request.POST)
            form_notif = NotifAdminForm(request.POST)
            form_regle = ModifierRegleForm(request.POST)
            form_pronos = PronoAdminForm(request.POST)
            if 'ajouter_question' in request.POST:
                return redirect('dkllapp:ajouter_question', 0)
            if 'modifier_question' in request.POST:
                if request.POST['prono_choisi']:
                    return redirect('dkllapp:ajouter_question', request.POST['prono_choisi'])
                else:
                    return redirect('dkllapp:admin')
            if 'ajouter_reponse' in request.POST:
                if request.POST['prono_choisi']:
                    return redirect('dkllapp:ajouter_reponse', request.POST['prono_choisi'])
                else:
                    return redirect('dkllapp:admin')
            if form_mail.is_valid():
                subject = form_mail.cleaned_data.get("sujet")
                message = form_mail.cleaned_data.get("corps")
                email_from = settings.EMAIL_HOST_USER
                recipient_list = []
                if form_mail.cleaned_data.get('users') is True:
                    for user in User.objects.all().values('email'):
                        recipient_list.append(user)
                elif form_mail.cleaned_data.get('admin') is True:
                    recipient_list = ['louise_gautier@orange.fr', 'louise2004gautier@gmail.com']
                else:
                    return redirect('dkllapp:admin')
                send_mail(subject, message, email_from, recipient_list)
            if form_notif.is_valid():
                nouvelle_notif = Notif()
                nouvelle_notif.message = form_notif.cleaned_data.get('message')
                nouvelle_notif.save()
                return redirect('dkllapp:admin')
            if form_regle.is_valid():
                nouvelle_notif = Regle.objects.filter(id=form_regle.cleaned_data.get('regle_a_modifier')).first()
                if nouvelle_notif:
                    return redirect('dkllapp:modifier_regle', nouvelle_notif.id)
                else:
                    return redirect('dkllapp:admin')
        else:
            admin_activation_choix(type_choix, type_activation)
    form_mail = MailAdminForm()
    form_notif = NotifAdminForm()
    form_regle = ModifierRegleForm()
    return render(request=request,
                  template_name="dkllapp/admin.html",
                  context={'ligues': ligues, 'episode_en_cours_': episode_en_cours_,
                           'form_mail': form_mail, 'form_notif': form_notif, 'form_regle': form_regle,
                           'regles': regles, 'evenements': evenements, 'questions_plus': questions_plus,
                           'isadmin': is_admin(request.user.id)})


@login_required
def changer_episode(request):
    ligues = Membre.objects\
        .filter(user_id=request.user.id).order_by('insert_datetime')\
        .values('id', 'ligue_id', 'ligue__nom')
    if request.method == "POST":
        form = EpisodeChangeForm(request.POST)
        if form.is_valid():
            episode_a_changer = Episode.objects.filter(nom='episode').first()
            episode_a_changer.valeur = form.cleaned_data.get('new_episode')
            episode_a_changer.save()

            membres = Membre.objects.all().order_by('id')
            for membre in membres:
                poulains = Choix.objects.filter(user_id=membre.user_id).filter(type=1).order_by('id')
                print('poulains', poulains)
                if len(poulains) == 6:
                    equipe_poulains = Equipe.objects.filter(user_id=membre.user_id).filter(ligue_id=membre.ligue_id)\
                        .filter(type=1).filter(episode=episode_en_cours()).order_by('id')
                    print('equipe_poulains', equipe_poulains)
                    if len(equipe_poulains) >= 1:
                        pass
                    else:
                        poulains_id = []
                        for candidat in poulains:
                            poulains_id.append(candidat.candidat_id)
                        print('poulains_id', poulains_id)
                        nouvelle_ligne_equipe = Equipe()
                        nouvelle_ligne_equipe.user_id = request.user.id
                        nouvelle_ligne_equipe.ligue_id = membre.ligue_id
                        nouvelle_ligne_equipe.candidat_id = random.choice(poulains_id)
                        nouvelle_ligne_equipe.episode = episode_en_cours()
                        nouvelle_ligne_equipe.type = 1
                        nouvelle_ligne_equipe.save()

                    podium = Choix.objects.filter(user_id=membre.user_id).filter(type=2).order_by('id')
                    equipe_podium = Equipe.objects.filter(user_id=membre.user_id).filter(ligue_id=membre.ligue_id)\
                        .filter(type=2).filter(episode=episode_en_cours()).order_by('id')
                    if len(equipe_podium) >= 1:
                        pass
                    else:
                        for candidat in podium:
                            nouvelle_ligne_equipe = Equipe()
                            nouvelle_ligne_equipe.user_id = request.user.id
                            nouvelle_ligne_equipe.ligue_id = membre.ligue_id
                            nouvelle_ligne_equipe.candidat_id = candidat.candidat_id
                            nouvelle_ligne_equipe.episode = episode_en_cours()
                            nouvelle_ligne_equipe.type = 2
                            nouvelle_ligne_equipe.save()

                    gagnant = Choix.objects.filter(user_id=membre.user_id).filter(type=3).order_by('id')
                    equipe_gagnant = Equipe.objects.filter(user_id=membre.user_id).filter(ligue_id=membre.ligue_id)\
                        .filter(type=3).filter(episode=episode_en_cours()).order_by('id')
                    if len(equipe_gagnant) >= 1:
                        pass
                    else:
                        for candidat in gagnant:
                            nouvelle_ligne_equipe = Equipe()
                            nouvelle_ligne_equipe.user_id = request.user.id
                            nouvelle_ligne_equipe.ligue_id = membre.ligue_id
                            nouvelle_ligne_equipe.candidat_id = candidat.candidat_id
                            nouvelle_ligne_equipe.episode = episode_en_cours()
                            nouvelle_ligne_equipe.type = 3
                            nouvelle_ligne_equipe.save()
                else:
                    pass
            return redirect('dkllapp:admin')
    form = EpisodeChangeForm()
    return render(request=request,
                  template_name="dkllapp/changer_episode.html",
                  context={'ligues': ligues, 'form': form,
                           'isadmin': is_admin(request.user.id)})


@login_required
def changer_equipe_tv(request):
    ligues = Membre.objects\
        .filter(user_id=request.user.id).order_by('insert_datetime')\
        .values('id', 'ligue_id', 'ligue__nom')
    episode_en_cours_ = episode_en_cours()
    candidats = Candidat.objects.all().order_by('id')\
        .values('id', 'nom', 'equipe_tv', 'chemin_img', 'statut', 'statut_bool', 'form_id')
    new_fields = {}
    for candidat in candidats:
        new_fields[candidat['form_id']] = forms.BooleanField(required=False)
    DynamicChangerEquipeTVForm = type('DynamicChangerEquipeTVForm', (ChangerEquipeTVForm,), new_fields)
    if request.method == "POST":
        form = DynamicChangerEquipeTVForm(request.POST)
        if form.is_valid():
            selected_candidat = []
            for field in form.cleaned_data:
                if "bool" in field and form.cleaned_data[field]:
                    selected_candidat.append(int(field[4:6]))
            if len(selected_candidat) > 0:
                for candidat in selected_candidat:
                    candidat_a_changer = Candidat.objects.filter(id=candidat).first()
                    candidat_a_changer.equipe_tv = form.cleaned_data.get('groupes')
                    candidat_a_changer.save()
                return redirect('dkllapp:admin')
            else:
                return redirect('dkllapp:changer_equipe_tv')
    form = DynamicChangerEquipeTVForm()
    print('form', form)
    print('candidats', candidats)
    return render(request=request,
                  template_name="dkllapp/changer_equipe_tv.html",
                  context={'ligues': ligues, 'episode_en_cours_': episode_en_cours_,
                           'form': form, 'candidats': candidats,
                           'isadmin': is_admin(request.user.id)})


@login_required
def changer_statut(request):
    ligues = Membre.objects\
        .filter(user_id=request.user.id).order_by('insert_datetime')\
        .values('id', 'ligue_id', 'ligue__nom')
    episode_en_cours_ = episode_en_cours()
    candidats = Candidat.objects.all().order_by('id')\
        .values('id', 'nom', 'equipe_tv', 'chemin_img', 'statut', 'statut_bool', 'form_id')
    new_fields = {}
    for candidat in candidats:
        new_fields[candidat['form_id']] = forms.BooleanField(required=False)
    DynamicChangerStatutForm = type('DynamicChangerStatutForm', (ChangerStatutForm,), new_fields)
    if request.method == "POST":
        form = DynamicChangerStatutForm(request.POST)
        if form.is_valid():
            selected_candidat = []
            for field in form.cleaned_data:
                if "bool" in field and form.cleaned_data[field]:
                    selected_candidat.append(int(field[4:6]))
            if len(selected_candidat) > 0:
                for candidat in selected_candidat:
                    candidat_a_changer = Candidat.objects.filter(id=candidat).first()
                    candidat_a_changer.statut = form.cleaned_data.get('statuts')
                    if form.cleaned_data.get('statuts') == "En jeu":
                        candidat_a_changer.statut_bool = True
                        candidat_a_changer.chemin_img = "dkllapp/img/contestants/" + "in/" + "{:02d}".format(candidat) + ".png"

                    else:
                        candidat_a_changer.statut_bool = False
                        candidat_a_changer.chemin_img = "dkllapp/img/contestants/" + "out/" + "{:02d}".format(candidat) + ".png"
                    candidat_a_changer.save()
                return redirect('dkllapp:admin')
            else:
                return redirect('dkllapp:changer_statut')
    form = DynamicChangerStatutForm()
    print('form', form)
    print('candidats', candidats)
    return render(request=request,
                  template_name="dkllapp/changer_statut.html",
                  context={'ligues': ligues, 'episode_en_cours_': episode_en_cours_,
                           'form': form, 'candidats': candidats,
                           'isadmin': is_admin(request.user.id)})


@login_required
def ajouter_question(request, question_id):
    ligues = Membre.objects \
        .filter(user_id=request.user.id).order_by('insert_datetime') \
        .values('id', 'ligue_id', 'ligue__nom')
    episode_en_cours_ = episode_en_cours()
    question = Question.objects.filter(id=question_id).first()
    propositions = Proposition.objects.filter(question_id=question_id).all()
    if request.method == "POST":
        form = AjouterQuestionForm(request.POST)
        if form.is_valid():
            if question_id == '0':
                question = Question()
            question.enonce = form.cleaned_data.get('enonce')
            question.episode = form.cleaned_data.get('episode')
            question.bonus = form.cleaned_data.get('bonus')
            question.malus = form.cleaned_data.get('malus')
            question.save()
            propositions_avant = form.cleaned_data.get('propositions')
            propositions_decoupees = []
            current_proposition = ""
            for car in propositions_avant:
                if car == ";":
                    propositions_decoupees = propositions_decoupees + [current_proposition]
                    current_proposition = ""
                else:
                    current_proposition = current_proposition + car
            propositions_decoupees.append(current_proposition)
            for proposition_decoupee in propositions_decoupees:
                if Proposition.objects.filter(question_id=question_id).filter(texte=proposition_decoupee).first():
                    pass
                elif proposition_decoupee == "":
                    pass
                else:
                    nouvelle_proposition = Proposition()
                    nouvelle_proposition.question_id = question.id
                    nouvelle_proposition.texte = proposition_decoupee
                    nouvelle_proposition.save()
            return redirect('dkllapp:admin')
    form = AjouterQuestionForm()
    return render(request=request,
                  template_name="dkllapp/ajouter_question.html",
                  context={'ligues': ligues, 'episode_en_cours_': episode_en_cours_, 'form': form,
                           'question': question, 'propositions': propositions,
                           'isadmin': is_admin(request.user.id)})


@login_required
def ajouter_reponse(request, question_id):
    ligues = Membre.objects \
        .filter(user_id=request.user.id).order_by('insert_datetime') \
        .values('id', 'ligue_id', 'ligue__nom')
    episode_en_cours_ = episode_en_cours()
    propositions = Proposition.objects.filter(question_id=question_id).all()
    if request.method == "POST":
        for proposition in propositions:
            if str(proposition.id) in request.POST:
                proposition.pertinence = True
                proposition.save()
            else:
                proposition.pertinence = False
                proposition.save()
        return redirect('dkllapp:admin')
    return render(request=request,
                  template_name="dkllapp/ajouter_reponse.html",
                  context={'ligues': ligues, 'episode_en_cours_': episode_en_cours_,
                           'propositions': propositions,
                           'isadmin': is_admin(request.user.id)})


@login_required
def modifier_regle(request, regle_id):
    ligues = Membre.objects\
        .filter(user_id=request.user.id).order_by('insert_datetime')\
        .values('id', 'ligue_id', 'ligue__nom')
    episode_en_cours_ = episode_en_cours()
    regle_a_modifier = Regle.objects.filter(id=regle_id).first()
    if request.method == "POST":
        form = CreerRegleForm(request.POST)
        if form.is_valid():
            if regle_id == '0':
                nouvelle_regle = Regle()
                nouvelle_regle.contenu = form.cleaned_data.get('contenu')
                nouvelle_regle.points_1 = form.cleaned_data.get('points_1')
                nouvelle_regle.points_2 = form.cleaned_data.get('points_2')
                nouvelle_regle.points_3 = form.cleaned_data.get('points_3')
                nouvelle_regle.save()
            elif regle_a_modifier:
                regle_a_modifier.contenu = form.cleaned_data.get('contenu')
                regle_a_modifier.points_1 = form.cleaned_data.get('points_1')
                regle_a_modifier.points_2 = form.cleaned_data.get('points_2')
                regle_a_modifier.points_3 = form.cleaned_data.get('points_3')
                regle_a_modifier.save()
            else:
                pass
            return redirect('dkllapp:admin')
    form = CreerRegleForm()
    return render(request=request,
                  template_name="dkllapp/modifier_regle.html",
                  context={'ligues': ligues, 'episode_en_cours_': episode_en_cours_, 'form': form,
                           'regle_a_modifier': regle_a_modifier,
                           'isadmin': is_admin(request.user.id)})


@login_required
def ajouter_evenement(request):
    ligues = Membre.objects\
        .filter(user_id=request.user.id).order_by('insert_datetime')\
        .values('id', 'ligue_id', 'ligue__nom')
    episode_en_cours_ = episode_en_cours()
    candidats = Candidat.objects.all().order_by('id')\
        .values('id', 'nom', 'equipe_tv', 'chemin_img', 'statut', 'statut_bool', 'form_id')
    regles = Regle.objects.all().order_by('insert_datetime').values('id', 'contenu')
    choices = [(regle['id'], regle['contenu']) for regle in regles]
    print('regles', choices)
    new_fields = {}
    for candidat in candidats:
        new_fields[candidat['form_id']] = forms.BooleanField(required=False)
    new_fields['regle'] = forms.ChoiceField(choices=choices, required=True, widget=forms.Select(attrs={'class': "form_select"}))
    print("new_fields['regle']", new_fields['regle'])
    DynamicAjouterEvenementForm = type('DynamicAjouterEvenementForm', (AjouterEvenementForm,), new_fields)
    if request.method == "POST":
        form = DynamicAjouterEvenementForm(request.POST)
        if form.is_valid():
            selected_candidat = []
            for field in form.cleaned_data:
                if "bool" in field and form.cleaned_data[field]:
                    selected_candidat.append(int(field[4:6]))
            if 0 < len(selected_candidat):
                for candidat_id in selected_candidat:
                    nouvel_evenenement = Evenement()
                    nouvel_evenenement.episode = form.cleaned_data.get('episode')
                    nouvel_evenenement.typage = form.cleaned_data.get('typage')
                    nouvel_evenenement.user_id = request.user.id
                    nouvel_evenenement.candidat_id = candidat_id
                    nouvel_evenenement.regle_id = form.cleaned_data.get('regle')
                    nouvel_evenenement.save()
            return redirect('dkllapp:admin')
    form = DynamicAjouterEvenementForm()
    return render(request=request,
                  template_name="dkllapp/ajouter_evenement.html",
                  context={'ligues': ligues, 'episode_en_cours_': episode_en_cours_,
                           'form': form, 'candidats': candidats,
                           'isadmin': is_admin(request.user.id)})


##########################################Ligues################################
@login_required
def mur(request, ligue_id):
    ligues = Membre.objects\
        .filter(user_id=request.user.id).order_by('insert_datetime')\
        .values('id', 'ligue_id', 'ligue__nom')
    current_ligue = Ligue.objects.filter(id=ligue_id).values('id', 'nom')[0]
    current_user = UserProfile.objects.filter(id=request.user.id).values('user__username', 'img')[0]
    mur = Mur.objects\
        .filter(ligue_id=ligue_id).order_by('-last_modified')\
        .values('id', 'ligue_id', 'user_id', 'parent_id',
                'user__user__username', 'user__img', 'message', 'insert_datetime', 'last_modified')
    new_fields = {}
    for message in mur:
        if message['parent_id']:
            pass
        else:
            field_name = 'area' + str(message['id'])
            field_label = 'label' + str(message['id'])
            new_fields[field_name] = forms.CharField(label=field_label, max_length=999, required=False)
    DynamicMessageMurForm = type('DynamicMessageMurForm', (MessageMurForm,), new_fields)
    if request.method == "POST":
        form = DynamicMessageMurForm(request.POST)
        print(request.POST)
        for field in request.POST:
            print(field, request.POST[field])
            if field == 'csrfmiddlewaretoken':
                pass
            elif request.POST[field]:
                if field == 'nouveau_parent':
                    print('field nouveau parent')
                    nouveau_message = Mur()
                    nouveau_message.user_id = request.user.id
                    nouveau_message.ligue_id = ligue_id
                    nouveau_message.message = request.POST[field]
                    print('nouveau_message', nouveau_message)
                    nouveau_message.save()
                elif 'area' in field:
                    print('field[4:]', field[4:])
                    nouveau_message = Mur()
                    nouveau_message.user_id = request.user.id
                    nouveau_message.ligue_id = ligue_id
                    nouveau_message.message = request.POST[field]
                    nouveau_message.parent_id = field[4:]
                    nouveau_message.save()
                    parent_modifier = Mur.objects.filter(id=field[4:]).first()
                    parent_modifier.last_modified = now()
                    parent_modifier.save()
        return redirect('dkllapp:mur', ligue_id)
    form = DynamicMessageMurForm()
    notif = Notif.objects.latest('insert_datetime')
    return render(request=request,
                  template_name="dkllapp/mur.html",
                  context={'ligues': ligues, 'page': 'mur', 'current_ligue': current_ligue, 'mur': mur, 'notif': notif,
                           'current_user': current_user, 'form': form,
                           'isadmin': is_admin(request.user.id)})


@login_required
def equipe(request, ligue_id):
    ligues = Membre.objects\
        .filter(user_id=request.user.id).order_by('insert_datetime')\
        .values('id', 'ligue_id', 'ligue__nom')
    current_ligue = Ligue.objects.filter(id=ligue_id).values('id', 'nom')[0]
    episode_en_cours_ = episode_en_cours()
    equipe = Equipe.objects \
        .filter(user_id=request.user.id) \
        .filter(ligue_id=current_ligue['id']) \
        .filter(episode=episode_en_cours_) \
        .filter(type=1) \
        .order_by('candidat_id') \
        .values('id', 'candidat_id', 'candidat__nom', 'candidat__equipe_tv', 'candidat__chemin_img',
                'candidat__statut', 'candidat__statut_bool', 'type')
    return render(request=request,
                  template_name="dkllapp/equipe.html",
                  context={'ligues': ligues, 'page': 'equipe',
                           'equipe': equipe,
                           'ligue_id': ligue_id, 'before_creation': 'equipe',
                           'episode_en_cours_': episode_en_cours_, 'current_ligue': current_ligue,
                           'isadmin': is_admin(request.user.id)})


@login_required
def resultat(request, ligue_id):
    ligues = Membre.objects\
        .filter(user_id=request.user.id).order_by('insert_datetime')\
        .values('id', 'ligue_id', 'ligue__nom')
    current_ligue = Ligue.objects.filter(id=ligue_id).values('id', 'nom')[0]
    membres = points_ligue_episode(ligue_id, 0)
    return render(request=request,
                  template_name="dkllapp/resultat.html",
                  context={'ligues': ligues, 'page': 'resultat', 'ligue_id': ligue_id, 'current_ligue': current_ligue,
                           'membres': membres,
                           'isadmin': is_admin(request.user.id)})


@login_required
def details(request, ligue_id, selected_episode):
    ligues = Membre.objects\
        .filter(user_id=request.user.id).order_by('insert_datetime')\
        .values('id', 'ligue_id', 'ligue__nom')
    current_ligue = Ligue.objects.filter(id=ligue_id).values('id', 'nom')[0]
    episode_en_cours_ = episode_en_cours()
    membres = Membre.objects.filter(ligue_id=current_ligue['id']).order_by('insert_datetime')\
        .values('id', 'user_id', 'user__user__username', 'user__img')
    choix = Choix.objects.all().order_by('id')\
        .values('id', 'user_id', 'candidat__chemin_img', 'type')
    membres_points = points_ligue_episode(ligue_id, selected_episode)
    return render(request=request,
                  template_name="dkllapp/details.html",
                  context={'ligues': ligues, 'page': 'details',
                           'ligue_id': ligue_id, 'episode_en_cours_': episode_en_cours_,
                           'current_ligue': current_ligue, 'membres': membres,  'choix': choix,
                           'membres_points': membres_points,
                           'isadmin': is_admin(request.user.id)})


@login_required
def changer_nom_ligue(request, ligue_id):
    ligues = Membre.objects\
        .filter(user_id=request.user.id).order_by('insert_datetime')\
        .values('id', 'ligue_id', 'ligue__nom')
    if request.method == "POST":
        form = LigueCreationForm(request.POST)
        if form.is_valid():
            current_ligue = Ligue.objects.filter(id=ligue_id).first()
            current_ligue.nom = form.cleaned_data.get('nom')
            current_ligue.save()
            return redirect('dkllapp:details', current_ligue.id)
    form = LigueCreationForm()
    return render(request=request,
                  template_name="dkllapp/changer_nom_ligue.html",
                  context={'form': form, 'ligues': ligues,
                           'isadmin': is_admin(request.user.id)})


##########################################Pronos################################
@login_required
def pronos(request):
    ligues = Membre.objects\
        .filter(user_id=request.user.id).order_by('insert_datetime')\
        .values('id', 'ligue_id', 'ligue__nom')
    episode_en_cours_ = episode_en_cours()
    questions = Question.objects.filter(episode=episode_en_cours_).order_by('-insert_datetime')
    questions_plus = []
    for question in questions:
        propositions = Proposition.objects.filter(question_id=question.id)
        guess = Guess.objects.filter(question_id=question.id).filter(user_id=request.user.id).first()
        questions_plus.append({'question': question, 'guess': guess, 'propositions': propositions})
    return render(request=request,
                  template_name="dkllapp/pronos.html",
                  context={'ligues': ligues, 'page': 'pronos', 'questions_plus': questions_plus,
                           'isadmin': is_admin(request.user.id)})


@login_required
def pronos_cgi(request, question_id, proposition_id):
    current_user_guess = Guess.objects.filter(question_id=question_id).filter(user_id=request.user.id).first()
    if current_user_guess:
        Guess.objects.filter(question_id=question_id).filter(user_id=request.user.id).delete()
        if proposition_id == str(current_user_guess.proposition_id):
            pass
        else:
            nouveau_guess = Guess()
            nouveau_guess.user_id = request.user.id
            nouveau_guess.question_id = question_id
            nouveau_guess.proposition_id = proposition_id
            nouveau_guess.save()
    else:
        nouveau_guess = Guess()
        nouveau_guess.user_id = request.user.id
        nouveau_guess.question_id = question_id
        nouveau_guess.proposition_id = proposition_id
        nouveau_guess.save()
    return redirect('dkllapp:pronos')


@login_required
def bonus(request):
    ligues = Membre.objects\
        .filter(user_id=request.user.id).order_by('insert_datetime')\
        .values('id', 'ligue_id', 'ligue__nom')
    questions = Question.objects.order_by('-episode').order_by('-insert_datetime')
    questions_plus = []
    for question in questions:
        propositions = Proposition.objects.filter(question_id=question.id)
        repondu = False
        for proposition in propositions:
            if proposition.pertinence:
                repondu = True
        guess = Guess.objects.filter(question_id=question.id).filter(user_id=request.user.id)\
            .values('id', 'user_id', 'question_id', 'proposition_id', 'proposition__pertinence').first()
        questions_plus.append({'question': question, 'guess': guess,
                               'propositions': propositions, 'repondu': repondu})
    points_feu = PointsFeu.objects.filter(user_id=request.user.id).values('user_id', 'feu').order_by('user_id').first()
    print(points_feu)
    return render(request=request,
                  template_name="dkllapp/bonus.html",
                  context={'ligues': ligues, 'page': 'bonus',
                           'questions_plus': questions_plus, 'points_feu': points_feu,
                           'isadmin': is_admin(request.user.id)})


##########################################Profil################################
@login_required
def profil(request):
    ligues = Membre.objects\
        .filter(user_id=request.user.id).order_by('insert_datetime')\
        .values('id', 'ligue_id', 'ligue__nom')
    candidats = Candidat.objects.all().order_by('id')
    choix_user = Choix.objects\
        .filter(user_id=request.user.id).order_by('candidat_id')\
        .values('id', 'type', 'candidat_id', 'candidat__nom', 'candidat__equipe_tv', 'candidat__chemin_img', 'candidat__statut', 'candidat__statut_bool')
    return render(request=request,
                  template_name="dkllapp/profil.html",
                  context={'candidats': candidats, 'ligues': ligues,
                           'choix_user': choix_user, 'before_creation': 'profil',
                           'isadmin': is_admin(request.user.id)})


@login_required
def choix(request, type_choix, before, txt):
    ligues = Membre.objects\
        .filter(user_id=request.user.id).order_by('insert_datetime')\
        .values('id', 'ligue_id', 'ligue__nom')
    episode_en_cours_ = episode_en_cours()
    txt_alert = txt
    candidats = Candidat.objects.all().order_by('id')\
        .values('id', 'nom', 'equipe_tv', 'chemin_img', 'statut', 'statut_bool', 'form_id')
    new_fields = {}
    for candidat in candidats:
        new_fields[candidat['form_id']] = forms.BooleanField(required=False)
    DynamicChoixCreationForm = type('DynamicChoixCreationForm', (ChoixCreationForm,), new_fields)
    if request.method == "POST":
        form = DynamicChoixCreationForm(request.POST)
        if form.is_valid():
            selected_candidat = []
            for field in form.cleaned_data:
                if "bool" in field and form.cleaned_data[field]:
                    selected_candidat.append(int(field[4:6]))
            if len(selected_candidat) == nbr_par_type(type_choix):
                choix_pour_un_type(request.user, type_choix, selected_candidat)
                if before == "profil":
                    return redirect('dkllapp:profil')
                else:
                    return redirect('dkllapp:index')
            else:
                txt_alert = "alert"
                return redirect('dkllapp:choix', type_choix, before, txt_alert)
    form = DynamicChoixCreationForm()
    return render(request=request,
                  template_name="dkllapp/choix.html",
                  context={'form': form, 'ligues': ligues, 'candidats': candidats, 'txt_alert': txt, 'type_choix': type_choix,
                           'isadmin': is_admin(request.user.id)})


##########################################Règles################################
@login_required
def generales(request):
    ligues = Membre.objects\
        .filter(user_id=request.user.id).order_by('insert_datetime')\
        .values('id', 'ligue_id', 'ligue__nom')
    return render(request=request,
                  template_name="dkllapp/generales.html",
                  context={'ligues': ligues, 'page': 'generales',
                           'isadmin': is_admin(request.user.id)})


@login_required
def bareme(request):
    ligues = Membre.objects\
        .filter(user_id=request.user.id).order_by('insert_datetime')\
        .values('id', 'ligue_id', 'ligue__nom')
    regles = Regle.objects.all().order_by('id')
    return render(request=request,
                  template_name="dkllapp/bareme.html",
                  context={'ligues': ligues, 'page': 'bareme', 'regles': regles,
                           'isadmin': is_admin(request.user.id)})


@login_required
def candidats(request):
    ligues = Membre.objects\
        .filter(user_id=request.user.id).order_by('insert_datetime')\
        .values('id', 'ligue_id', 'ligue__nom')
    candidats = Candidat.objects.all().order_by('id')
    return render(request=request,
                  template_name="dkllapp/candidats.html",
                  context={'ligues': ligues, 'page': 'candidats', 'candidats': candidats,
                           'isadmin': is_admin(request.user.id)})


@login_required
def faq(request):
    ligues = Membre.objects\
        .filter(user_id=request.user.id).order_by('insert_datetime')\
        .values('id', 'ligue_id', 'ligue__nom')
    return render(request=request,
                  template_name="dkllapp/faq.html",
                  context={'ligues': ligues, 'page': 'faq',
                           'isadmin': is_admin(request.user.id)})


@login_required
def classement_general(request):
    ligues = Membre.objects \
        .filter(user_id=request.user.id).order_by('insert_datetime') \
        .values('id', 'ligue_id', 'ligue__nom')
    users = User.objects.all().order_by('id')
    users_a_classer = []
    for user in users:
        max_points_user = 0
        ligue_max_points_user = ""
        ligues_user = Membre.objects.filter(user_id=user.id)\
            .values('ligue_id')
        print('user.id', user.id, 'ligues_user', ligues_user)
        if ligues_user:
            for ligue in ligues_user:
                points = Points.objects.filter(user_id=user.id).filter(ligue_id=ligue['ligue_id']) \
                    .values('ligue_id') \
                    .annotate(Sum('somme_points_selon_types'))
                if points:
                    if points[0]['somme_points_selon_types__sum'] > max_points_user:
                        max_points_user = points[0]['somme_points_selon_types__sum']
                        ligue_max_points_user = ligue['ligue_id']
                else:
                    pass
            if max_points_user == 0:
                pass
            else:
                users_a_classer.append([user.id, ligue_max_points_user, max_points_user])
        else:
            pass
    print(users_a_classer)
    membres_unsorted = []
    for user_membre in users_a_classer:
        membre_points = Points.objects.filter(user_id=user_membre[0]).filter(ligue_id=user_membre[1]) \
            .values('ligue_id', 'user_id') \
            .annotate(Sum('somme_points_poulains')) \
            .annotate(Sum('somme_points_podium')) \
            .annotate(Sum('somme_points_gagnant')) \
            .annotate(Sum('somme_points_selon_types'))

        membre_avec_points = {
            'id': user_membre[0],
            'ligue' : Ligue.objects.filter(id=user_membre[1]).values('nom')[0]['nom'],
            'username': User.objects.filter(id=user_membre[0]).values('username')[0]['username'],
            'img': UserProfile.objects.filter(id=user_membre[0]).values('img')[0]['img'],
            'points_poulains': membre_points[0]['somme_points_poulains__sum'],
            'points_podium': membre_points[0]['somme_points_podium__sum'],
            'points_gagnant': membre_points[0]['somme_points_gagnant__sum'],
            'points_candidats': membre_points[0]['somme_points_selon_types__sum']
        }
        membres_unsorted.append(membre_avec_points)

    membres_sorted = sorted(membres_unsorted, key=lambda i: i['points_candidats'], reverse=True)
    rang = 1
    for joueur in membres_sorted:
        joueur['rang'] = rang
        rang = rang + 1
    return render(request=request,
                  template_name="dkllapp/classement_general.html",
                  context={'ligues': ligues, 'page': 'classement_general', 'membres_sorted': membres_sorted,
                           'isadmin': is_admin(request.user.id)})


@login_required
def statistiques(request):
    statistiques = 'statistiques'
    return render(request=request,
                  template_name="dkllapp/statistiques.html",
                  context={'statistiques': statistiques,
                           'isadmin': is_admin(request.user.id)})


@login_required
def nouveau_login(request):
    nouveau_login = 'nouveau_login'
    return render(request=request,
                  template_name="dkllapp/nouveau_login.html",
                  context={'nouveau_login': nouveau_login,
                           'isadmin': is_admin(request.user.id)})


@login_required
def nouveau_mdp(request):
    nouveau_mdp = 'nouveau_mdp'
    return render(request=request,
                  template_name="dkllapp/nouveau_mdp.html",
                  context={'nouveau_mdp': nouveau_mdp,
                           'isadmin': is_admin(request.user.id)})


@login_required
def picto(request):
    picto = 'picto'
    return render(request=request,
                  template_name="dkllapp/index.html",
                  context={'picto': picto,
                           'isadmin': is_admin(request.user.id)})


@login_required
def creation_ligue(request):
    ligues = Membre.objects\
        .filter(user_id=request.user.id).order_by('insert_datetime')\
        .values('id', 'ligue_id', 'ligue__nom')
    if request.method == "POST":
        form = LigueCreationForm(request.POST)
        if form.is_valid():
            nouvelle_ligue = Ligue()
            nouvelle_ligue.nom = form.cleaned_data.get('nom')
            nouvelle_ligue.save()
            nouveau_membre = Membre()
            nouveau_membre.user_id = request.user.id
            nouveau_membre.ligue_id = nouvelle_ligue.id
            nouveau_membre.save()
            #mail ou web push à prévoir
            return redirect('dkllapp:mur', nouvelle_ligue.id)
    form = LigueCreationForm()
    return render(request=request,
                  template_name="dkllapp/creation_ligue.html",
                  context={'form': form, 'ligues': ligues,
                           'isadmin': is_admin(request.user.id)})


@login_required
def rejoindre_ligue(request):
    ligues = Membre.objects\
        .filter(user_id=request.user.id).order_by('insert_datetime')\
        .values('id', 'ligue_id', 'ligue__nom')
    if request.method == "POST":
        form = LigueJoinForm(request.POST)
        if form.is_valid():
            print('début if')
            ligue_a_rejoindre = Ligue.objects.filter(id=form.cleaned_data.get('ligue_id')).first()
            print('ligue_a_rejoindre', ligue_a_rejoindre)
            if ligue_a_rejoindre:
                deja_membre = Membre.objects \
                    .filter(user_id=request.user.id) \
                    .filter(id=ligue_a_rejoindre.id)
                if deja_membre:
                    pass
                else:
                    nouveau_membre = Membre()
                    nouveau_membre.user_id = request.user.id
                    nouveau_membre.ligue_id = ligue_a_rejoindre.id
                    nouveau_membre.save()
                    print('nouveau_membre', nouveau_membre)
                    #mail ou web push à prévoir
                    print('avant redirect')
                    return redirect('dkllapp:mur', ligue_a_rejoindre.id)
    form = LigueJoinForm()
    return render(request=request,
                  template_name="dkllapp/rejoindre_ligue.html",
                  context={'rejoindre_ligue': rejoindre_ligue, 'ligues': ligues, 'form': form,
                           'isadmin': is_admin(request.user.id)})


@login_required
def faire_equipe(request, ligue_id, before, txt):
    ligues = Membre.objects\
        .filter(user_id=request.user.id).order_by('insert_datetime')\
        .values('id', 'ligue_id', 'ligue__nom')
    current_ligue = Ligue.objects.filter(id=ligue_id).values('id', 'nom')[0]
    episode_en_cours_ = episode_en_cours()
    txt_alert = txt
    poulains = Choix.objects.filter(user_id=request.user.id).filter(type=1).order_by('id')\
        .values('id', 'candidat__id', 'candidat__nom', 'candidat__equipe_tv', 'candidat__chemin_img',
                'candidat__statut', 'candidat__statut_bool', 'candidat__form_id')
    new_fields = {}
    for poulain in poulains:
        new_fields[poulain['candidat__form_id']] = forms.BooleanField(required=False)
    DynamicEquipeCreationForm = type('DynamicEquipeCreationForm', (EquipeCreationForm,), new_fields)
    if request.method == "POST":
        form = DynamicEquipeCreationForm(request.POST)
        if form.is_valid():
            selected_candidat = []
            for field in form.cleaned_data:
                if "bool" in field and form.cleaned_data[field]:
                    selected_candidat.append(int(field[4:6]))
            if 0 < len(selected_candidat) < 4:
                if form.cleaned_data['propagation'] is False:
                    equipe_pour_une_ligue(request.user, ligue_id, episode_en_cours_, selected_candidat)
                else:
                    for ligue in ligues:
                        print('ligue', ligue)
                        equipe_pour_une_ligue(request.user, ligue['ligue_id'], episode_en_cours_, selected_candidat)
                if before == "equipe":
                    return redirect('dkllapp:equipe', current_ligue['id'])
                else:
                    return redirect('dkllapp:index')
            else:
                txt_alert = "alert"
                print('else', current_ligue['id'], before, txt_alert)
                return redirect('dkllapp:faire_equipe', current_ligue['id'], before, txt_alert)

    form = DynamicEquipeCreationForm()
    return render(request=request,
                  template_name="dkllapp/faire_equipe.html",
                  context={'form': form, 'ligues': ligues, 'poulains': poulains, 'txt_alert': txt_alert,
                           'isadmin': is_admin(request.user.id)})


######################################TESTS#################################################
############################################################################################
############################################################################################
def home_mail(request):
    user = request.user

    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = MailForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            current_site = get_current_site(request)
            context = {
                'user': user,
                'domain': 'domain',
                'uidb64': 'uidb64',
                'token': 'token',
                'message': form.cleaned_data['corps']}
            subject = form.cleaned_data['sujet']
            message = render_to_string('dkllapp/account_activation_email.html', context)
            email_from = settings.EMAIL_HOST_USER
            recipient_list = ['louise2004gautier@gmail.com']
            print("email_from", email_from, "recipient_list", recipient_list)
            send_mail(subject, message, email_from, recipient_list)
            return HttpResponseRedirect('/home_push/')

    # if a GET (or any other method) we'll create a blank form
    else:
        form = MailForm()

    return render(request, 'dkllapp/home_mail.html', {user: user})


#######Test web push notifications #####

@require_GET
def home_push(request):
    webpush_settings = getattr(settings, 'WEBPUSH_SETTINGS', {})
    vapid_key = webpush_settings.get('VAPID_PUBLIC_KEY')
    user = request.user
    return render(request, 'dkllapp/home.html', {user: user, 'vapid_key': vapid_key})


@require_POST
@csrf_exempt
def send_push(request):
    try:
        body = request.body
        data = json.loads(body)

        if 'head' not in data or 'body' not in data or 'id' not in data:
            return JsonResponse(status=400, data={"message": "Invalid data format"})

        user_id = data['id']
        payload = {'head': data['head'], 'body': data['body']}
        users = User.objects.all()
        for user_dkllapp in users:
            print("user_dkllapp.id", user_dkllapp.id)
            user_push = get_object_or_404(User, pk=user_dkllapp.id)
            send_user_notification(user=user_push, payload=payload, ttl=1000)

        return JsonResponse(status=200, data={"message": "Web push successful"})
    except TypeError:
        return JsonResponse(status=500, data={"message": "An error occurred"})
