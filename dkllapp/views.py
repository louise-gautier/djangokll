import random
import smtplib
from email.mime.text import MIMEText

from decouple import config
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth.models import User
from django.contrib.sites.shortcuts import get_current_site
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.mail import send_mail, EmailMultiAlternatives
from django.db import IntegrityError
from django.db.models import Sum, Q
from django.shortcuts import render, get_object_or_404, redirect
from django.template import loader
from django.template.loader import render_to_string

from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.conf import settings
from django.utils.timezone import now

from django.http.response import JsonResponse, HttpResponse
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
from django import forms

from webpush import send_user_notification
import json
import shortuuid

from .forms import NewUserForm, MailForm, LigueCreationForm, EquipeCreationForm, LigueJoinForm, ChoixCreationForm, \
    EpisodeChangeForm, ActivateChoiceForm, ChangerEquipeTVForm, ChangerStatutForm, MailAdminForm, NotifAdminForm, \
    ModifierRegleForm, CreerRegleForm, AjouterEvenementForm, MessageMurForm, PronoAdminForm, AjouterQuestionForm, \
    PictoForm, ProfilMailForm, ChangerIdentifiantForm, ReinitailiserMdpForm, PronosGuessForm
from .models import Candidat, Ligue, Mur, Notif, Choix, Episode, ActivationChoix, Membre, Equipe, Evenement, Points, \
    Regle, Blip, UserProfile, Question, Guess, Proposition, PointsFeu, EquipesFaites
from .token import account_activation_token


#v############################### FONCTIONS GENERIQUES #########################################
def is_admin(user_id):
    admins = [1, 2, 7, 9, 10]  # 18 = Laura, 19 = MA
    bool_admin = False
    if user_id in admins:
        bool_admin = True
    return bool_admin


def episode_en_cours():
    ep = Episode.objects.values('valeur').latest('insert_datetime')
    return ep['valeur']


def is_poulains():
    etat = ActivationChoix.objects.filter(id=2).values().latest('insert_datetime')['etat']
    if etat == 1:
        activation_poulains = True
    else:
        activation_poulains = False
    return activation_poulains


def is_podium():
    etat = ActivationChoix.objects.filter(id=3).values().latest('insert_datetime')['etat']
    if etat == 1:
        activation_podium = True
    else:
        activation_podium = False
    return activation_podium


def is_gagnant():
    etat = ActivationChoix.objects.filter(id=4).values().latest('insert_datetime')['etat']
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
    etat_a_changer = ActivationChoix.objects.filter(nom=type_choix).first()
    if type_activation == 'activate':
        etat_a_changer.etat = 1
    else:
        etat_a_changer.etat = 0
    etat_a_changer.save()


def points_ligue_episode(ligue_id, un_episode):
    membres = Membre.objects.filter(ligue_id=ligue_id).values('ligue_id', 'user_id', 'user__user__username', 'user__img')
    points_feu = PointsFeu.objects.values('user_id', 'feu').all()
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
        membre_avec_points = {'id': membre['user_id'], 'username': membre['user__user__username'], 'img': membre['user__img']}
        marqueur = 'lost'
        marqueur_feu = 'lost'
        for membre_points_feu in points_feu:
            if membre_points_feu['user_id'] == membre['user_id']:
                membre_avec_points['points_feu'] = membre_points_feu['feu']
                marqueur_feu = 'found'
        for membre_points in points:
            if membre_points['user_id'] == membre['user_id']:
                membre_avec_points['points_poulains'] = membre_points['somme_points_poulains__sum']
                membre_avec_points['points_podium'] = membre_points['somme_points_podium__sum']
                membre_avec_points['points_gagnant'] = membre_points['somme_points_gagnant__sum']
                membre_avec_points['points_candidats'] = membre_points['somme_points_selon_types__sum']
                marqueur = 'found'
            else:
                pass
        if marqueur == 'lost' and marqueur_feu == 'lost':
            membre_avec_points['points_poulains'] = 0
            membre_avec_points['points_podium'] = 0
            membre_avec_points['points_gagnant'] = 0
            membre_avec_points['points_candidats'] = 0
            membre_avec_points['points_feu'] = 0
            membre_avec_points['total'] = 0
        elif marqueur == 'lost':
            membre_avec_points['points_poulains'] = 0
            membre_avec_points['points_podium'] = 0
            membre_avec_points['points_gagnant'] = 0
            membre_avec_points['points_candidats'] = 0
            membre_avec_points['total'] = membre_avec_points['points_feu']
        elif marqueur_feu == 'lost':
            membre_avec_points['points_feu'] = 0
            membre_avec_points['total'] = membre_avec_points['points_candidats']
        else:
            membre_avec_points['total'] = membre_avec_points['points_feu'] + membre_avec_points['points_candidats']
        membres_unsorted.append(membre_avec_points)
    membres_sorted = sorted(membres_unsorted, key=lambda i: i['total'], reverse=True)
    rang = 1
    for joueur in membres_sorted:
        joueur['rang'] = rang
        rang = rang + 1
    return membres_sorted


def equipe_pour_une_ligue(user, ligue_id, episode, selected_candidat):
    current_userprofile = UserProfile.objects.filter(user_id=user.id).first()
    lignes_equipe = Equipe.objects \
        .filter(user_id=current_userprofile.id) \
        .filter(ligue_id=ligue_id) \
        .filter(episode=episode) \
        .filter(type=1) \
        .delete()
    for candidat_id in selected_candidat:
        nouvelle_ligne_equipe = Equipe()
        nouvelle_ligne_equipe.user_id = current_userprofile.id
        nouvelle_ligne_equipe.ligue_id = ligue_id
        nouvelle_ligne_equipe.episode = episode
        nouvelle_ligne_equipe.candidat_id = candidat_id
        nouvelle_ligne_equipe.type = 1
        nouvelle_ligne_equipe.save()


def choix_pour_un_type(user, type_candidat, selected_candidat):
    current_userprofile = UserProfile.objects.filter(user_id=user.id).first()
    lignes_equipe = Choix.objects \
        .filter(user_id=current_userprofile.id) \
        .filter(type=type_candidat) \
        .delete()
    for candidat_id in selected_candidat:
        nouvelle_ligne_choix = Choix()
        nouvelle_ligne_choix.user_id = current_userprofile.id
        nouvelle_ligne_choix.candidat_id = candidat_id
        nouvelle_ligne_choix.type = type_candidat
        nouvelle_ligne_choix.save()


def smtp_send_email(subject, body, sender, recipients):
    smtp_sender = "pilixpiliapp@gmail.com"
    smtp_password = config("smtp_pwd")
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = ', '.join(recipients)
    smtp_server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    smtp_server.login(smtp_sender, smtp_password)
    smtp_server.sendmail(smtp_sender, recipients, msg.as_string())
    smtp_server.quit()


