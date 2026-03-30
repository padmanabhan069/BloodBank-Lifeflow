"""
Main blueprint routes — dashboard, landing
"""
from flask import render_template, redirect, url_for
from flask_login import login_required, current_user
from app.main import main
from app.models import User, DonorProfile, BloodRequest, BloodStock, Notification


@main.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))


@main.route('/dashboard')
@login_required
def dashboard():
    profile = current_user.profile
    total_donors = DonorProfile.query.count()
    available_donors = DonorProfile.query.filter_by(is_available=True).count()
    active_requests = BloodRequest.query.filter_by(status='active').count()
    my_donations = len(current_user.donation_history)

    # Blood group inventory
    stock = {s.blood_group: s.units_available for s in BloodStock.query.all()}

    # Donor counts per blood group
    from app.models import BLOOD_GROUPS
    bg_counts = {}
    for bg in BLOOD_GROUPS:
        bg_counts[bg] = DonorProfile.query.filter_by(blood_group=bg, is_available=True).count()

    # Recent donors (new registrations)
    donors = (DonorProfile.query
              .join(User)
              .filter(User.is_blocked == False)
              .order_by(DonorProfile.updated_at.desc())
              .limit(9).all())

    # Show eligibility modal only once — right after a new account is created
    from flask import session as flask_session
    show_eligibility_modal = flask_session.pop('show_eligibility_modal', False)

    return render_template('donor/dashboard.html',
                           profile=profile,
                           total_donors=total_donors,
                           available_donors=available_donors,
                           active_requests=active_requests,
                           my_donations=my_donations,
                           stock=stock,
                           bg_counts=bg_counts,
                           donors=donors,
                           show_eligibility_modal=show_eligibility_modal)
