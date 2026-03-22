"""
Requests blueprint — blood request CRUD, accept/decline, notifications
"""
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.requests_bp import requests
from app import db
from app.models import BloodRequest, RequestResponse, Notification, DonorProfile, User
from app.forms import BloodRequestForm
from app.utils import send_in_app_notification, send_request_notification_email, get_compatible_blood_groups


@requests.route('/', methods=['GET', 'POST'])
@login_required
def index():
    form = BloodRequestForm()
    if form.validate_on_submit():
        req = BloodRequest(
            user_id=current_user.id,
            blood_group=form.blood_group.data,
            units=form.units.data,
            hospital=form.hospital.data,
            location=form.location.data,
            need_date=form.need_date.data,
            need_time=form.need_time.data,
            contact=form.contact.data,
            notes=form.notes.data,
            is_urgent=form.is_urgent.data
        )
        db.session.add(req)
        db.session.flush()

        # Notify only donors whose blood group is compatible with the requested blood group
        compatible_groups = get_compatible_blood_groups(req.blood_group)
        matching = (DonorProfile.query.join(User)
                    .filter(DonorProfile.is_available == True,
                            DonorProfile.blood_group.in_(compatible_groups),
                            DonorProfile.user_id != current_user.id,
                            User.is_blocked == False).all())

        notified = 0
        for p in matching:
            send_in_app_notification(
                p.user_id,
                f'🚨 {"URGENT " if req.is_urgent else ""}Blood Request — {req.blood_group}',
                f'{req.blood_group} blood needed at {req.hospital} on {req.need_date}. '
                f'Your blood group ({p.blood_group}) is compatible. Are you available?',
                notif_type='request', related_id=req.id
            )
            send_request_notification_email(p.user, req)
            notified += 1
        
        # Confirmation for the requester
        send_in_app_notification(
            current_user.id,
            '✅ Blood Request Submitted',
            f'Your request for {req.blood_group} blood at {req.hospital} has been posted. {notified} donor(s) alerted.',
            notif_type='info', related_id=req.id
        )

        db.session.commit()
        flash(f'Request submitted! {notified} donor(s) alerted.', 'success')
        return redirect(url_for('requests.index'))

    active = BloodRequest.query.filter_by(status='active').order_by(
        BloodRequest.created_at.desc()).all()
    return render_template('requests/index.html', form=form, active_requests=active)


@requests.route('/<int:req_id>')
@login_required
def view_request(req_id):
    req = BloodRequest.query.get_or_404(req_id)
    my_response = RequestResponse.query.filter_by(
        request_id=req_id, donor_id=current_user.id).first()
    return render_template('requests/view.html', req=req, my_response=my_response)


@requests.route('/<int:req_id>/respond', methods=['POST'])
@login_required
def respond(req_id):
    req = BloodRequest.query.get_or_404(req_id)
    action = request.form.get('action')   # 'accept' or 'decline'
    if action not in ('accept', 'decline'):
        return jsonify({'success': False, 'message': 'Invalid action'}), 400

    existing = RequestResponse.query.filter_by(request_id=req_id,
                                               donor_id=current_user.id).first()
    previous_action = existing.action if existing else None
    if existing:
        existing.action = action
    else:
        existing = RequestResponse(request_id=req_id, donor_id=current_user.id, action=action)
        db.session.add(existing)

    if action == 'accept' and previous_action != 'accept':
        # Update emergency responses count
        p = current_user.profile
        if p:
            p.emergency_responses += 1
            p.compute_rank_score()

        # Notify requester
        send_in_app_notification(
            req.user_id,
            '✅ Donor Available',
            f'{current_user.name} (BG: {p.blood_group if p else "N/A"}) is available for your request.',
            notif_type='info', related_id=req_id
        )

        # Notify all admins (as requested: "admin will recieve their details")
        admins = User.query.filter_by(role='admin').all()
        for admin in admins:
            if admin.id != current_user.id:
                send_in_app_notification(
                    admin.id,
                    '📢 Donor Available for Blood Request',
                    f'Donor {current_user.name} ({current_user.email}) is available for {req.blood_group} request at {req.hospital}. Phone: {p.phone if p else "N/A"}',
                    notif_type='alert', related_id=req_id
                )

    db.session.commit()
    flash(f'Thank you for responding!', 'success')
    return redirect(url_for('requests.view_request', req_id=req_id))


@requests.route('/notifications')
@login_required
def notifications():
    notifs = (Notification.query.filter_by(user_id=current_user.id)
              .order_by(Notification.created_at.desc()).all())
    # Mark all as read
    for n in notifs:
        n.is_read = True
    db.session.commit()
    return render_template('requests/notifications.html', notifications=notifs,
                           unread=0)


@requests.route('/notifications/mark-read/<int:notif_id>', methods=['POST'])
@login_required
def mark_read(notif_id):
    n = Notification.query.filter_by(id=notif_id, user_id=current_user.id).first_or_404()
    n.is_read = True
    db.session.commit()
    return jsonify({'success': True})
