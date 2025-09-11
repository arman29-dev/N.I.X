from smtplib import SMTP
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from .config import SENDER, SENDER_PASSWORD



def send_email(to: str, subject: str, body: str) -> tuple[bool, str]:
    try:
        msg = MIMEMultipart()
        msg['From'] = f"N.I.X System Service <{SENDER}>"
        msg['To'] = to
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'html'))

        with SMTP('smtp.gmail.com', 587) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(SENDER, SENDER_PASSWORD)
            server.send_message(msg)

        return True, 'Email sent successfully'

    except Exception as E:
        return False, f"SMTP Error: {str(E)}"
