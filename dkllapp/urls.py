from django.conf.urls.static import static
from django.template.defaulttags import url
from django.urls import path, include
from django.views.generic import TemplateView

from dkllapp import views
from dkllapp.views import send_push, home_push
from mysite import settings

app_name = 'dkllapp'
urlpatterns = [
    path('', views.index, name='index'),
    path('faire_equipe/<ligue_id>/<before>/<txt>', views.faire_equipe, name='faire_equipe'),
    path('choix/<type_choix>/<before>/<txt>', views.choix, name='choix'),

    path('admin/', views.admin, name='admin'),
    path('changer_episode/', views.changer_episode, name='changer_episode'),
    path('changer_equipe_tv/', views.changer_equipe_tv, name='changer_equipe_tv'),
    path('changer_statut/', views.changer_statut, name='changer_statut'),
    path('modifier_regle/<regle_id>/', views.modifier_regle, name='modifier_regle'),
    path('ajouter_evenement/', views.ajouter_evenement, name='ajouter_evenement'),
    path('ajouter_question/<question_id>/', views.ajouter_question, name='ajouter_question'),
    path('ajouter_reponse/<question_id>/', views.ajouter_reponse, name='ajouter_reponse'),

    path('mur/<ligue_id>/', views.mur, name='mur'),
    path('equipe/<ligue_id>/', views.equipe, name='equipe'),
    path('resultat/<ligue_id>/', views.resultat, name='resultat'),
    path('details/<ligue_id>/<selected_episode>/', views.details, name='details'),
    path('changer_nom_ligue/<ligue_id>', views.changer_nom_ligue, name='changer_nom_ligue'),

    path('pronos/<message>', views.pronos, name='pronos'),
    path('bonus/', views.bonus, name='bonus'),

    path('profil/<message>/', views.profil, name='profil'),
    path('ligues_user/', views.ligues_user, name='ligues_user'),
    path('candidats_user/', views.candidats_user, name='candidats_user'),
    path('picto/<txt_alert>/', views.picto, name='picto'),
    path('changer_identifiant/<message>', views.changer_identifiant, name='changer_identifiant'),
    path('changer_mdp/<message>', views.changer_mdp, name='changer_mdp'),
    path('creation_ligue/', views.creation_ligue, name='creation_ligue'),
    path('rejoindre_ligue/', views.rejoindre_ligue, name='rejoindre_ligue'),
    path('rejoindre_ligue_cgi/<ligue_id>', views.rejoindre_ligue_cgi, name='rejoindre_ligue_cgi'),

    path('generales/', views.generales, name='generales'),
    path('bareme/', views.bareme, name='bareme'),
    path('candidats/', views.candidats, name='candidats'),
    path('faq/', views.faq, name='faq'),
    path('classement_general/', views.classement_general, name='classement_general'),
    path('stat_1/', views.stat_1, name='stat_1'),
    path('stat_2/', views.stat_2, name='stat_2'),
    path('stat_3/', views.stat_3, name='stat_3'),

    path("register/<message>", views.register_request, name="register"),
    path("reinitialiser_mdp/<message>", views.reinitialiser_mdp, name="reinitialiser_mdp"),
    path("login/", views.login_request, name="login"),
    path("logout/", views.logout_request, name="logout"),

    path('account_activation_sent/', views.account_activation_sent, name='account_activation_sent'),
    path('activate/<uidb64>/<token>/', views.activate, name='activate'),

    url(r'^.well-known/acme-challenge/.*$', views.acme_challenge, name='acme-challenge'),

    path('home_push/', home_push),
    path('send_push', send_push),
    #path('webpush/', include('webpush.urls')),
    path('home_push/sw.js', TemplateView.as_view(template_name='dkllapp/sw.js', content_type='application/x-javascript'))

] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)