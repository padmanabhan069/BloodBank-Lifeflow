"""
REST API blueprint — AJAX donor search, stats, donor detail
"""
from flask import jsonify, request
from flask_login import login_required, current_user
from app.api import api
from app.models import DonorProfile, User, BloodRequest, BloodStock, Notification


@api.route('/donors/search')
@login_required
def search_donors():
    blood_group = request.args.get('blood_group', '')
    location = request.args.get('location', '')
    availability = request.args.get('availability', '')

    query = DonorProfile.query.join(User).filter(
        User.is_blocked == False
    )
    if blood_group:
        query = query.filter(DonorProfile.blood_group == blood_group)
    if location:
        query = query.filter(
            (DonorProfile.location.ilike(f'%{location}%')) |
            (DonorProfile.city.ilike(f'%{location}%'))
        )
    if availability == 'available':
        query = query.filter(DonorProfile.is_available == True)

    donors = query.order_by(DonorProfile.blood_rank_score.desc()).limit(50).all()

    return jsonify([{
        'id': d.id,
        'name': d.user.name,
        'blood_group': d.blood_group,
        'location': d.location or d.city or '',
        'is_available': d.is_available,
        'bmi': d.bmi,
        'total_donations': d.total_blood_donations,
        'days_until_eligible': d.blood_days_until_eligible,
        'is_platelet_donor': d.is_platelet_donor,
        'rank_score': d.blood_rank_score
    } for d in donors])


@api.route('/donors/<int:donor_id>')
@login_required
def donor_detail(donor_id):
    d = DonorProfile.query.get_or_404(donor_id)
    return jsonify({
        'id': d.id,
        'name': d.user.name,
        'blood_group': d.blood_group,
        'location': d.location,
        'phone': d.phone,
        'is_available': d.is_available,
        'bmi': d.bmi,
        'age': d.age,
        'gender': d.gender,
        'total_blood_donations': d.total_blood_donations,
        'total_platelet_donations': d.total_platelet_donations,
        'is_platelet_donor': d.is_platelet_donor,
        'days_until_eligible': d.blood_days_until_eligible,
    })


@api.route('/stats')
@login_required
def stats():
    total_donors = DonorProfile.query.count()
    available = DonorProfile.query.filter_by(is_available=True).count()
    active_requests = BloodRequest.query.filter_by(status='active').count()
    stock = {s.blood_group: s.units_available for s in BloodStock.query.all()}
    unread = Notification.query.filter_by(
        user_id=current_user.id, is_read=False).count()

    return jsonify({
        'total_donors': total_donors,
        'available': available,
        'active_requests': active_requests,
        'my_donations': len(current_user.donation_history),
        'unread_notifications': unread,
        'stock': stock
    })


@api.route('/notifications/unread-count')
@login_required
def unread_count():
    count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return jsonify({'count': count})


@api.route('/notifications/list')
@login_required
def notifications_list():
    """Return latest 20 notifications as JSON for the slide-in drawer."""
    from app import db
    notifs = (Notification.query
              .filter_by(user_id=current_user.id)
              .order_by(Notification.created_at.desc())
              .limit(20).all())
    # Mark all as read when drawer is opened
    for n in notifs:
        n.is_read = True
    db.session.commit()

    icon_map = {
        'request': 'exclamation-triangle-fill',
        'alert':   'megaphone-fill',
        'reminder':'clock-fill',
        'info':    'info-circle-fill',
    }
    color_map = {
        'request': '#EF4444',
        'alert':   '#F59E0B',
        'reminder':'#3B82F6',
        'info':    '#10B981',
    }

    return jsonify([{
        'id': n.id,
        'title': n.title,
        'message': n.message,
        'type': n.notif_type,
        'icon': icon_map.get(n.notif_type, 'info-circle-fill'),
        'color': color_map.get(n.notif_type, '#3B82F6'),
        'related_id': n.related_id,
        'time': n.created_at.strftime('%b %d, %I:%M %p'),
        'was_unread': not n.is_read,  # already marked read, original state captured
    } for n in notifs])

