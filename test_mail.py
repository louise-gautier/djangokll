import smtplib
from email.mime.text import MIMEText
from decouple import config

#send_mail(subject, message, email_from, recipient_list)


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


subject = "Test Email Pili"
body = "This is the body of the text message"
sender = "🌶️ Brigade Pili²"
recipients = ["louise_gautier@orange.fr", "louise2004gautier@gmail.com"]

smtp_send_email(subject, body, sender, recipients)
