from django.conf.urls import url
from django.conf.urls.static import static
from django.urls import path, include

# Centralisation des def de views avec attribution de l'url
# C'est l'equivalent des décorateurs dans routes en Flask
from django.views.generic import TemplateView

from dkllapp import views
from dkllapp.views import send_push, home_push, home_mail
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

    path('pronos/', views.pronos, name='pronos'),
    path('pronos_cgi/<question_id>/<proposition_id>', views.pronos_cgi, name='pronos_cgi'),
    path('bonus/', views.bonus, name='bonus'),

    path('profil/', views.profil, name='profil'),
    path('picto/<txt_alert>/', views.picto, name='picto'),
    path('nouveau_login/', views.nouveau_login, name='nouveau_login'),
    path('nouveau_mdp/', views.nouveau_mdp, name='nouveau_mdp'),
    path('creation_ligue/', views.creation_ligue, name='creation_ligue'),
    path('rejoindre_ligue/', views.rejoindre_ligue, name='rejoindre_ligue'),

    path('generales/', views.generales, name='generales'),
    path('bareme/', views.bareme, name='bareme'),
    path('candidats/', views.candidats, name='candidats'),
    path('faq/', views.faq, name='faq'),
    path('classement_general/', views.classement_general, name='classement_general'),
    path('statistiques/', views.statistiques, name='statistiques'),

    path("register/", views.register_request, name="register"),
    path("login/", views.login_request, name="login"),
    path("logout/", views.logout_request, name="logout"),

    path('account_activation_sent/', views.account_activation_sent, name='account_activation_sent'),
    path('activate/<uidb64>/<token>/', views.activate, name='activate'),

    path('home_push/', home_push),
    path('send_push', send_push),
    path('webpush/', include('webpush.urls')),
    path('home_mail/', home_mail),
    path('home_push/sw.js', TemplateView.as_view(template_name='dkllapp/sw.js', content_type='application/x-javascript'))

] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