##########################################REGISTRATION ET LOGIN################################
def register_request(request, message):
    if request.method == "POST":
        form = NewUserForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.refresh_from_db()  # load the profile instance created by the signal
            #user.userprofile.id = user.id
            user.userprofile.img = 'dkllapp/img/kitchen/default.png'
            user.userprofile.boolemail = True
            current_site = get_current_site(request)
            context = {
                'user': user,
                'domain': current_site.domain,
                'uidb64': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': account_activation_token.make_token(user), }
            #mail
            subject = "🐣 Activation de ton compte Pili Pili"
            message = render_to_string('dkllapp/account_activation_email.html', context)
            email_from_smtp = "🌶️ Brigade Pili²"
            recipient_list = [user.email]
            smtp_send_email(subject, message, email_from_smtp, recipient_list)
            user.save()
            return redirect('dkllapp:account_activation_sent')
        else:
            message = "Une erreur s'est produite, vérifie que tous les critères sont respectés."
            test_mail = User.objects.filter(email=form.cleaned_data.get('email'))
            test_username = User.objects.filter(username=form.data.get('username'))
            if test_mail:
                message = "L'email est déjà utilisé"
            elif test_username:
                message = "L'identifiant est déjà utilisé"
            else:
                if request.POST['password1'] != request.POST['password2']:
                    message = "Les champs ne sont pas identiques"
                else:
                    if len(request.POST['password1']) > 8:
                        try:
                            test = int(form.cleaned_data.get('password1'))
                            message = "Le mot de passe ne doit pas être entièrement numérique"
                        except ValueError:
                            pass
                    else:
                        message = "Le mot de passe doit faire au moins 9 caractères"
            return redirect('dkllapp:register', message)
    form = NewUserForm()
    return render(request=request, template_name="dkllapp/register.html",
                  context={"register_form": form, 'message': message})


def reinitialiser_mdp(request, message):
    if request.method == "POST":
        form = ReinitailiserMdpForm(request.POST)
        if form.is_valid():
            current_user = User.objects.filter(email=form.cleaned_data.get('email').lower()).first()
            if current_user:
                nouveau_mdp = 'PxP_' + shortuuid.uuid()
                current_user.set_password(nouveau_mdp)
                current_user.save()
                # mail
                current_site = get_current_site(request)
                html_message = loader.render_to_string(
                    'dkllapp/mails/topch_mdp.html',
                    {
                        'user': current_user,
                        'domain': current_site.domain,
                        'from_email': settings.EMAIL_HOST_USER,
                        'nouveau_mdp': nouveau_mdp,
                    }
                )
                email_subject = "🔐 Réinitilisation de ton mot de passe Pili Pili"
                email_from = '🌶️ Brigade Pili² <pilixpiliapp@gmail.com>'
                recipient_list = [current_user.email]
                mail = EmailMultiAlternatives(
                    email_subject, 'This is message', email_from, recipient_list)
                mail.attach_alternative(html_message, "text/html")
                mail.send()

                current_user.save()
                return redirect('dkllapp:profil', '1')
            else:
                message = "Adresse e-mail introuvable"
                return redirect('dkllapp:reinitialiser_mdp', message)
        else:
            message = "Une erreur s'est produite."
            return redirect('dkllapp:reinitialiser_mdp', message)
    form = ReinitailiserMdpForm()
    return render(request=request, template_name="dkllapp/reinitialiser_mdp.html",
                  context={"register_form": form, 'message': message})


def account_activation_sent(request):
    return render(request, 'dkllapp/account_activation_sent.html')


def activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.userprofile.email_confirmed = True
        user.save()
        login(request, user)
        #mail
        current_user = user
        current_site = get_current_site(request)
        html_message = loader.render_to_string(
            'dkllapp/mails/topch_welcome.html',
            {
                'user': current_user,
                'domain': current_site.domain,
                'from_email': settings.EMAIL_HOST_USER,
            }
        )
        email_subject = "🌶️🌶️ Bienvenue sur Pili Pili"
        email_from = '🌶️ Brigade Pili² <pilixpiliapp@gmail.com>'
        recipient_list = [current_user.email]
        mail = EmailMultiAlternatives(
            email_subject, 'This is message', email_from, recipient_list)
        mail.attach_alternative(html_message, "text/html")
        mail.send()
        return redirect('dkllapp:index')
    else:
        return render(request, 'account_activation_invalid.html')


def login_request(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(username=username, password=password)
        user_avec_email = User.objects.filter(email=username).first()
        if user is not None:
            if user.userprofile.email_confirmed is True:
                login(request, user)
                return redirect("dkllapp:index")
            else:
                messages.error(request, "Tu n'as pas confirmé ton e-mail.")
        elif user_avec_email:
            user_email_authentifie = authenticate(username=user_avec_email.username, password=password)
            if user_email_authentifie is not None:
                if user_email_authentifie.userprofile.email_confirmed is True:
                    login(request, user_email_authentifie)
                    return redirect("dkllapp:index")
                else:
                    messages.error(request, "Tu n'as pas confirmé ton e-mail.")
            else:
                messages.error(request, "Login ou mot de passe incorrect.")
        else:
            messages.error(request, "Login ou mot de passe incorrect.")
    form = AuthenticationForm()
    return render(request=request, template_name="dkllapp/login.html",
                  context={"login_form": form})


@login_required
def logout_request(request):
    logout(request)
    return redirect("dkllapp:index")


##########################################FIN REGISTRATION ET LOGIN################################
######################################HOME - INDEX################################
@login_required
def index(request):
    poulains_ouvert = is_poulains()
    podium_ouvert = is_podium()
    gagnant_ouvert = is_gagnant()
    current_userprofile = UserProfile.objects.filter(user_id=request.user.id).first()
    ligues = Membre.objects\
        .filter(user_id=current_userprofile.id).order_by('ligue__insert_datetime')\
        .values('id', 'ligue_id', 'ligue__nom')
    episode_en_cours_ = episode_en_cours()
    notif = Notif.objects.latest('insert_datetime')
    admin_user = UserProfile.objects.values('id', 'img', 'user__username').filter(id=2).first()
    choix_user = Choix.objects \
        .filter(user_id=current_userprofile.id).order_by('candidat_id') \
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

        scores = points_ligue_episode(ligue['ligue_id'], 0)
        ligue['taille'] = len(scores)
        for score in scores:
            if score['id'] == request.user.id:
                ligue['classement_user'] = score['rang']
                ligue['score_user'] = score['total']

    return render(request=request,
                  template_name="dkllapp/index.html",
                  context={'ligues': ligues, 'notif': notif, 'admin_user': admin_user,
                           'choix_user': choix_user, 'lignes_equipes': lignes_equipes,
                           'before_creation': 'index',
                           'poulains_ouvert': poulains_ouvert, 'podium_ouvert': podium_ouvert, 'gagnant_ouvert': gagnant_ouvert,
                           'isadmin': is_admin(request.user.id)})


##########################################Admin################################
@login_required
def admin(request):
    current_userprofile = UserProfile.objects.filter(user_id=request.user.id).first()
    ligues = Membre.objects\
        .filter(user_id=current_userprofile.id).order_by('ligue__insert_datetime')\
        .values('id', 'ligue_id', 'ligue__nom')
    episode_en_cours_ = episode_en_cours()
    poulains_ouvert = is_poulains()
    podium_ouvert = is_podium()
    gagnant_ouvert = is_gagnant()
    nbr_users = len(UserProfile.objects.filter(email_confirmed=True).all()) - 1
    nbr_users_actifs = len(Membre.objects.values('user_id').distinct())
    nbr_users_equipe_prochain_episode = len(EquipesFaites.objects.filter(episode=episode_en_cours_).filter(count__gt=1).values('user_id').distinct())
    # Tableau règles
    regles = Regle.objects.all().order_by('insert_datetime')
    # Tableau questions
    questions = Question.objects.all().order_by('episode').order_by('-insert_datetime')
    questions_plus = []
    for question in questions:
        propositions = Proposition.objects.filter(question_id=question.id)
        repondu = False
        for proposition in propositions:
            if proposition.pertinence:
                repondu = True
        questions_plus.append({'question': question, 'propositions': propositions, 'repondu': repondu})
    # Tableau evenement
    evenements = Evenement.objects.all().order_by('-insert_datetime')\
        .values('id', 'user__user__username', 'regle__contenu', 'candidat__nom',
                'candidat__chemin_img', 'episode', 'typage', 'insert_datetime')
    # envoi de forms
    if request.method == 'POST':
        type_choix = 'activate' if '_activate_' in list(request.POST)[1] \
            else 'deactivate' if '_deactivate_' in list(request.POST)[1] else ''
        type_activation = 'poulains' if 'poulains' in list(request.POST)[1] \
            else 'podium' if 'podium' in list(request.POST)[1] \
            else 'gagnant' if 'gagnant' in list(request.POST)[1] else ''
        # si pas de form activation candidats
        if (type_choix, type_activation) == ('', ''):
            form_mail = MailAdminForm(request.POST)
            form_notif = NotifAdminForm(request.POST)
            form_regle = ModifierRegleForm(request.POST)
            # form questions
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
            # form mail
            if form_mail.is_valid():
                current_user = request.user
                current_site = get_current_site(request)
                html_message = form_mail.cleaned_data.get("corps")
                email_subject = form_mail.cleaned_data.get("sujet")
                email_from = '🌶️ Brigade Pili² <pilixpiliapp@gmail.com>'
                recipient_list = []
                if form_mail.cleaned_data.get('users') is True:
                    all_users = UserProfile.objects.values('user__email').filter(boolemail=True).all()
                    for un_user in all_users:
                        recipient_list.append(un_user['user__email'])
                elif form_mail.cleaned_data.get('admin') is True:
                    #recipient_list = ['louise2004gautier@gmail.com']
                    recipient_list = ['louise2004gautier@gmail.com', 'lau.oberto@gmail.com', 'marieanne.baudin@gmail.com']
                    #recipient_list = ['jade.accabat@live.fr','louise.beugniet@gmail.com','sinda.tajouri@gmail.com','jordan.lorho@toucantoco.com','aurelien.crouzet@gmail.com','audrey.lacour01@gmail.com','pascal.delbosc@gmail.com','jonathan.chamignon@gmail.com','lau.oberto@gmail.com','marie.dubus@hotmail.com','nicoriri9@gmail.com','louise_gautier@orange.fr','clemdums@hotmail.com','thomasdanvin@gmail.com','marjo_0404@hotmail.fr','kevin.seysen@gmail.com','elsa.dechambrun@gmail.com','constance.laumone@gmail.com','TCL@TCL.fr','isaure.debecdelievre@gmail.com','ansel.buzancais@live.fr','raphbrl26@gmail.com','chloewibaux@gmail.com','timfirst@hotmail.fr','leila.zenak@gmail.com','marieanne.baudin@gmail.com','adeline_842@hotmail.com','fanny_mf@live.fr','cmll.granger@gmail.com','theofellous@gmail.com','normam4@wanadoo.fr','elodie.queyranne@gmail.com','mllemeissa@msn.com','lunahmt@gmail.com','etiennefauv@hotmail.fr','margaux.daguillon@gmail.com','agbo.romain@hotmail.fr','carod35@hotmail.fr','guerric1@yahoo.com','bestanlo@hotmail.com','baptiste.basket@hotmail.fr','aze2112@gmail.com','flore.giesler@gmail.com','romandilly@gmail.com','louisedamy@hotmail.fr','will.pnzk@gmail.com','mathieu.sanchez@outlook.fr','imen.braham@gmail.com','clement.fonteneau@yahoo.fr','jess_bertho@hotmail.fr','anpiwa@mailoo.org','coline.cros@gmail.com','julie.cavillot@hotmail.com','lea.fievet@iae-aix.com','charles.merriaud@gmail.com','justinelegal@hotmail.fr','charlene-brize@live.fr','malak.khalil@gmail.com','fanny.mijon@gmail.com','auguste.ballu@gmail.com','matthieu.raussou@gmail.com','martincosteau@hotmail.fr','justine.le-gal@hei.yncrea.fr','chloe.aubinaud@gmail.com','astrid.ngeto@hotmail.fr','ppaulinedenis@gmail.com','marie.prim@hotmail.fr','soltanar@hotmail.com','philippine.leon@icloud.com','celine270497@gmail.com','hortensefievet@hotmail.fr','louis.bolteau@gmail.com','mderoit@gmail.com','juliette.francois4@gmail.com','martin.herbelin@gmail.com','anthony.mat@hotmail.fr','ziatihicham2@gmail.com','merlin.aurelie@hotmail.fr','adeletoutain@hotmail.fr','marieandreo@msn.com','m.opinel@hotmail.fr','ines.girard-de-courtilles@hei.yncrea.fr','marion.cousseau@gmail.com','v.cousseau@gmx.fr','salome.jay@gmail.com','enzo-manent@hotmail.fr','elodie.coudry@hotmail.fr','c.grangechavanis@gmail.com','mylene.andreu@yahoo.fr','hh-f@hotmail.fr','josephine.ranson@hotmail.fr','mariie.fabre@gmail.com','ma.thiebaud@gmail.com','anais.kerdraon@hotmail.fr','melissa.langlois0@gmail.com','benallal.tayeb@gmail.com','jdemontes@audencia.com','margauxpons31@gmail.com','albangrangechavanis@gmail.com','florence.desthieux@gmail.com','thomas.dambrine1@gmail.com','mpouyal@gmail.com','rongere.audrey@gmail.com','laura.arnaud31@gmail.com','jeremy.margeot@gmail.com','claire.mvincent@gmail.com','cyrielle.cleenewerck@hotmail.fr','nonopetitbrun@hotmail.fr','louis.chene@gmail.com','yohan.hericher@gmail.com','laurie.lemaitre@shippingbo.com','pierre.bonhoure@shippingbo.com','caro271093@hotmail.fr','astrid.ngeto@gmail.com','laurewibaux@gmail.com','myriammontosamoysan@gmail.com','gregoire.ghuysen@hotmail.fr','galtier.catherine@gmail.com','rebecca.perdriault@gmail.com','cecileramond@gmail.com','carotte_pas_fraiche@hotmail.fr','ow_steven@hotmail.com','julie.cdlc@gmail.com','tieuma29@hotmail.fr','lkhiat@gmail.com','doualla.g@gmail.com','matthfo@gmail.com','pauline.guitton@gmail.com','camille.potier@hotmail.com','celine.degayffier@yahoo.fr','vlefrancois@audencia.com','yayem1996@gmail.com','benjaminecotten@hotmail.fr','hortense@agroptima.com','hort.giraud@gmail.com','louis_bondu@hotmail.com','annabelle-chalopin@hotmail.fr','darcissac.c@gmail.com','porral.mathieu@gmail.com','keller.laetitia@hotmail.com','pi.mauries@gmail.com','goran.stefanovic@ymail.com','theokraif1995@gmail.com','loucomte31@gmail.com','qh.hamonou@gmail.com','savannahsalvoni@gmail.com','matthieu2609@gmail.com','aderevel@gmail.com','hilairebesse@gmail.com','cel.touloum@gmail.com','nadal.maxime@gmail.com','nicolas.lemehaute@orange.fr','celia.raque@hec.edu','xavier.harder@edhec.com','mbacquet24@gmail.com','thomas.stage.machine@gmail.com','arthur.chatain@gmail.com','nicolasgervais@live.fr','nicofaivre@orange.fr','mickael_abtan@hotmail.com','vianney-t@hotmail.com','piko49@gmail.com','violette.dubois59@gmail.com','elise_enriquez@hotmail.fr','marine.abtan@gmail.com','anthony.bonin23@gmail.com','abitboljerem@gmail.com','n.moreau1001@gmail.com','erik.delecourt@gmail.com','nathanjaoui@gmail.com','h.chaouch@tbs-education.org','thomas.ziegler@outlook.fr','tatoon.fraisse@gmail.com','victor.bdf@icloud.com','martin.blondel7@gmail.com','anne.robert85@gmail.com','efrank93@gmail.com','guillaumedelmas25@gmail.com','guilhemsauvaire30@gmail.com','clemence.nepveux@gmail.com','arthur.chatain@wanadoo.fr','elsa.j26@wanadoo.fr','firmin.thibault@yahoo.fr','paul.petit13@gmail.com','solene-jacquart@hotmail.fr','fizzypolak@hotmail.fr','nicolas.dobro@gmail.com','cambourakis.jules@gmail.com','sashal@hotmail.fr','alexandre.keller@hec.edu','benjamin.dadolle@yahoo.fr','annelise.jaunet@gmail.com','cecileburdillat@hotmail.fr','herz@yopmail.co','herzhang@hotmail.com','theokraif.aviva@outlook.fr','clara.jaoui@hotmail.com','charles.modaine@gmail.com','henri.callens@hotmail.fr','evaingelaere@gmail.com','camillepignol@hotmail.fr','antoine.guichard35@gmail.com','benjamin.fagu@gmail.com','teddy-smith-35@hotmail.fr','cryptomatth@gmail.com','mathildeandrier@live.fr','jadesophie.valtat@gmail.com','quentindonsimon@gmail.com','emmanuel.Chomier@hotmail.fr','bgueugnon@em-normandie.fr','etienne.favre@outlook.com','julian.andreo@iae-aix.com','geoffrey.bugnon@gmail.com','marietoison@hotmail.fr','green__apple@hotmail.fr','Falanga.danielle@gmail.com','sandra.gillet@iae-aix.com','leaa.rem@gmail.com','amaury.andreetti@gmail.com','arnosbh@gmail.com','luc.mercereau@hotmail.fr','test@hotmail.fr','juliecendrier355@gmail.com','klein.vhb09@gmail.com','julie.doffemont@gmail.com','gregoire.poulin@outlook.fr','andra-@hotmail.fr','valentine.geindre@gmail.com','t.cloe@yahoo.fr','her@yopmail.com','savannah.s@hotmail.fr','yousra.namir3@gmail.com','antoinetezenas@yahoo.fr','chloecarreric@gmail.com','lynda.aob@gmail.com','flobonnet7@hotmail.com','thibaut.bousquet@gmail.com','emma.desgages@hotmail.fr','charlotte.guimier@outlook.com','qu_jessica@live.fr','alicia.desgrees@gmail.com','yves.matton@technofounders.com','tessier1902@gmail.com','t.martel@stimuli-technology.com','raph-tn@hotmail.fr','dbousquie@gmail.com','jeanne.raison@yahoo.fr','martin.huerre@orange.fr','rom20100@gmail.com','daveperrot@gmail.com','clementine.artemis@gmail.com','trogerantoine@gmail.com','agathe.sowinski@essec.edu','comefradetal@gmail.com','ragagnonj@gmail.com','mathilde.quere@gmx.fr','jean-baptiste.civit@wanadoo.fr','mathilde.pinatel@hotmail.fr','agathe.secall@sciencespo.fr','julien.noel111@gmail.com','heloisepeaud@gmail.com','ines.journois@gmail.com','lucas.andres.etu@gmail.com','florian.lequere@gmail.com','math.mattei@gmail.com','thomas.foucher33@gmail.com','chrsrodrigues@gmail.com','agnes.bucheli-civit@wanadoo.fr','lise.x.3@hotmail.fr','mathilde_carles@hotmail.com','sibyllegros@gmail.com','adrienvert10@hotmail.fr','a.pralong@yahoo.fr','johnatan.muallem@gmail.com','arielle.lebail@gmail.com','francoiseveillepeau@hotmail.com','gregoire.maisonneuve@orange.fr','ch.tassel@hotmail.com','ch.tassel@advance-capital.fr','guileneuf@hotmail.com','jean-baptiste@28ddesign.com','alix.civit@wanadoo.fr','alix@lgamanagement.com','christiphe.civit65@gmail.com','zajdlaurie@gmail.com','jdallagata@hotmail.fr','jeannepages@wanadoo.fr','estelle.godard@hotmail.com','marie.cozette2611@gmail.com','hanymyriam97@gmail.com','salome.papuchon.bba@edhec.com','gildas.eveno@gmail.com','valentindacosta92@gmail.com','morgane.nopper@gmail.com','marie.pralong83@gmail.com','yannis.kadiri@gmail.com','aurelplg@gmail.com','tom-pineau@hotmail.fr','firm1.b@gmail.com','edouardtrabuc@hotmail.fr','priscillegrange@hotmail.fr','camille-lt@hotmail.fr','grandhomme.leo@gmail.com','guillaume.tirel@essec.edu','gloriamailys@gmail.com','maite.m.richard@gmail.com','ellena.tessore@gmail.com','julie@belloir.fr','myriamhany@laposte.net','hanymyriam97@outlook.fr','aerolivesili@hotmail.fr','margaux.devroede@ieseg.fr','diane.gloria@hotmail.fr','jaybe2007@hotmail.fr','nicolas.bouvattier@digeiz.com','nicolasbouvattier@gmail.com','alicenovet3101@gmail.com','juliettepauthe@hotmail.com','louisemporcher@gmail.com','marion.bechu@playplay.com','hortense.drevon@gmail.com','camille.sampoux@gmail.com','charlotte.lequeux13@gmail.com','charlotte.fontan@hotmail.fr','baptiste.tignol@gmail.com','valentine.aguiar@hotmail.fr','agathe.loustalet@gmail.com','contact@floda.me','grinnyhermant@gmail.com','zaf.aflalo@gmail.com','sarahisal@hotmail.fr','nini.denfer@yahoo.fr','laura.genc@outlook.fr','albanededumast@hotmail.fr','ardonquentin@orange.fr','sabine.bardaune@gmail.com','marie-charlotte.dautel@hotmail.fr','irisdevillele@gmail.com','elodie.pradels@gmail.com','philippine.franc@gmail.com','alix.rodarie@gmail.com','cedric.souidaray@gmail.com','margedudela@hotmail.com','martinet.alix@gmail.com','ivan.valerio@gmail.com','mahomerlino@gmail.com','ayanamerlino@gmail.com','lucaskrumbholz@wanadoo.fr','jason.maurisset@gmail.com']
                else:
                    return redirect('dkllapp:admin')
                mail = EmailMultiAlternatives(
                    email_subject, 'This is message', email_from, [], bcc=recipient_list)
                mail.attach_alternative(html_message, "text/html")
                mail.send()
            # form notifications
            if form_notif.is_valid():
                nouvelle_notif = Notif()
                nouvelle_notif.message = form_notif.cleaned_data.get('message')
                nouvelle_notif.lien = form_notif.cleaned_data.get('lien')
                nouvelle_notif.save()
                return redirect('dkllapp:admin')
            # form regles
            if form_regle.is_valid():
                nouvelle_regle = Regle.objects.filter(id=form_regle.cleaned_data.get('regle_a_modifier')).first()
                if nouvelle_regle:
                    return redirect('dkllapp:modifier_regle', nouvelle_regle.id)
                else:
                    return redirect('dkllapp:admin')
        else:
            # si form activation candidats
            admin_activation_choix(type_choix, type_activation)
            return redirect('dkllapp:admin')
    form_mail = MailAdminForm()
    form_notif = NotifAdminForm()
    form_regle = ModifierRegleForm()
    return render(request=request,
                  template_name="dkllapp/admin.html",
                  context={'ligues': ligues, 'episode_en_cours_': episode_en_cours_,
                           'nbr_users': nbr_users, 'nbr_users_actifs': nbr_users_actifs,
                           'nbr_users_equipe_prochain_episode': nbr_users_equipe_prochain_episode,
                           'form_mail': form_mail, 'form_notif': form_notif, 'form_regle': form_regle,
                           'regles': regles, 'evenements': evenements, 'questions_plus': questions_plus,
                           'isadmin': is_admin(request.user.id), 'poulains_ouvert': poulains_ouvert,
                           'podium_ouvert': podium_ouvert, 'gagnant_ouvert': gagnant_ouvert})


@login_required
def changer_episode(request):
    current_userprofile = UserProfile.objects.filter(user_id=request.user.id).first()
    ligues = Membre.objects\
        .filter(user_id=current_userprofile.id).order_by('ligue__insert_datetime')\
        .values('id', 'ligue_id', 'ligue__nom')
    if request.method == "POST":
        form = EpisodeChangeForm(request.POST)
        if form.is_valid():
            episode_a_changer = Episode.objects.filter(nom='episode').first()
            episode_a_changer.valeur = form.cleaned_data.get('new_episode')
            episode_a_changer.save()
            nouvelle_notif = Notif()
            nouvelle_notif.message = "Zepartiii pour l’épisode " + str(episode_a_changer.valeur - 1) + ", on espère que tu as fait ta compo ! 🧑‍🍳"
            nouvelle_notif.lien = "/"
            nouvelle_notif.save()

            membres = Membre.objects.all().order_by('id')
            for membre in membres:
                poulains = Choix.objects.filter(user_id=membre.user_id).filter(type=1).order_by('id')
                if len(poulains) == 6:
                    equipe_poulains = Equipe.objects.filter(user_id=membre.user_id).filter(ligue_id=membre.ligue_id)\
                        .filter(type=1).filter(episode=episode_en_cours()).order_by('id')
                    if len(equipe_poulains) >= 1:
                        pass
                    else:
                        poulains_id = []
                        for candidat in poulains:
                            poulains_id.append(candidat.candidat_id)
                        nouvelle_ligne_equipe = Equipe()
                        nouvelle_ligne_equipe.user_id = membre.user_id
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
                            nouvelle_ligne_equipe.user_id = membre.user_id
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
                            nouvelle_ligne_equipe.user_id = membre.user_id
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
    current_userprofile = UserProfile.objects.filter(user_id=request.user.id).first()
    ligues = Membre.objects\
        .filter(user_id=current_userprofile.id).order_by('ligue__insert_datetime')\
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
    return render(request=request,
                  template_name="dkllapp/changer_equipe_tv.html",
                  context={'ligues': ligues, 'episode_en_cours_': episode_en_cours_,
                           'form': form, 'candidats': candidats,
                           'isadmin': is_admin(request.user.id)})


@login_required
def changer_statut(request):
    current_userprofile = UserProfile.objects.filter(user_id=request.user.id).first()
    ligues = Membre.objects\
        .filter(user_id=current_userprofile.id).order_by('ligue__insert_datetime')\
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
    return render(request=request,
                  template_name="dkllapp/changer_statut.html",
                  context={'ligues': ligues, 'episode_en_cours_': episode_en_cours_,
                           'form': form, 'candidats': candidats,
                           'isadmin': is_admin(request.user.id)})


@login_required
def ajouter_question(request, question_id):
    current_userprofile = UserProfile.objects.filter(user_id=request.user.id).first()
    ligues = Membre.objects\
        .filter(user_id=current_userprofile.id).order_by('ligue__insert_datetime')\
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
            if question_id == '0':
                nouvelle_notif = Notif()
                nouvelle_notif.message = "🔥 De nouveaux pronos sont disponibles !"
                nouvelle_notif.lien = "/pronos/1"
                nouvelle_notif.save()
            if form.cleaned_data.get('is_mail'):
                #mail
                current_user = request.user
                current_site = get_current_site(request)
                html_message = loader.render_to_string(
                    'dkllapp/mails/topch_prono2.html',
                    {
                        'user': current_user,
                        'domain': current_site.domain,
                        'from_email': settings.EMAIL_HOST_USER,
                        'enonce': question.enonce,
                        'bonus': question.bonus,
                        'malus': question.malus,
                    }
                )
                email_subject = "🔥 Un nouveau prono est disponible !"
                email_from = '🌶️ Brigade Pili² <pilixpiliapp@gmail.com>'
                all_users = UserProfile.objects.values('user__email').filter(boolemail=True).all()
                recipient_list = []
                for un_user in all_users:
                    recipient_list.append(un_user['user__email'])
                mail = EmailMultiAlternatives(
                    email_subject, 'This is message', email_from, [], bcc=recipient_list)
                mail.attach_alternative(html_message, "text/html")
                mail.send()

            return redirect('dkllapp:admin')
    form = AjouterQuestionForm()
    return render(request=request,
                  template_name="dkllapp/ajouter_question.html",
                  context={'ligues': ligues, 'episode_en_cours_': episode_en_cours_, 'form': form,
                           'question': question, 'propositions': propositions,
                           'isadmin': is_admin(request.user.id)})


@login_required
def ajouter_reponse(request, question_id):
    current_userprofile = UserProfile.objects.filter(user_id=request.user.id).first()
    ligues = Membre.objects\
        .filter(user_id=current_userprofile.id).order_by('ligue__insert_datetime')\
        .values('id', 'ligue_id', 'ligue__nom')
    episode_en_cours_ = episode_en_cours()
    question = Question.objects.filter(id=question_id).first()
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
                           'propositions': propositions, 'question': question,
                           'isadmin': is_admin(request.user.id)})


