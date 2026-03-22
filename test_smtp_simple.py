
import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()

def test_smtp():
    server = os.environ.get('MAIL_SERVER')
    port = int(os.environ.get('MAIL_PORT', 587))
    user = os.environ.get('MAIL_USERNAME')
    password = os.environ.get('MAIL_PASSWORD')
    sender = os.environ.get('MAIL_DEFAULT_SENDER')

    print(f"Server: {server}")
    print(f"Port: {port}")
    print(f"User: {user}")

    msg = EmailMessage()
    msg.set_content("This is a test email.")
    msg['Subject'] = "SMTP Test"
    msg['From'] = sender
    msg['To'] = user

    try:
        print("Connecting to server...")
        with smtplib.SMTP(server, port) as smtp:
            print("Starting TLS...")
            smtp.starttls()
            print("Logging in...")
            smtp.login(user, password)
            print("Sending email...")
            smtp.send_message(msg)
            print("SUCCESS!")
    except Exception as e:
        print(f"FAILURE: {e}")

if __name__ == "__main__":
    test_smtp()
