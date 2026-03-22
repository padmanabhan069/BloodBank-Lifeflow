
import os
from flask import Flask
from flask_mail import Mail, Message
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', '').strip()
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', '').strip() == 'True'
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', '').strip()
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '').strip()
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', '').strip()

mail = Mail(app)

print(f"Testing mail with Server: {app.config['MAIL_SERVER']}, User: {app.config['MAIL_USERNAME']}")

with app.app_context():
    msg = Message(
        subject='BloodLife — Mail Connection Test',
        recipients=[app.config['MAIL_USERNAME']], # Send to self
        body='If you see this, your Flask-Mail configuration is working correctly!'
    )
    try:
        mail.send(msg)
        with open('mail_debug_output.txt', 'w') as f:
            f.write("SUCCESS: Email sent successfully!")
        print("SUCCESS: Email sent successfully!")
    except Exception as e:
        import traceback
        err_msg = f"FAILED: Email could not be sent. Error Type: {type(e).__name__}\nError Message: {str(e)}\n{traceback.format_exc()}"
        with open('mail_debug_output.txt', 'w') as f:
            f.write(err_msg)
        print("FAILED: Check mail_debug_output.txt for details")
