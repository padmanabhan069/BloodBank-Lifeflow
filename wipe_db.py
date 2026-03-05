from app import create_app, db
from app.models import User, DonorProfile, BloodRequest, DonationHistory, PlateletDonation, Notification, EligibilityCheck, BloodStock, RequestResponse

app = create_app()
with app.app_context():
    # Delete in order of dependencies
    db.session.query(Notification).delete()
    db.session.query(DonationHistory).delete()
    db.session.query(PlateletDonation).delete()
    db.session.query(RequestResponse).delete()
    db.session.query(BloodRequest).delete()
    db.session.query(EligibilityCheck).delete()
    db.session.query(DonorProfile).delete()
    db.session.query(BloodStock).delete()
    db.session.query(User).delete()
    db.session.commit()
    print("All data wiped successfully.")