@login_required
def modifier_regle(request, regle_id):
    current_userprofile = UserProfile.objects.filter(user_id=request.user.id).first()
    ligues = Membre.objects\
        .filter(user_id=current_userprofile.id).order_by('ligue__insert_datetime')\
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
    current_userprofile = UserProfile.objects.filter(user_id=request.user.id).first()
    ligues = Membre.objects\
        .filter(user_id=current_userprofile.id).order_by('ligue__insert_datetime')\
        .values('id', 'ligue_id', 'ligue__nom')
    episode_en_cours_ = episode_en_cours()
    candidats = Candidat.objects.all().order_by('id')\
        .values('id', 'nom', 'equipe_tv', 'chemin_img', 'statut', 'statut_bool', 'form_id')
    regles = Regle.objects.all().order_by('insert_datetime').values('id', 'contenu')
    choices = [(regle['id'], regle['contenu']) for regle in regles]
    new_fields = {}
    for candidat in candidats:
        new_fields[candidat['form_id']] = forms.BooleanField(required=False)
    new_fields['regle'] = forms.ChoiceField(choices=choices, required=True, widget=forms.Select(attrs={'class': "form_select"}))
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
                    nouvel_evenenement.user_id = current_userprofile.id
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
    current_userprofile = UserProfile.objects.filter(user_id=request.user.id).first()
    ligues = Membre.objects\
        .filter(user_id=current_userprofile.id).order_by('ligue__insert_datetime')\
        .values('id', 'ligue_id', 'ligue__nom')
    current_ligue = Ligue.objects.filter(id=ligue_id).values('id', 'nom')[0]
    #values('user__username', 'img')
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
    mur_inverse = mur.reverse()

    DynamicMessageMurForm = type('DynamicMessageMurForm', (MessageMurForm,), new_fields)
    if request.method == "POST":
        form = DynamicMessageMurForm(request.POST)
        for field in request.POST:
            if field == 'csrfmiddlewaretoken':
                pass
            elif request.POST[field]:
                if field == 'nouveau_parent':
                    nouveau_message = Mur()
                    nouveau_message.user_id = current_userprofile.id
                    nouveau_message.ligue_id = ligue_id
                    nouveau_message.message = request.POST[field]
                    nouveau_message.save()
                elif 'area' in field:
                    nouveau_message = Mur()
                    nouveau_message.user_id = current_userprofile.id
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
    admin_user = UserProfile.objects.values('id', 'img', 'user__username').filter(id=2).first()
    return render(request=request,
                  template_name="dkllapp/mur.html",
                  context={'ligues': ligues, 'page': 'mur', 'current_ligue': current_ligue,
                           'mur': mur, 'mur_inverse': mur_inverse,
                           'notif': notif, 'admin_user': admin_user,
                           'current_user': current_userprofile, 'form': form,
                           'isadmin': is_admin(request.user.id)})


