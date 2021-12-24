import uuid
from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.timezone import now
from django.contrib.postgres.fields import ArrayField


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    img = models.CharField(max_length=999, default='dkllapp/img/kitchen/default.png')
    boolemail = models.BooleanField(default=True)
    email_confirmed = models.BooleanField(default=False)


@receiver(post_save, sender=User)
def update_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
    instance.userprofile.save()


class Candidat(models.Model):
    nom = models.CharField(max_length=128)
    age = models.IntegerField(default=0)
    description = models.CharField(max_length=999)
    equipe_tv = models.CharField(max_length=128)
    statut = models.CharField(max_length=128)
    statut_bool = models.BooleanField(default=True)
    form_id = models.CharField(max_length=128)
    chemin_img = models.CharField(max_length=128)


class Ligue(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField(max_length=128)
    insert_datetime = models.DateTimeField(default=now, blank=True)


class Choix(models.Model):
    user = models.ForeignKey('UserProfile', on_delete=models.RESTRICT)
    candidat = models.ForeignKey('Candidat', on_delete=models.RESTRICT)
    type = models.IntegerField(default=0)
    insert_datetime = models.DateTimeField(default=now, blank=True)


class Regle(models.Model):
    contenu = models.CharField(max_length=128)
    points_1 = models.IntegerField(default=0)
    points_2 = models.IntegerField(default=0)
    points_3 = models.IntegerField(default=0)
    insert_datetime = models.DateTimeField(default=now, blank=True)


class Evenement(models.Model):
    user = models.ForeignKey('UserProfile', on_delete=models.RESTRICT)
    regle = models.ForeignKey('Regle', on_delete=models.RESTRICT)
    candidat = models.ForeignKey('Candidat', on_delete=models.RESTRICT)
    episode = models.IntegerField(default=0)
    typage = models.IntegerField(default=0)
    insert_datetime = models.DateTimeField(default=now, blank=True)


class Membre(models.Model):
    user = models.ForeignKey('UserProfile', on_delete=models.RESTRICT)
    ligue = models.ForeignKey('Ligue', on_delete=models.RESTRICT)


class Equipe(models.Model):
    user = models.ForeignKey('UserProfile', on_delete=models.RESTRICT)
    ligue = models.ForeignKey('Ligue', on_delete=models.RESTRICT)
    episode = models.IntegerField(default=0)
    candidat = models.ForeignKey('Candidat', on_delete=models.RESTRICT)
    type = models.IntegerField(default=0)
    insert_datetime = models.DateTimeField(default=now, blank=True)


class Mur(models.Model):
    ligue = models.ForeignKey('Ligue', on_delete=models.RESTRICT)
    user = models.ForeignKey('UserProfile', on_delete=models.RESTRICT)
    message = models.CharField(max_length=999)
    insert_datetime = models.DateTimeField(default=now, blank=True)


class Notif(models.Model):
    message = models.CharField(max_length=999)
    insert_datetime = models.DateTimeField(default=now, blank=True)


class Coeur(models.Model):
    mur = models.ForeignKey('Mur', on_delete=models.RESTRICT)
    user = models.ForeignKey('UserProfile', on_delete=models.RESTRICT)
    coeur = models.BooleanField(default=False)
    insert_datetime = models.DateTimeField(default=now, blank=True)


class Quotidien(models.Model):
    question = models.CharField(max_length=999)
    propositions = ArrayField(models.CharField(max_length=999))
    reponse = models.CharField(max_length=999)
    episode = models.IntegerField(default=0)
    bonus = models.IntegerField(default=0)
    malus = models.IntegerField(default=0)
    insert_datetime = models.DateTimeField(default=now, blank=True)


class Pronostic(models.Model):
    user = models.ForeignKey('UserProfile', on_delete=models.RESTRICT)
    quotidien = models.ForeignKey('Quotidien', on_delete=models.RESTRICT)
    pronostic = models.CharField(max_length=999)
    insert_datetime = models.DateTimeField(default=now, blank=True)


class Episode(models.Model):
    nom = models.CharField(max_length=100)
    valeur = models.IntegerField(default=0)
    insert_datetime = models.DateTimeField(default=now, blank=True)


class ActivationChoix(models.Model):
    nom = models.CharField(max_length=100)
    etat = models.IntegerField(default=0)
    insert_datetime = models.DateTimeField(default=now, blank=True)


class Points(models.Model):
    ligue_id = models.CharField(max_length=100)
    user_id = models.IntegerField(default=0)
    type = models.IntegerField(default=0)
    candidat_id = models.IntegerField(default=0)
    regle_id = models.IntegerField(default=0)
    episode = models.IntegerField(default=0)
    typage = models.IntegerField(default=0)
    points_1 = models.IntegerField(default=0)
    points_2 = models.IntegerField(default=0)
    points_3 = models.IntegerField(default=0)
    somme_points_poulains = models.IntegerField(default=0)
    somme_points_podium = models.IntegerField(default=0)
    somme_points_gagnant = models.IntegerField(default=0)
    somme_points_selon_types = models.IntegerField(default=0)

    class Meta:
        managed = False
        db_table = "dkllapp_points"
