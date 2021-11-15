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

from .forms import NewUserForm, MailForm
from .models import Candidat, Ligue, Mur, Notif
from .token import account_activation_token


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


########################Test mail


##########################################Home################################


class IndexView(LoginRequiredMixin, generic.ListView):
    login_url = '/login/'
    template_name = 'dkllapp/index.html'
    context_object_name = 'latest_question_list'

    def get_queryset(self):
        """Return the last five published questions."""
        return Question.objects.order_by('-pub_date')[:5]


##########################################admin################################
@login_required
def admin(request):
    admin = 'admin'
    return render(request=request,
                  template_name="dkllapp/index.html",
                  context={'admin': admin})

##########################################ligues################################
@login_required
def ligues(request):
    ligues = Ligue.objects.all
    return render(request=request,
                  template_name="dkllapp/index.html",
                  context={'ligues': ligues})


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
def classement(request, ligue_id):
    ligues = Ligue.objects.all()
    return render(request=request,
                  template_name="dkllapp/classement.html",
                  context={'ligues': ligues, 'page': 'classement',
                           'ligue_id': ligue_id})


@login_required
def details(request, ligue_id):
    ligues = Ligue.objects.all()
    return render(request=request,
                  template_name="dkllapp/details.html",
                  context={'ligues': ligues, 'page': 'details',
                           'ligue_id': ligue_id})


##########################################générales################################

@login_required
def generales(request):
    ligues = Ligue.objects.all()
    return render(request=request,
                  template_name="dkllapp/generales.html",
                  context={'ligues': ligues})


@login_required
def regles(request):
    regles = 'generales'
    return render(request=request,
                  template_name="dkllapp/regles.html",
                  context={'regles': regles})


@login_required
def candidats(request):
    candidats = Candidat.objects.all
    return render(request=request,
                  template_name="dkllapp/candidats.html",
                  context={'candidats': candidats})

##########################################La commu################################


@login_required
def suggestions(request):
    suggestions = 'suggestions'
    return render(request=request,
                  template_name="dkllapp/index.html",
                  context={'suggestions': suggestions})


@login_required
def pronos(request):
    pronos = 'pronos'
    return render(request=request,
                  template_name="dkllapp/index.html",
                  context={'pronos': pronos})


@login_required
def profil(request):
    candidats = Candidat.objects.all
    ligues = Ligue.objects.all
    return render(request=request,
                  template_name="dkllapp/profil.html",
                  context={'candidats': candidats, 'ligues': ligues})


@login_required
def bareme(request):
    return render(request=request,
                  template_name="dkllapp/bareme.html",
                  context={})

@login_required
def faq(request):
    return render(request=request,
                  template_name="dkllapp/faq.html",
                  context={})


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
def creation_ligue(request):
    creation_ligue = 'creation_ligue'
    return render(request=request,
                  template_name="dkllapp/index.html",
                  context={'creation_ligue': creation_ligue})


@login_required
def rejoindre_ligue(request):
    rejoindre_ligue = 'rejoindre_ligue'
    return render(request=request,
                  template_name="dkllapp/index.html",
                  context={'rejoindre_ligue': rejoindre_ligue})


