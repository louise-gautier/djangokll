# Generated by Django 3.2.5 on 2021-11-14 00:07

from django.conf import settings
import django.contrib.postgres.fields
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ActivationChoix',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nom', models.CharField(max_length=100)),
                ('etat', models.IntegerField(default=0)),
                ('insert_datetime', models.DateTimeField(blank=True, default=django.utils.timezone.now)),
            ],
        ),
        migrations.CreateModel(
            name='Candidat',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nom', models.CharField(max_length=128)),
                ('age', models.IntegerField(default=0)),
                ('description', models.CharField(max_length=999)),
                ('brigade', models.CharField(max_length=128)),
            ],
        ),
        migrations.CreateModel(
            name='Episode',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nom', models.CharField(max_length=100)),
                ('valeur', models.IntegerField(default=0)),
                ('insert_datetime', models.DateTimeField(blank=True, default=django.utils.timezone.now)),
            ],
        ),
        migrations.CreateModel(
            name='Ligue',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('nom', models.CharField(max_length=128)),
                ('insert_datetime', models.DateTimeField(blank=True, default=django.utils.timezone.now)),
            ],
        ),
        migrations.CreateModel(
            name='Quotidien',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('question', models.CharField(max_length=999)),
                ('propositions', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=999), size=None)),
                ('reponse', models.CharField(max_length=999)),
                ('episode', models.IntegerField(default=0)),
                ('bonus', models.IntegerField(default=0)),
                ('malus', models.IntegerField(default=0)),
                ('insert_datetime', models.DateTimeField(blank=True, default=django.utils.timezone.now)),
            ],
        ),
        migrations.CreateModel(
            name='Regle',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('contenu', models.CharField(max_length=128)),
                ('points_1', models.IntegerField(default=0)),
                ('points_2', models.IntegerField(default=0)),
                ('points_3', models.IntegerField(default=0)),
                ('insert_datetime', models.DateTimeField(blank=True, default=django.utils.timezone.now)),
            ],
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('img', models.CharField(default='dkllapp/img/kitchen/default.png', max_length=999)),
                ('boolemail', models.BooleanField(default=True)),
                ('email_confirmed', models.BooleanField(default=False)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Pronostic',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pronostic', models.CharField(max_length=999)),
                ('insert_datetime', models.DateTimeField(blank=True, default=django.utils.timezone.now)),
                ('quotidien', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, to='dkllapp.quotidien')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, to='dkllapp.userprofile')),
            ],
        ),
        migrations.CreateModel(
            name='Notif',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('message', models.CharField(max_length=999)),
                ('insert_datetime', models.DateTimeField(blank=True, default=django.utils.timezone.now)),
                ('ligue', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, to='dkllapp.ligue')),
            ],
        ),
        migrations.CreateModel(
            name='Mur',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('message', models.CharField(max_length=999)),
                ('insert_datetime', models.DateTimeField(blank=True, default=django.utils.timezone.now)),
                ('ligue', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, to='dkllapp.ligue')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, to='dkllapp.userprofile')),
            ],
        ),
        migrations.CreateModel(
            name='Membre',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ligue', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, to='dkllapp.ligue')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, to='dkllapp.userprofile')),
            ],
        ),
        migrations.CreateModel(
            name='Evenement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('episode', models.IntegerField(default=0)),
                ('typage', models.IntegerField(default=0)),
                ('insert_datetime', models.DateTimeField(blank=True, default=django.utils.timezone.now)),
                ('candidat', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, to='dkllapp.candidat')),
                ('regle', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, to='dkllapp.regle')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, to='dkllapp.userprofile')),
            ],
        ),
        migrations.CreateModel(
            name='Equipe',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('episode', models.IntegerField(default=0)),
                ('type', models.IntegerField(default=0)),
                ('candidat', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, to='dkllapp.candidat')),
                ('ligue', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, to='dkllapp.ligue')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, to='dkllapp.userprofile')),
            ],
        ),
        migrations.CreateModel(
            name='Coeur',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('coeur', models.BooleanField(default=False)),
                ('insert_datetime', models.DateTimeField(blank=True, default=django.utils.timezone.now)),
                ('mur', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, to='dkllapp.mur')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, to='dkllapp.userprofile')),
            ],
        ),
        migrations.CreateModel(
            name='Choix',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.IntegerField(default=0)),
                ('insert_datetime', models.DateTimeField(blank=True, default=django.utils.timezone.now)),
                ('candidat', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, to='dkllapp.candidat')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, to='dkllapp.userprofile')),
            ],
        ),
    ]
