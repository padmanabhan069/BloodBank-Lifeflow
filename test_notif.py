from app import create_app, db
from app.models import User, DonorProfile, BloodRequest, Notification
from datetime import date, timedelta

def test_request_notification():
    app = create_app()
    with app.app_context():
        # Get a donor who is NOT the requester
        requester = User.query.filter_by(email='john@example.com').first()
        donor = User.query.filter_by(email='jane@example.com').first()
        
        if not requester or not donor:
            print("Users not found. Run seed_db.py first.")
            return
            
        print(f"Requester: {requester.name} ({requester.profile.blood_group})")
        print(f"Donor: {donor.name} ({donor.profile.blood_group})")
        
        # Create a request for O- (Jane's blood group)
        req = BloodRequest(
            user_id=requester.id,
            blood_group='O-',
            units=1,
            hospital='Test Hospital',
            location='Test Loc',
            need_date=date.today(),
            need_time='10:00',
            contact='123456',
            is_urgent=True
        )
        db.session.add(req)
        db.session.commit()
        print(f"Request created for O- (ID: {req.id})")
        
        # Manually trigger the notification logic (replicating what's in routes.py)
        matching = (DonorProfile.query.join(User)
                    .filter(DonorProfile.blood_group == req.blood_group,
                            DonorProfile.is_available == True,
                            DonorProfile.user_id != requester.id,
                            User.is_blocked == False).all())
        
        print(f"Found {len(matching)} matching donors.")
        for p in matching:
            print(f"Checking donor: {p.user.name} (Eligible days: {p.blood_days_until_eligible})")
            if p.blood_days_until_eligible == 0:
                from app.utils import send_in_app_notification
                send_in_app_notification(
                    p.user_id,
                    f'🚨 URGENT Blood Request — {req.blood_group}',
                    f'Blood needed at {req.hospital}',
                    notif_type='request', related_id=req.id
                )
                print(f"Notification sent to {p.user.name}")
        
        # Check if Jane has the notification
        notifs = Notification.query.filter_by(user_id=donor.id).order_by(Notification.created_at.desc()).all()
        print(f"Jane has {len(notifs)} notifications.")
        for n in notifs:
            print(f"- {n.title}: {n.message} (Type: {n.notif_type})")

if __name__ == '__main__':
    test_request_notification()
