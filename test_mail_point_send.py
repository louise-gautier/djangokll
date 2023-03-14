import os

from django.template import loader
from django.template.loader import render_to_string
from django.core.mail import send_mail, EmailMultiAlternatives
from decouple import config
import codecs

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
f = codecs.open("test_mail.html", 'r')
html_message = str(f.read())
email_subject = "🌶️🌶️ Bienvenue sur Pili Pili"
email_from = '🌶️ Brigade Pili² <pilixpiliapp@gmail.com>'
recipient_list = ["louise2004gautier@gmail.com"]
mail = EmailMultiAlternatives(
    email_subject, 'This is message', email_from, recipient_list)
mail.attach_alternative(html_message, "text/html")
mail.send()
