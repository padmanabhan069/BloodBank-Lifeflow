from dotenv import load_dotenv
load_dotenv()

from app import create_app, db
from app.models import User, DonorProfile, BloodRequest, DonationHistory
from app.models import PlateletDonation, Notification, EligibilityCheck
from app.utils import create_sample_data

app = create_app()


@app.shell_context_processor
def make_shell_context():
    """Expose models in flask shell for debugging."""
    return {
        'db': db,
        'User': User,
        'DonorProfile': DonorProfile,
        'BloodRequest': BloodRequest,
        'DonationHistory': DonationHistory,
        'PlateletDonation': PlateletDonation,
        'Notification': Notification,
        'EligibilityCheck': EligibilityCheck,
    }


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # create_sample_data()   # Disabled to keep database empty
    app.run(debug=True, port=5000)
