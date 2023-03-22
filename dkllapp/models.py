import uuid
from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.timezone import now
from django.contrib.auth.models import User


User._meta.get_field('email')._unique = True
User._meta.get_field('username')._unique = True


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    img = models.CharField(max_length=999, default='dkllapp/img/kitchen/default.png')
    boolemail = models.BooleanField(default=True)
    email_confirmed = models.BooleanField(default=False)


@receiver(post_save, sender=User)
def update_user_profile(sender, instance, created, **kwargs):
    if created:
        #UserProfile.objects.create(user=instance, id=User.id)
        p = UserProfile(user=kwargs["instance"])
        p.save()
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
    insert_datetime = models.DateTimeField(default=now, blank=True)


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
    parent = models.ForeignKey('Mur', on_delete=models.CASCADE, blank=True, null=True)
    insert_datetime = models.DateTimeField(default=now, blank=True)
    last_modified = models.DateTimeField(default=now, blank=True)


class Notif(models.Model):
    message = models.CharField(max_length=999)
    lien = models.CharField(max_length=999, default="")
    insert_datetime = models.DateTimeField(default=now, blank=True)


class Coeur(models.Model):
    mur = models.ForeignKey('Mur', on_delete=models.RESTRICT)
    user = models.ForeignKey('UserProfile', on_delete=models.RESTRICT)
    coeur = models.BooleanField(default=False)
    insert_datetime = models.DateTimeField(default=now, blank=True)


class Question(models.Model):
    enonce = models.CharField(max_length=999)
    episode = models.IntegerField(default=0)
    bonus = models.IntegerField(default=0)
    malus = models.IntegerField(default=0)
    insert_datetime = models.DateTimeField(default=now, blank=True)


class Proposition(models.Model):
    question = models.ForeignKey('Question', on_delete=models.RESTRICT)
    texte = models.CharField(max_length=999)
    pertinence = models.BooleanField(default=False)
    insert_datetime = models.DateTimeField(default=now, blank=True)


class Guess(models.Model):
    user = models.ForeignKey('UserProfile', on_delete=models.RESTRICT)
    question = models.ForeignKey('Question', on_delete=models.RESTRICT)
    proposition = models.ForeignKey('Proposition', on_delete=models.RESTRICT)
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


class PointsFeu(models.Model):
    user_id = models.IntegerField(default=0)
    feu = models.IntegerField(default=0)

    class Meta:
        managed = False
        db_table = "dkllapp_points_feu"


class EquipesFaites(models.Model):
    user_id = models.IntegerField(default=0)
    ligue_id = models.IntegerField(default=0)
    episode = models.IntegerField(default=0)
    count = models.IntegerField(default=0)

    class Meta:
        managed = False
        db_table = "dkllapp_equipes_faites"


class Media(models.Model):
    TYPES = [('url', 'URL'), ('image', 'Image'), ('video', 'Video Clip')]
    type = models.CharField(max_length=100, verbose_name='Type', choices=TYPES)
    url = models.CharField(max_length=255, verbose_name='Media URL')
    text = models.TextField(verbose_name='Parsed media text')

    class Meta:
        verbose_name = 'Media'
        verbose_name_plural = 'Media'

    def __str__(self):
        return self.url

    def __unicode__(self):
        return self.url


class Blip(models.Model):
    TYPES = [('f', 'Friends'), ('d', 'All from my department'), ('a', 'All users'),
             ('p', 'Private message')]
    message = models.TextField(verbose_name='Message')
    author = models.ForeignKey(User, verbose_name='Author', related_name='author',  on_delete=models.CASCADE)
    in_reply_to = models.ForeignKey('self', verbose_name='Reply to blip', blank=True, null=True,  on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)
    media = models.ManyToManyField(Media, verbose_name='Media', blank=True, null=True)

    class Meta:
        verbose_name = 'Blip'
        verbose_name_plural = 'Blips'

    def __str__(self):
        return self.message

    def __unicode__(self):
        return self.message
