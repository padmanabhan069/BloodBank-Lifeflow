"""
Admin blueprint — user management, blood stock, analytics
"""
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from functools import wraps
from app.admin import admin
from app import db
from app.models import (User, DonorProfile, BloodRequest, DonationHistory,
                        BloodStock, Notification, RequestResponse, BLOOD_GROUPS)
from app.forms import BloodStockUpdateForm


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Admin access required.', 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated


@admin.route('/')
@login_required
@admin_required
def index():
    total_users = User.query.count()
    active_requests = BloodRequest.query.filter_by(status='active').count()
    total_donations = DonationHistory.query.count()
    from datetime import date
    this_month = DonationHistory.query.filter(
        db.func.strftime('%Y-%m', DonationHistory.donation_date) ==
        date.today().strftime('%Y-%m')
    ).count()
    return render_template('admin/dashboard.html',
                           total_users=total_users,
                           active_requests=active_requests,
                           total_donations=total_donations,
                           this_month=this_month)


@admin.route('/users')
@login_required
@admin_required
def manage_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users)


@admin.route('/users/<int:user_id>/toggle-block', methods=['POST'])
@login_required
@admin_required
def toggle_block(user_id):
    user = User.query.get_or_404(user_id)
    if user.is_admin:
        return jsonify({'success': False, 'message': 'Cannot block admin'}), 400
    user.is_blocked = not user.is_blocked
    db.session.commit()
    action = 'blocked' if user.is_blocked else 'unblocked'
    return jsonify({'success': True, 'action': action, 'is_blocked': user.is_blocked})


@admin.route('/requests')
@login_required
@admin_required
def view_requests():
    from datetime import date
    reqs = BloodRequest.query.order_by(BloodRequest.created_at.desc()).all()
    return render_template('admin/requests.html', requests=reqs, today=date.today())


@admin.route('/requests/<int:req_id>/close', methods=['POST'])
@login_required
@admin_required
def close_request(req_id):
    req = BloodRequest.query.get_or_404(req_id)
    req.status = 'closed'
    db.session.commit()
    flash('Request closed.', 'success')
    return redirect(url_for('admin.view_requests'))


@admin.route('/requests/<int:req_id>/fulfill', methods=['POST'])
@login_required
@admin_required
def fulfill_request(req_id):
    """Mark request as fulfilled after a donor has donated."""
    req = BloodRequest.query.get_or_404(req_id)
    req.status = 'fulfilled'
    db.session.commit()
    # Notify the requester
    from app.utils import send_in_app_notification
    send_in_app_notification(
        req.user_id,
        '🎉 Blood Request Fulfilled!',
        f'Your {req.blood_group} blood request at {req.hospital} has been marked as fulfilled by the admin. Thank you!',
        notif_type='info', related_id=req_id
    )
    flash('Request marked as fulfilled!', 'success')
    return redirect(url_for('admin.view_requests'))


@admin.route('/requests/expire', methods=['POST'])
@login_required
@admin_required
def expire_requests():
    """Manually trigger expiry of past-date active requests."""
    from datetime import date
    expired = BloodRequest.query.filter(
        BloodRequest.status == 'active',
        BloodRequest.need_date < date.today()
    ).all()
    count = 0
    for req in expired:
        req.status = 'expired'
        count += 1
    db.session.commit()
    flash(f'{count} expired request(s) auto-closed.', 'success')
    return redirect(url_for('admin.view_requests'))


@admin.route('/requests/<int:req_id>/donors')
@login_required
@admin_required
def request_donors(req_id):
    """Admin panel: view all donors who responded to a specific request."""
    req = BloodRequest.query.get_or_404(req_id)
    accepted = [r for r in req.responses if r.action == 'accept']
    declined = [r for r in req.responses if r.action == 'decline']
    return render_template('admin/request_donors.html',
                           req=req, accepted=accepted, declined=declined)


@admin.route('/inventory', methods=['GET', 'POST'])
@login_required
@admin_required
def inventory():
    form = BloodStockUpdateForm()
    stocks = {s.blood_group: s for s in BloodStock.query.all()}
    if form.validate_on_submit():
        bg = form.blood_group.data
        if bg in stocks:
            stocks[bg].units_available = form.units.data
            stocks[bg].updated_by = current_user.id
        else:
            new_stock = BloodStock(blood_group=bg, units_available=form.units.data,
                                   updated_by=current_user.id)
            db.session.add(new_stock)
        db.session.commit()
        flash(f'{bg} stock updated to {form.units.data} units.', 'success')
        return redirect(url_for('admin.inventory'))
    return render_template('admin/inventory.html', form=form, stocks=stocks,
                           blood_groups=BLOOD_GROUPS)


@admin.route('/analytics')
@login_required
@admin_required
def analytics():
    return render_template('admin/analytics.html')


@admin.route('/analytics/data')
@login_required
@admin_required
def analytics_data():
    """JSON endpoint for Chart.js charts."""
    from datetime import date
    from collections import Counter

    # Monthly donations over last 6 months
    donations = DonationHistory.query.all()
    months = {}
    for d in donations:
        key = d.donation_date.strftime('%b %Y')
        months[key] = months.get(key, 0) + 1

    # Blood group distribution
    bg_dist = {}
    for p in DonorProfile.query.all():
        if p.blood_group:
            bg_dist[p.blood_group] = bg_dist.get(p.blood_group, 0) + 1

    # Monthly requests
    req_months = {}
    for r in BloodRequest.query.all():
        key = r.created_at.strftime('%b %Y')
        req_months[key] = req_months.get(key, 0) + 1

    # Top donors
    top = (DonorProfile.query.join(User)
           .order_by(DonorProfile.blood_rank_score.desc()).limit(5).all())
    top_names = [p.user.name for p in top]
    top_scores = [p.total_blood_donations for p in top]

    return jsonify({
        'donations': {'labels': list(months.keys()), 'data': list(months.values())},
        'blood_groups': {'labels': list(bg_dist.keys()), 'data': list(bg_dist.values())},
        'requests': {'labels': list(req_months.keys()), 'data': list(req_months.values())},
        'top_donors': {'labels': top_names, 'data': top_scores}
    })
