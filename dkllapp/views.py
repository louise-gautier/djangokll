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
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseRedirect
from django.template.loader import render_to_string

from django.utils.encoding import force_bytes, force_text
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.conf import settings
from django.urls import reverse
from django.views import generic

from django.http.response import JsonResponse, HttpResponse
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
from webpush import send_user_notification
import json

from .forms import NewUserForm, MailForm, LigueCreationForm
from .models import Candidat, Ligue, Mur, Notif, Choix, Episode, ActivationChoix, Membre
from .token import account_activation_token


#v############################### FONCTIONS GENERIQUES #########################################
def is_admin(user_id):
    admins = [1, 5, 8, 9]
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


##########################################REGISTRATION ET LOGIN################################
def register_request(request):
    if request.method == "POST":
        form = NewUserForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.refresh_from_db()  # load the profile instance created by the signal
            user.userprofile.img = 'dkllapp/img/kitchen/default.png'
            user.userprofile.boolemail = True
            user.save()
            current_site = get_current_site(request)
            context = {
                'user': user,
                'domain': current_site.domain,
                'uidb64': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': account_activation_token.make_token(user), }

            #mail
            subject = "Activation de ton email KLL"
            message = render_to_string('dkllapp/account_activation_email.html', context)
            email_from = settings.EMAIL_HOST_USER
            recipient_list = [user.email]
            print("email_from", email_from, "recipient_list", recipient_list)
            send_mail(subject, message, email_from, recipient_list)

            return redirect('dkllapp:account_activation_sent')

        messages.error(request, "Unsuccessful registration. Invalid information.")
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
                    messages.info(request, f"You are now logged in as {username}.")
                    return redirect("dkllapp:index")
                else:
                    messages.error(request, "Unconfirmed email.")
            else:
                messages.error(request, "Invalid username or password.")
        else:
            messages.error(request, "Invalid username or password.")
    form = AuthenticationForm()
    return render(request=request, template_name="dkllapp/login.html", context={"login_form": form})


@login_required
def logout_request(request):
    logout(request)
    messages.info(request, "You have successfully logged out.")
    return redirect("dkllapp:index")


##########################################FIN REGISTRATION ET LOGIN################################
######################################HOME - INDEX################################
@login_required
def index(request):
    ligues = Ligue.objects.all()
    notif = Notif.objects.latest('insert_datetime')
    choix_user = Choix.objects \
        .filter(user_id=request.user.id) \
        .values('id', 'type', 'candidat_id', 'candidat__nom', 'candidat__equipe_tv', 'candidat__chemin_img',
                'candidat__statut', 'candidat__statut_bool')

    return render(request=request,
                  template_name="dkllapp/index.html",
                  context={'ligues': ligues, 'notif': notif, 'choix_user': choix_user,
                           'before_creation': 'index'})


##########################################Admin################################
@login_required
def admin(request):
    admin = 'admin'
    return render(request=request,
                  template_name="dkllapp/index.html",
                  context={'admin': admin})


##########################################Ligues################################
@login_required
def mur(request, ligue_id):
    ligues = Ligue.objects.all()
    mur = Mur.objects\
        .filter(ligue_id=ligue_id)\
        .values('id', 'ligue_id', 'user_id', 'user__user__username', 'user__img', 'message', 'insert_datetime')
    print('mur', mur)
    notif = Notif.objects.latest('insert_datetime')
    return render(request=request,
                  template_name="dkllapp/mur.html",
                  context={'ligues': ligues, 'page': 'mur',
                           'ligue_id': ligue_id, 'mur': mur, 'notif': notif})


@login_required
def equipe(request, ligue_id):
    ligues = Ligue.objects.all()
    return render(request=request,
                  template_name="dkllapp/equipe.html",
                  context={'ligues': ligues, 'page': 'equipe',
                           'ligue_id': ligue_id})


@login_required
def resultat(request, ligue_id):
    ligues = Ligue.objects.all()
    return render(request=request,
                  template_name="dkllapp/resultat.html",
                  context={'ligues': ligues, 'page': 'resultat',
                           'ligue_id': ligue_id})


@login_required
def details(request, ligue_id):
    ligues = Ligue.objects.all()
    return render(request=request,
                  template_name="dkllapp/details.html",
                  context={'ligues': ligues, 'page': 'details',
                           'ligue_id': ligue_id})


##########################################Profil################################
@login_required
def profil(request):
    ligues = Ligue.objects.all()
    print(request.user.id)
    candidats = Candidat.objects.all()
    choix_user = Choix.objects\
        .filter(user_id=request.user.id)\
        .values('id', 'type', 'candidat_id', 'candidat__nom', 'candidat__equipe_tv', 'candidat__chemin_img', 'candidat__statut', 'candidat__statut_bool')
    return render(request=request,
                  template_name="dkllapp/profil.html",
                  context={'candidats': candidats, 'ligues': ligues,
                           'choix_user': choix_user, 'before_creation': 'profil'})


@login_required
def choix(request):
    candidats = Candidat.objects.all()
    ligues = Ligue.objects.all()
    return render(request=request,
                  template_name="dkllapp/profil.html",
                  context={'candidats': candidats, 'ligues': ligues})


##########################################Règles################################
@login_required
def generales(request):
    ligues = Ligue.objects.all()
    return render(request=request,
                  template_name="dkllapp/generales.html",
                  context={'ligues': ligues})

@login_required
def bareme(request):
    return render(request=request,
                  template_name="dkllapp/bareme.html",
                  context={})


@login_required
def candidats(request):
    candidats = Candidat.objects.all()
    return render(request=request,
                  template_name="dkllapp/candidats.html",
                  context={'candidats': candidats})


@login_required
def faq(request):
    return render(request=request,
                  template_name="dkllapp/faq.html",
                  context={})


@login_required
def pronos(request):
    pronos = 'pronos'
    return render(request=request,
                  template_name="dkllapp/index.html",
                  context={'pronos': pronos})


@login_required
def nouveau_login(request):
    nouveau_login = 'nouveau_login'
    return render(request=request,
                  template_name="dkllapp/nouveau_login.html",
                  context={'nouveau_login': nouveau_login})


@login_required
def nouveau_mdp(request):
    nouveau_mdp = 'nouveau_mdp'
    return render(request=request,
                  template_name="dkllapp/nouveau_mdp.html",
                  context={'nouveau_mdp': nouveau_mdp})


@login_required
def picto(request):
    picto = 'picto'
    return render(request=request,
                  template_name="dkllapp/index.html",
                  context={'picto': picto})


@login_required
def creation_ligue(request, before):
    form = LigueCreationForm()
    if form.validate_on_submit():
        nouvelle_ligue = Ligue(nom=form.nom.data)
        nouvelle_ligue.save()
        nouveau_membre = Membre(user=request.user, ligue=nouvelle_ligue)
        #mail ou web push à prévoir
        if before == "profil":
            return redirect('dkllapp:profile')
        else:
            return redirect('dkllapp:index')
    return render(request=request,
                  template_name="dkllapp/creation_ligue.html",
                  context={'form': form})


@login_required
def rejoindre_ligue(request):
    rejoindre_ligue = 'rejoindre_ligue'
    return render(request=request,
                  template_name="dkllapp/index.html",
                  context={'rejoindre_ligue': rejoindre_ligue})


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
        user = get_object_or_404(User, pk=user_id)
        payload = {'head': data['head'], 'body': data['body']}
        send_user_notification(user=user, payload=payload, ttl=1000)

        return JsonResponse(status=200, data={"message": "Web push successful"})
    except TypeError:
        return JsonResponse(status=500, data={"message": "An error occurred"})