@login_required
def equipe(request, ligue_id):
    current_userprofile = UserProfile.objects.filter(user_id=request.user.id).first()
    ligues = Membre.objects\
        .filter(user_id=current_userprofile.id).order_by('ligue__insert_datetime')\
        .values('id', 'ligue_id', 'ligue__nom')
    current_ligue = Ligue.objects.filter(id=ligue_id).values('id', 'nom')[0]
    episode_en_cours_ = episode_en_cours()
    liste_episode = list(range(1, episode_en_cours_ + 1))
    liste_episode.reverse()
    poulains_ouvert = is_poulains()
    podium_ouvert = is_podium()
    gagnant_ouvert = is_gagnant()
    choix_user = Choix.objects \
        .filter(user_id=current_userprofile.id).order_by('candidat_id') \
        .values('id', 'type', 'candidat_id', 'candidat__nom', 'candidat__equipe_tv', 'candidat__chemin_img',
                'candidat__statut', 'candidat__statut_bool')
    equipe = Equipe.objects \
        .filter(user_id=current_userprofile.id) \
        .filter(ligue_id=current_ligue['id']) \
        .filter(episode=episode_en_cours_) \
        .filter(type=1) \
        .order_by('candidat_id') \
        .values('id', 'candidat_id', 'candidat__nom', 'candidat__equipe_tv', 'candidat__chemin_img',
                'candidat__statut', 'candidat__statut_bool', 'type')

    equipes = Equipe.objects \
        .filter(user_id=current_userprofile.id) \
        .filter(ligue_id=current_ligue['id']) \
        .filter(type=1) \
        .order_by('-episode') \
        .order_by('candidat_id') \
        .values('id', 'episode', 'candidat_id', 'candidat__nom', 'candidat__equipe_tv', 'candidat__chemin_img',
                'candidat__statut', 'candidat__statut_bool', 'type')
    return render(request=request,
                  template_name="dkllapp/equipe.html",
                  context={'ligues': ligues, 'page': 'equipe',
                           'equipe': equipe, 'choix_user': choix_user, 'equipes': equipes,
                           'ligue_id': ligue_id, 'before_creation': 'equipe', 'liste_episode': liste_episode,
                           'episode_en_cours_': episode_en_cours_, 'current_ligue': current_ligue,
                           'poulains_ouvert': poulains_ouvert, 'podium_ouvert': podium_ouvert,
                           'gagnant_ouvert': gagnant_ouvert, 'isadmin': is_admin(request.user.id)})


