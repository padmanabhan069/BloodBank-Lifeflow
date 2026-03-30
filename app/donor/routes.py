"""
Donor blueprint — profile, directory, availability toggle, QR, PDF, history, rankings
"""
from flask import render_template, redirect, url_for, flash, request, jsonify, send_file
from flask_login import login_required, current_user
from datetime import date
import io

from app.donor import donor
from app import db
from app.models import User, DonorProfile, BloodRequest, DonationHistory, PlateletDonation, Notification
from app.forms import ProfileUpdateForm, DonationRecordForm
from app.utils import calculate_bmi, generate_qr_code, generate_donor_pdf


@donor.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    profile = current_user.profile
    form = ProfileUpdateForm(obj=profile)
    if form.validate_on_submit():
        current_user.name = form.name.data
        if profile:
            profile.phone = form.phone.data
            profile.dob = form.dob.data
            profile.gender = form.gender.data
            profile.location = form.location.data
            profile.weight = form.weight.data
            profile.height = form.height.data
            profile.is_platelet_donor = form.platelet_willing.data
            profile.compute_rank_score()
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('donor.profile'))
    return render_template('donor/profile.html', form=form, profile=profile)


@donor.route('/toggle-availability', methods=['POST'])
@login_required
def toggle_availability():
    profile = current_user.profile
    if profile:
        profile.is_available = not profile.is_available
        db.session.commit()
        status = 'available' if profile.is_available else 'unavailable'
        return jsonify({'success': True, 'status': status, 'is_available': profile.is_available})
    return jsonify({'success': False}), 400


@donor.route('/directory')
@login_required
def directory():
    blood_group = request.args.get('blood_group', '')
    location = request.args.get('location', '')
    availability = request.args.get('availability', '')
    page = request.args.get('page', 1, type=int)

    query = DonorProfile.query.join(User).filter(
        User.is_blocked == False
    )

    if blood_group:
        query = query.filter(DonorProfile.blood_group == blood_group)
    if location:
        query = query.filter(DonorProfile.location.ilike(f'%{location}%'))
    if availability == 'available':
        query = query.filter(DonorProfile.is_available == True)
    elif availability == 'unavailable':
        query = query.filter(DonorProfile.is_available == False)

    donors = query.order_by(DonorProfile.blood_rank_score.desc()).paginate(
        page=page, per_page=12, error_out=False)

    from app.models import BLOOD_GROUPS
    return render_template('donor/directory.html', donors=donors,
                           blood_groups=BLOOD_GROUPS)


@donor.route('/donor/<int:donor_id>')
@login_required
def view_donor(donor_id):
    d = DonorProfile.query.get_or_404(donor_id)
    return render_template('donor/view_donor.html', d=d)


@donor.route('/history')
@login_required
def history():
    donations = DonationHistory.query.filter_by(
        user_id=current_user.id).order_by(DonationHistory.donation_date.desc()).all()
    profile = current_user.profile
    return render_template('donor/history.html', donations=donations, profile=profile)


@donor.route('/record-donation', methods=['GET', 'POST'])
@login_required
def record_donation():
    form = DonationRecordForm()
    if form.validate_on_submit():
        profile = current_user.profile
        donation = DonationHistory(
            user_id=current_user.id,
            donation_type=form.donation_type.data,
            donation_date=form.donation_date.data,
            location=form.location.data,
            blood_group=profile.blood_group if profile else None,
            notes=form.notes.data
        )
        db.session.add(donation)

        # Update profile dates & counts
        if profile:
            if form.donation_type.data == 'blood':
                profile.last_blood_donation = form.donation_date.data
                profile.total_blood_donations += 1
            else:
                profile.last_platelet_donation = form.donation_date.data
                profile.total_platelet_donations += 1
            profile.compute_rank_score()

        db.session.commit()
        flash('Donation recorded successfully!', 'success')
        return redirect(url_for('donor.history'))
    unread = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return render_template('donor/record_donation.html', form=form, unread=unread)


@donor.route('/rankings')
@login_required
def rankings():
    blood_leaders = (DonorProfile.query.join(User)
                     .filter(User.is_blocked == False)
                     .order_by(DonorProfile.total_blood_donations.desc())
                     .limit(10).all())
    platelet_leaders = (DonorProfile.query.join(User)
                        .filter(User.is_blocked == False,
                                DonorProfile.is_platelet_donor == True)
                        .order_by(DonorProfile.total_platelet_donations.desc())
                        .limit(10).all())
    unread = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return render_template('donor/rankings.html',
                           blood_leaders=blood_leaders,
                           platelet_leaders=platelet_leaders,
                           unread=unread)


@donor.route('/platelet')
@login_required
def platelet():
    platelet_donors = (DonorProfile.query.join(User)
                       .filter(DonorProfile.is_platelet_donor == True,
                               User.is_blocked == False)
                       .order_by(DonorProfile.platelet_rank_score.desc()).all())
    profile = current_user.profile
    return render_template('donor/platelet.html',
                           platelet_donors=platelet_donors,
                           profile=profile)


@donor.route('/toggle-platelet', methods=['POST'])
@login_required
def toggle_platelet():
    profile = current_user.profile
    if profile:
        profile.is_platelet_donor = not profile.is_platelet_donor
        db.session.commit()
        return jsonify({'success': True, 'is_platelet_donor': profile.is_platelet_donor})
    return jsonify({'success': False}), 400


@donor.route('/qr-code')
@login_required
def qr_code():
    profile_url = url_for('donor.view_donor', donor_id=current_user.profile.id, _external=True)
    qr_bytes = generate_qr_code(profile_url)
    return send_file(io.BytesIO(qr_bytes), mimetype='image/png',
                     download_name=f'donor-qr-{current_user.id}.png')


@donor.route('/download-report')
@login_required
def download_report():
    profile = current_user.profile
    pdf_bytes = generate_donor_pdf(current_user, profile)
    if not pdf_bytes:
        flash('Could not generate PDF. Please try again.', 'danger')
        return redirect(url_for('donor.profile'))
    return send_file(io.BytesIO(pdf_bytes), mimetype='application/pdf',
                     download_name=f'donor-report-{current_user.id}.pdf',
                     as_attachment=True)
