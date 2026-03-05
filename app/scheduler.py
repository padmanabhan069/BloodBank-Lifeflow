"""
Background scheduler for donor eligibility reminders (APScheduler)
"""
from apscheduler.schedulers.background import BackgroundScheduler
import atexit


def send_eligibility_reminders(app):
    """Check donors and send reminder notifications when cooldown is over."""
    with app.app_context():
        from datetime import date
        from app import db
        from app.models import DonorProfile, User, Notification

        today = date.today()
        profiles = DonorProfile.query.filter_by(is_available=True).all()

        for profile in profiles:
            user = profile.user
            if not user or user.is_blocked:
                continue

            # Blood donation reminder
            if profile.last_blood_donation:
                from datetime import timedelta
                eligible_date = profile.last_blood_donation + timedelta(days=90)
                if eligible_date == today:
                    already_notified = Notification.query.filter_by(
                        user_id=user.id, notif_type='reminder'
                    ).filter(
                        Notification.title.contains('Blood')
                    ).filter(
                        db.func.date(Notification.created_at) == today
                    ).first()

                    if not already_notified:
                        n = Notification(
                            user_id=user.id,
                            title='🩸 Blood Donation Reminder',
                            message='You are now eligible to donate blood again! '
                                    'Visit your nearest blood bank.',
                            notif_type='reminder'
                        )
                        db.session.add(n)

            # Platelet donation reminder
            if profile.is_platelet_donor and profile.last_platelet_donation:
                from datetime import timedelta
                eligible_date = profile.last_platelet_donation + timedelta(days=30)
                if eligible_date == today:
                    already_notified = Notification.query.filter_by(
                        user_id=user.id, notif_type='reminder'
                    ).filter(
                        Notification.title.contains('Platelet')
                    ).filter(
                        db.func.date(Notification.created_at) == today
                    ).first()

                    if not already_notified:
                        n = Notification(
                            user_id=user.id,
                            title='🔬 Platelet Donation Reminder',
                            message='You are now eligible to donate platelets again! '
                                    'Schedule your donation today.',
                            notif_type='reminder'
                        )
                        db.session.add(n)

        db.session.commit()


def auto_expire_requests(app):
    """Auto-close blood requests whose need_date has passed."""
    with app.app_context():
        from datetime import date
        from app import db
        from app.models import BloodRequest
        expired = BloodRequest.query.filter(
            BloodRequest.status == 'active',
            BloodRequest.need_date < date.today()
        ).all()
        for req in expired:
            req.status = 'expired'
        if expired:
            db.session.commit()
            print(f'⏰ Auto-expired {len(expired)} blood request(s).')


def start_scheduler(app):
    """Start APScheduler to run reminders and expiry daily at 8 AM."""
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=lambda: send_eligibility_reminders(app),
        trigger='cron',
        hour=8,
        minute=0,
        id='eligibility_reminder'
    )
    scheduler.add_job(
        func=lambda: auto_expire_requests(app),
        trigger='cron',
        hour=0,
        minute=5,
        id='auto_expire_requests'
    )
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown())