@login_required
def resultat(request, ligue_id):
    current_userprofile = UserProfile.objects.filter(user_id=request.user.id).first()
    ligues = Membre.objects\
        .filter(user_id=current_userprofile.id).order_by('ligue__insert_datetime')\
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
    current_userprofile = UserProfile.objects.filter(user_id=request.user.id).first()
    ligues = Membre.objects\
        .filter(user_id=current_userprofile.id).order_by('ligue__insert_datetime')\
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
    current_userprofile = UserProfile.objects.filter(user_id=request.user.id).first()
    ligues = Membre.objects\
        .filter(user_id=current_userprofile.id).order_by('ligue__insert_datetime')\
        .values('id', 'ligue_id', 'ligue__nom')
    current_user = User.objects.filter(id=request.user.id).first()
    if request.method == "POST":
        form = LigueCreationForm(request.POST)
        if form.is_valid():
            current_ligue = Ligue.objects.filter(id=ligue_id).first()
            old_name = current_ligue.nom
            current_ligue.nom = form.cleaned_data.get('nom')
            current_ligue.save()
            nouvelle_ligne_mur = Mur()
            nouvelle_ligne_mur.message = "✏️" + str(current_user.username) \
                                         + " a changé le nom de la ligue " + old_name + " en " + current_ligue.nom
            nouvelle_ligne_mur.user_id = 2
            nouvelle_ligne_mur.ligue_id = ligue_id
            nouvelle_ligne_mur.save()
            return redirect('dkllapp:details', current_ligue.id, '0')
    form = LigueCreationForm()
    return render(request=request,
                  template_name="dkllapp/changer_nom_ligue.html",
                  context={'form': form, 'ligues': ligues,
                           'isadmin': is_admin(request.user.id)})


