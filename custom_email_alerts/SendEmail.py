#!/usr/bin/python3

import smtplib
import os
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate
from email import encoders


class SendEmail(object):

    def __init__(self, settings):
        self.host = settings["mail"]["smtp"]["host"]
        self.port = settings["mail"]["smtp"]["port"]
        self.username = settings["mail"]["credentials"]["username"]
        self.password = settings["mail"]["credentials"]["password"]
        self.email_from = settings["mail"]["from"]
        self.email_to = settings["mail"]["to"]
        self.check = None

    def check_smtp_server(self):
        # Connect
        conn = smtplib.SMTP(self.host, self.port)
        # Check SMTP server reachable and ready
        self.check = conn.helo()
        # Disconnect
        conn.quit()
        # Check result
        if self.check[0] != 250:
            return False
        else:
            return True

    # https://stackoverflow.com/questions/3362600/how-to-send-email-attachments
    def send(self, subject, body, attachment=None):
        # Form the message content
        content = MIMEMultipart()
        content["Subject"] = subject
        content["From"] = self.email_from
        content["To"] = self.email_to
        content['Date'] = formatdate(localtime=True)
        content.attach(MIMEText(body, "html"))
        # Prepare attachment if present
        if attachment:
            part = MIMEBase('application', "octet-stream")
            with open(attachment, "rb") as f:
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', 'attachment; filename=%s' % os.path.basename(attachment))
            content.attach(part)
        # Send email
        conn = smtplib.SMTP(self.host, self.port)
        conn.starttls()
        conn.login(self.username, self.password)
        result = conn.sendmail(self.username, self.email_to, content.as_string())
        # Disconnect
        conn.quit()
        # Check result
        if not len(result):
            return True
        else:
            return False