##########################################Pronos################################
@login_required
def pronos(request, message):
    current_userprofile = UserProfile.objects.filter(user_id=request.user.id).first()
    ligues = Membre.objects\
        .filter(user_id=current_userprofile.id).order_by('ligue__insert_datetime')\
        .values('id', 'ligue_id', 'ligue__nom')
    episode_en_cours_ = episode_en_cours()
    questions = Question.objects.filter(episode=episode_en_cours_).order_by('-insert_datetime')
    questions_plus = []
    message = message
    new_fields = {}
    for question in questions:
        propositions = Proposition.objects.filter(question_id=question.id)
        guess = Guess.objects.filter(question_id=question.id).filter(user_id=current_userprofile.id).first()
        questions_plus.append({'question': question, 'guess': guess, 'propositions': propositions})
        radio_propositions = []
        for proposition in propositions:
            form_id = '{0:03d}'.format(question.id) + "_" + '{0:03d}'.format(proposition.id)
            radio_propositions.append((form_id, proposition.texte))
            new_fields['{0:03d}'.format(question.id)] = forms.ChoiceField(choices=radio_propositions, widget=forms.RadioSelect, required=False)
    DynamicPronosGuessForm = type('DynamicPronosGuessForm', (PronosGuessForm,), new_fields)
    if request.method == "POST":
        form = DynamicPronosGuessForm(request.POST)
        if "btn_effacer" in request.POST:
            Guess.objects.filter(question__episode=episode_en_cours()).filter(user_id=current_userprofile.id).delete()
            message = "Réponses effacées"
            return redirect('dkllapp:pronos', message)
        else:
            if form.is_valid():
                if message == "":
                    pass
                for long_question_id in form.cleaned_data:
                    if form.cleaned_data[long_question_id]:
                        current_user_guess = Guess.objects.filter(question_id=int(long_question_id)).filter(user_id=current_userprofile.id).first()
                        guess_proposition_id = int(form.cleaned_data[long_question_id][4:7])
                        if current_user_guess:
                            Guess.objects.filter(question_id=int(long_question_id)).filter(user_id=current_userprofile.id).delete()
                            nouveau_guess = Guess()
                            nouveau_guess.user_id = current_userprofile.id
                            nouveau_guess.question_id = int(long_question_id)
                            nouveau_guess.proposition_id = guess_proposition_id
                            nouveau_guess.save()
                            message = "Réponses validées"
                        else:
                            nouveau_guess = Guess()
                            nouveau_guess.user_id = current_userprofile.id
                            nouveau_guess.question_id = int(long_question_id)
                            nouveau_guess.proposition_id = guess_proposition_id
                            nouveau_guess.save()
                            message = "Réponses validées"
                    else:
                        pass
                return redirect('dkllapp:pronos', message)
    form = DynamicPronosGuessForm()
    return render(request=request,
                  template_name="dkllapp/pronos.html",
                  context={'ligues': ligues, 'page': 'pronos', 'questions_plus': questions_plus,
                           'form': form,  'message': message,
                           'isadmin': is_admin(request.user.id)})


@login_required
def bonus(request):
    current_userprofile = UserProfile.objects.filter(user_id=request.user.id).first()
    ligues = Membre.objects\
        .filter(user_id=current_userprofile.id).order_by('ligue__insert_datetime')\
        .values('id', 'ligue_id', 'ligue__nom')
    questions = Question.objects.order_by('-episode').order_by('-insert_datetime')
    liste_episode = list(range(1, episode_en_cours() + 1))
    liste_episode.reverse()
    questions_plus = []
    for question in questions:
        propositions = Proposition.objects.filter(question_id=question.id)
        repondu = False
        for proposition in propositions:
            if proposition.pertinence:
                repondu = True
        guess = Guess.objects.filter(question_id=question.id).filter(user_id=current_userprofile.id)\
            .values('id', 'user_id', 'question_id', 'proposition_id', 'proposition__pertinence').first()
        questions_plus.append({'question': question, 'guess': guess,
                               'propositions': propositions, 'repondu': repondu})
    points_feu = PointsFeu.objects.filter(user_id=current_userprofile.id).values('user_id', 'feu').order_by('user_id').first()
    return render(request=request,
                  template_name="dkllapp/bonus.html",
                  context={'ligues': ligues, 'page': 'bonus', 'liste_episode': liste_episode,
                           'questions_plus': questions_plus, 'points_feu': points_feu,
                           'isadmin': is_admin(request.user.id)})


##########################################Profil################################
@login_required
def profil(request, message):
    current_userprofile = UserProfile.objects.filter(user_id=request.user.id).first()
    ligues = Membre.objects\
        .filter(user_id=current_userprofile.id).order_by('ligue__insert_datetime')\
        .values('id', 'ligue_id', 'ligue__nom')
    message = message
    if request.method == "POST":
        form = ProfilMailForm(request.POST)
        if form.is_valid():
            current_userprofile.boolemail = form.cleaned_data.get('mail')
            message = "Choix pris en compte"
            current_userprofile.save()
            return redirect('dkllapp:profil', message)
    form = ProfilMailForm()
    return render(request=request,
                  template_name="dkllapp/profil.html",
                  context={'candidats': candidats, 'ligues': ligues, 'page': 'profil',
                           'before_creation': 'profil',
                           'current_userprofile': current_userprofile, 'message': message,
                           'isadmin': is_admin(request.user.id)})


@login_required
def ligues_user(request):
    current_userprofile = UserProfile.objects.filter(user_id=request.user.id).first()
    ligues = Membre.objects\
        .filter(user_id=current_userprofile.id).order_by('ligue__insert_datetime')\
        .values('id', 'ligue_id', 'ligue__nom')
    for ligue in ligues:
        scores = points_ligue_episode(ligue['ligue_id'], 0)
        ligue['taille'] = len(scores)
        for score in scores:
            if score['id'] == request.user.id:
                ligue['classement_user'] = score['rang']
                ligue['score_user'] = score['total']
    return render(request=request,
                  template_name="dkllapp/ligues_user.html",
                  context={'candidats': candidats, 'ligues': ligues, 'page': 'ligues_user',
                           'current_userprofile': current_userprofile,
                           'isadmin': is_admin(request.user.id)})


@login_required
def candidats_user(request):
    current_userprofile = UserProfile.objects.filter(user_id=request.user.id).first()
    ligues = Membre.objects\
        .filter(user_id=current_userprofile.id).order_by('ligue__insert_datetime')\
        .values('id', 'ligue_id', 'ligue__nom')
    poulains_ouvert = is_poulains()
    podium_ouvert = is_podium()
    gagnant_ouvert = is_gagnant()
    choix_user = Choix.objects\
        .filter(user_id=current_userprofile.id).order_by('candidat_id')\
        .values('id', 'type', 'candidat_id', 'candidat__nom',
                'candidat__equipe_tv', 'candidat__chemin_img', 'candidat__statut', 'candidat__statut_bool')
    return render(request=request,
                  template_name="dkllapp/candidats_user.html",
                  context={'ligues': ligues, 'page': 'candidats_user', 'choix_user': choix_user,
                           'current_userprofile': current_userprofile,
                           'poulains_ouvert': poulains_ouvert, 'podium_ouvert': podium_ouvert,
                           'gagnant_ouvert': gagnant_ouvert, 'isadmin': is_admin(request.user.id)})


@login_required
def choix(request, type_choix, before, txt):
    current_userprofile = UserProfile.objects.filter(user_id=request.user.id).first()
    ligues = Membre.objects\
        .filter(user_id=current_userprofile.id).order_by('ligue__insert_datetime')\
        .values('id', 'ligue_id', 'ligue__nom')
    episode_en_cours_ = episode_en_cours()
    txt_alert = txt
    choix_user = Choix.objects.values("candidat_id").filter(type=type_choix).filter(user_id=current_userprofile.id).all()
    ids_choix = []
    for un_choix in choix_user:
        ids_choix.append(un_choix['candidat_id'])
    candidats = Candidat.objects.all().order_by('id')\
        .values('id', 'nom', 'equipe_tv', 'chemin_img', 'statut', 'statut_bool', 'form_id')
    new_fields = {}
    for candidat in candidats:
        if candidat['id'] in ids_choix:
            new_fields[candidat['form_id']] = forms.BooleanField(initial=True, required=False)
        else:
            new_fields[candidat['form_id']] = forms.BooleanField(initial=False, required=False)
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
                    return redirect('dkllapp:profil', '1')
                else:
                    return redirect('dkllapp:index')
            else:
                txt_alert = "alert"
                return redirect('dkllapp:choix', type_choix, before, txt_alert)
    form = DynamicChoixCreationForm()
    return render(request=request,
                  template_name="dkllapp/choix.html",
                  context={'form': form, 'ligues': ligues, 'candidats': candidats, 'txt_alert': txt,
                           'type_choix': type_choix, 'ids_choix': ids_choix,
                           'isadmin': is_admin(request.user.id)})


##########################################Règles################################
@login_required
def generales(request):
    current_userprofile = UserProfile.objects.filter(user_id=request.user.id).first()
    ligues = Membre.objects\
        .filter(user_id=current_userprofile.id).order_by('ligue__insert_datetime')\
        .values('id', 'ligue_id', 'ligue__nom')
    return render(request=request,
                  template_name="dkllapp/generales.html",
                  context={'ligues': ligues, 'page': 'generales',
                           'isadmin': is_admin(request.user.id)})


@login_required
def bareme(request):
    current_userprofile = UserProfile.objects.filter(user_id=request.user.id).first()
    ligues = Membre.objects\
        .filter(user_id=current_userprofile.id).order_by('ligue__insert_datetime')\
        .values('id', 'ligue_id', 'ligue__nom')
    regles = Regle.objects.exclude(id=17).exclude(id=21).order_by('id')
    return render(request=request,
                  template_name="dkllapp/bareme.html",
                  context={'ligues': ligues, 'page': 'bareme', 'regles': regles,
                           'isadmin': is_admin(request.user.id)})


@login_required
def candidats(request):
    current_userprofile = UserProfile.objects.filter(user_id=request.user.id).first()
    ligues = Membre.objects\
        .filter(user_id=current_userprofile.id).order_by('ligue__insert_datetime')\
        .values('id', 'ligue_id', 'ligue__nom')
    candidats = Candidat.objects.all().order_by('id')
    return render(request=request,
                  template_name="dkllapp/candidats.html",
                  context={'ligues': ligues, 'page': 'candidats', 'candidats': candidats,
                           'isadmin': is_admin(request.user.id)})


@login_required
def faq(request):
    current_userprofile = UserProfile.objects.filter(user_id=request.user.id).first()
    ligues = Membre.objects\
        .filter(user_id=current_userprofile.id).order_by('ligue__insert_datetime')\
        .values('id', 'ligue_id', 'ligue__nom')
    return render(request=request,
                  template_name="dkllapp/faq.html",
                  context={'ligues': ligues, 'page': 'faq',
                           'isadmin': is_admin(request.user.id)})


@login_required
def classement_general(request):
    current_userprofile = UserProfile.objects.filter(user_id=request.user.id).first()
    ligues = Membre.objects\
        .filter(user_id=current_userprofile.id).order_by('ligue__insert_datetime')\
        .values('id', 'ligue_id', 'ligue__nom')
    users = User.objects.all().order_by('id')
    users_a_classer = []
    for user in users:
        user_profile = UserProfile.objects.filter(user_id=user.id).first()
        max_points_user = 0
        ligue_max_points_user = ""
        ligues_user = Membre.objects.filter(user_id=user_profile.id)\
            .values('ligue_id')
        if ligues_user:
            for ligue in ligues_user:
                points = Points.objects.filter(user_id=user_profile.id).filter(ligue_id=ligue['ligue_id']) \
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
    membres_unsorted = []

    for user_membre in users_a_classer:
        user_membre_profile = UserProfile.objects.filter(user_id=user_membre[0]).first()
        membre_points = Points.objects.filter(user_id=user_membre_profile.id).filter(ligue_id=user_membre[1]) \
            .values('ligue_id', 'user_id') \
            .annotate(Sum('somme_points_poulains')) \
            .annotate(Sum('somme_points_podium')) \
            .annotate(Sum('somme_points_gagnant')) \
            .annotate(Sum('somme_points_selon_types'))
        membre_avec_points = {
            'id': user_membre[0],
            'ligue': Ligue.objects.filter(id=user_membre[1]).values('nom')[0]['nom'],
            'username': User.objects.filter(id=user_membre[0]).values('username')[0]['username'],
            'img': UserProfile.objects.filter(user_id=user_membre[0]).values('img')[0]['img'],
            'points_poulains': membre_points[0]['somme_points_poulains__sum'],
            'points_podium': membre_points[0]['somme_points_podium__sum'],
            'points_gagnant': membre_points[0]['somme_points_gagnant__sum'],
            'points_candidats': membre_points[0]['somme_points_selon_types__sum']}
        points_feu_user = PointsFeu.objects.values('user_id', 'feu').filter(user_id=user_membre_profile.id).order_by('user_id').first()
        if points_feu_user:
            membre_avec_points['points_feu'] = points_feu_user['feu']
            membre_avec_points['total'] = membre_avec_points['points_feu'] + membre_avec_points['points_candidats']
        else:
            membre_avec_points['points_feu'] = 0
            membre_avec_points['total'] = membre_avec_points['points_candidats']
        membres_unsorted.append(membre_avec_points)
    membres_sorted = sorted(membres_unsorted, key=lambda i: i['total'], reverse=True)
    rang = 1
    for joueur in membres_sorted:
        joueur['rang'] = rang
        rang = rang + 1
    membres_sorted_top10 = membres_sorted[:10]
    return render(request=request,
                  template_name="dkllapp/classement_general.html",
                  context={'ligues': ligues, 'page': 'classement_general', 'membres_sorted': membres_sorted_top10,
                           'isadmin': is_admin(request.user.id)})


@login_required
def stat_1(request):
    current_userprofile = UserProfile.objects.filter(user_id=request.user.id).first()
    ligues = Membre.objects\
        .filter(user_id=current_userprofile.id).order_by('ligue__insert_datetime')\
        .values('id', 'ligue_id', 'ligue__nom')
    statistiques = 'statistiques'
    return render(request=request,
                  template_name="dkllapp/stat_1.html",
                  context={'page': "stat_1", 'ligues': ligues,
                           'isadmin': is_admin(request.user.id)})


@login_required
def stat_2(request):
    current_userprofile = UserProfile.objects.filter(user_id=request.user.id).first()
    ligues = Membre.objects\
        .filter(user_id=current_userprofile.id).order_by('ligue__insert_datetime')\
        .values('id', 'ligue_id', 'ligue__nom')
    statistiques = 'statistiques'
    return render(request=request,
                  template_name="dkllapp/stat_2.html",
                  context={'page': "stat_2", 'ligues': ligues,
                           'isadmin': is_admin(request.user.id)})


@login_required
def stat_3(request):
    current_userprofile = UserProfile.objects.filter(user_id=request.user.id).first()
    ligues = Membre.objects\
        .filter(user_id=current_userprofile.id).order_by('ligue__insert_datetime')\
        .values('id', 'ligue_id', 'ligue__nom')
    statistiques = 'statistiques'
    return render(request=request,
                  template_name="dkllapp/stat_3.html",
                  context={'page': "stat_3", 'ligues': ligues,
                           'isadmin': is_admin(request.user.id)})


@login_required
def changer_identifiant(request, message):
    current_userprofile = UserProfile.objects.filter(user_id=request.user.id).first()
    ligues = Membre.objects\
        .filter(user_id=current_userprofile.id).order_by('ligue__insert_datetime')\
        .values('id', 'ligue_id', 'ligue__nom')
    current_user = User.objects.filter(id=request.user.id).first()
    if request.method == "POST":
        form = ChangerIdentifiantForm(request.POST)
        if form.is_valid():
            current_user.username = form.cleaned_data.get('new_username')
            try:
                current_user.save()
            except IntegrityError:
                message = "L'identifiant " + form.cleaned_data.get('new_username') + " est déjà utilisé"
                return redirect('dkllapp:changer_identifiant', message)
            message_profil = "L'identifiant a été mis à jour"
            return redirect('dkllapp:profil', message_profil)
    form = ChangerIdentifiantForm()
    return render(request=request,
                  template_name="dkllapp/changer_identifiant.html",
                  context={'ligues': ligues, 'form': form, 'current_user': current_user,
                           'message': message,
                           'isadmin': is_admin(request.user.id)})


@login_required
def changer_mdp(request, message):
    current_userprofile = UserProfile.objects.filter(user_id=request.user.id).first()
    ligues = Membre.objects\
        .filter(user_id=current_userprofile.id).order_by('ligue__insert_datetime')\
        .values('id', 'ligue_id', 'ligue__nom')
    current_user = User.objects.filter(id=request.user.id).first()
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            message_profil = "Le mot de passe a été mis à jour"
            return redirect('dkllapp:profil', message_profil)
        else:
            message = "Une erreur s'est produite, vérifie que tous les critères sont respectés."
            if request.POST['new_password1'] != request.POST['new_password2']:
                message = "Les champs ne sont pas identiques"
            else:
                if len(request.POST['new_password1']) > 8:
                    try:
                        test = int(form.cleaned_data.get('new_password1'))
                        message = "Le mot de passe ne doit pas être entièrement numérique"
                    except ValueError:
                        pass
                else:
                    message = "Le mot de passe doit faire au moins 9 caractères"
            return redirect('dkllapp:changer_mdp', message)
    else:
        form = PasswordChangeForm(request.user)
    return render(request=request,
                  template_name="dkllapp/changer_mdp.html",
                  context={'ligues': ligues, 'form': form, 'current_user': current_user,
                           'message': message,
                           'isadmin': is_admin(request.user.id)})


@login_required
def picto(request, txt_alert):
    current_userprofile = UserProfile.objects.filter(user_id=request.user.id).first()
    ligues = Membre.objects\
        .filter(user_id=current_userprofile.id).order_by('ligue__insert_datetime')\
        .values('id', 'ligue_id', 'ligue__nom')
    pictos = []
    new_fields = {}
    for i in range(1, 65):
        picto = "dkllapp/img/kitchen/png/" + "{:02d}".format(i) + ".png"
        pictos.append(picto)
        new_fields['pict_' + str(i)] = forms.BooleanField(required=False)
    DynamicPictoForm = type('DynamicPictoForm', (PictoForm,), new_fields)
    if request.method == "POST":
        form = DynamicPictoForm(request.POST)
        if form.is_valid():
            selected_picto = []
            for field in form.cleaned_data:
                if "pict_" in field and form.cleaned_data[field]:
                    selected_picto.append(int(field[5:7]))
            if 0 < len(selected_picto) < 2:
                current_userprofile.img = "dkllapp/img/kitchen/png/" + "{:02d}".format(int(selected_picto[0])) + ".png"
                current_userprofile.save()
                message_profil = "Le picto a été mis à jour"
                return redirect('dkllapp:profil', message_profil)
            else:
                txt_alert = "alert"
                return redirect('dkllapp:picto', txt_alert)
    form = DynamicPictoForm()
    return render(request=request,
                  template_name="dkllapp/picto.html",
                  context={'pictos': pictos, 'form': form, 'txt_alert': txt_alert, 'range64': list(range(1, 65)),
                           'isadmin': is_admin(request.user.id)})


@login_required
def creation_ligue(request):
    current_userprofile = UserProfile.objects.filter(user_id=request.user.id).first()
    ligues = Membre.objects\
        .filter(user_id=current_userprofile.id).order_by('ligue__insert_datetime')\
        .values('id', 'ligue_id', 'ligue__nom')
    user = User.objects.filter(id=request.user.id).first()
    if request.method == "POST":
        form = LigueCreationForm(request.POST)
        if form.is_valid():
            nouvelle_ligue = Ligue()
            nouvelle_ligue.nom = form.cleaned_data.get('nom')
            nouvelle_ligue.save()
            nouveau_membre = Membre()
            nouveau_membre.user_id = current_userprofile.id
            nouveau_membre.ligue_id = nouvelle_ligue.id
            nouveau_membre.save()
            #mail
            current_site = get_current_site(request)
            html_message = loader.render_to_string(
                'dkllapp/mails/topch_ligue.html',
                {
                    'user': user,
                    'message': 'Un mail',
                    'domain': current_site.domain,
                    'from_email': settings.EMAIL_HOST_USER,
                    'ligue_id': nouvelle_ligue.id,
                }
            )
            email_subject = "🌶️ Création de ta ligue Pili Pili"
            email_from = '🌶️ Brigade Pili² <pilixpiliapp@gmail.com>'
            recipient_list = [user.email]
            mail = EmailMultiAlternatives(
                email_subject, 'This is message', email_from, recipient_list)
            mail.attach_alternative(html_message, "text/html")
            mail.send()
            return redirect('dkllapp:mur', nouvelle_ligue.id)
    form = LigueCreationForm()
    return render(request=request,
                  template_name="dkllapp/creation_ligue.html",
                  context={'form': form, 'ligues': ligues,
                           'isadmin': is_admin(request.user.id)})


@login_required
def rejoindre_ligue(request, message):
    current_userprofile = UserProfile.objects.filter(user_id=request.user.id).first()
    ligues = Membre.objects\
        .filter(user_id=current_userprofile.id).order_by('ligue__insert_datetime')\
        .values('id', 'ligue_id', 'ligue__nom')
    message = message
    if request.method == "POST":
        form = LigueJoinForm(request.POST)
        if form.is_valid():
            try:
                ligue_a_rejoindre = Ligue.objects.filter(id=form.cleaned_data.get('ligue_id')).first()
            except ValidationError:
                message = "Code de la ligue incorrect"
                return redirect('dkllapp:rejoindre_ligue', message)
            if ligue_a_rejoindre:
                deja_membre = Membre.objects \
                    .filter(user_id=current_userprofile.id) \
                    .filter(ligue_id=ligue_a_rejoindre.id)
                if deja_membre:
                    pass
                else:
                    nouveau_membre = Membre()
                    nouveau_membre.user_id = current_userprofile.id
                    nouveau_membre.ligue_id = ligue_a_rejoindre.id
                    nouveau_membre.save()
                    return redirect('dkllapp:mur', ligue_a_rejoindre.id)
    form = LigueJoinForm()
    return render(request=request,
                  template_name="dkllapp/rejoindre_ligue.html",
                  context={'rejoindre_ligue': rejoindre_ligue, 'ligues': ligues, 'form': form,
                           'message': message,
                           'isadmin': is_admin(request.user.id)})


@login_required
def rejoindre_ligue_cgi(request, ligue_id):
    current_userprofile = UserProfile.objects.filter(user_id=request.user.id).first()
    ligue_a_rejoindre = Ligue.objects.filter(id=ligue_id).first()
    deja_membre = Membre.objects.filter(user_id=request.user.id).filter(ligue_id=ligue_a_rejoindre.id).first()
    if deja_membre:
        return redirect('dkllapp:mur', ligue_a_rejoindre.id)
    else:
        nouveau_membre = Membre()
        nouveau_membre.user_id = current_userprofile.id
        nouveau_membre.ligue_id = ligue_a_rejoindre.id
        nouveau_membre.save()
        return redirect('dkllapp:mur', ligue_a_rejoindre.id)


@login_required
def faire_equipe(request, ligue_id, before, txt):
    current_userprofile = UserProfile.objects.filter(user_id=request.user.id).first()
    ligues = Membre.objects\
        .filter(user_id=current_userprofile.id).order_by('ligue__insert_datetime')\
        .values('id', 'ligue_id', 'ligue__nom')
    current_ligue = Ligue.objects.filter(id=ligue_id).values('id', 'nom')[0]
    episode_en_cours_ = episode_en_cours()
    txt_alert = txt
    poulains = Choix.objects.filter(user_id=current_userprofile.id).filter(type=1).order_by('id')\
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
                        equipe_pour_une_ligue(request.user, ligue['ligue_id'], episode_en_cours_, selected_candidat)
                if before == "equipe":
                    return redirect('dkllapp:equipe', current_ligue['id'])
                else:
                    return redirect('dkllapp:index')
            else:
                txt_alert = "alert"
                return redirect('dkllapp:faire_equipe', current_ligue['id'], before, txt_alert)

    form = DynamicEquipeCreationForm()
    return render(request=request,
                  template_name="dkllapp/faire_equipe.html",
                  context={'form': form, 'ligues': ligues, 'poulains': poulains, 'txt_alert': txt_alert,
                           'isadmin': is_admin(request.user.id)})


def acme_challenge(request):
    return HttpResponse(settings.ACME_CHALLENGE_CONTENT)


######################################TESTS#################################################
############################################################################################

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
            user_push = get_object_or_404(User, pk=user_dkllapp.id)
            send_user_notification(user=user_push, payload=payload, ttl=1000)

        return JsonResponse(status=200, data={"message": "Web push successful"})
    except TypeError:
        return JsonResponse(status=500, data={"message": "An error occurred"})

"""
@login_required
def test_mail(request):
    current_user = request.user
    current_site = get_current_site(request)
    enonce = "Telle est la question ?"
    bonus = 4
    malus = -2
    html_message = loader.render_to_string(
        'dkllapp/mails/topch_prono.html',
        {
            'user': current_user,
            'domain': current_site.domain,
            'from_email': settings.EMAIL_HOST_USER,
            'enonce': enonce,
            'bonus': bonus,
            'malus': malus,
        }
    )
    email_subject = "🔥 Un nouveau prono est disponible !"
    email_from = '🌶️ Brigade Pili² <pilixpiliapp@gmail.com>'
    recipient_list = ['louise_gautier@orange.fr']
    mail = EmailMultiAlternatives(
        email_subject, 'This is message', email_from, recipient_list)
    mail.attach_alternative(html_message, "text/html")
    mail.send()
    return render(request=request,
                  template_name="dkllapp/test_mail.html",
                  context={'isadmin': is_admin(request.user.id)})

"""
