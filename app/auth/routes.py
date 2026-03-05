"""
Auth blueprint routes — login, logout, signup, forgot/reset password, eligibility
"""
from flask import render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, current_user, login_required
from app.auth import auth
from app import db
from app.models import User, DonorProfile, EligibilityCheck
from app.forms import LoginForm, RegistrationForm, ForgotPasswordForm, ResetPasswordForm
from app.utils import calculate_bmi, send_reset_email


@auth.route('/eligibility', methods=['GET', 'POST'])
def eligibility():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    if request.method == 'POST':
        answers = {
            'q_age':        request.form.get('age') == 'yes',
            'q_weight':     request.form.get('weight') == 'yes',
            'q_health':     request.form.get('health') == 'yes',
            'q_medication': request.form.get('medication') == 'yes',
            'q_sleep':      request.form.get('sleep') == 'yes',
            'q_alcohol':    request.form.get('alcohol') == 'yes',
            'q_tattoo':     request.form.get('tattoo') == 'yes',
            'q_surgery':    request.form.get('surgery') == 'yes',
            'q_infectious': request.form.get('infectious') == 'yes',
            'q_heart':      request.form.get('heart') == 'yes',
        }
        all_passed = all(answers.values())

        fail_reasons = {
            'q_age':        'Age must be between 18-65 years.',
            'q_weight':     'Weight must be at least 45 kg.',
            'q_health':     'You must be in good health with no current illness.',
            'q_medication': 'You must not be on restricted medication.',
            'q_sleep':      'At least 6 hours of sleep is required.',
            'q_alcohol':    'No alcohol consumption in the last 24 hours.',
            'q_tattoo':     'No tattoo or piercing in the last 6 months.',
            'q_surgery':    'No surgery or major dental procedure in the last 6 months.',
            'q_infectious': 'No recent infectious disease.',
            'q_heart':      'No history of serious heart or blood disorder.',
        }
        fail_reason = None
        for key, passed in answers.items():
            if not passed:
                fail_reason = fail_reasons[key]
                break

        check = EligibilityCheck(**answers, is_eligible=all_passed, fail_reason=fail_reason,
                                 session_id=session.get('_id', ''))
        db.session.add(check)
        db.session.commit()

        if all_passed:
            session['eligible'] = True
            return render_template('auth/eligibility.html', result='pass')
        else:
            return render_template('auth/eligibility.html', result='fail', reason=fail_reason)
    return render_template('auth/eligibility.html')


@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    if not session.get('eligible'):
        flash('Please complete the eligibility check first.', 'warning')
        return redirect(url_for('auth.eligibility'))

    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(name=form.name.data, email=form.email.data.lower())
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.flush()

        profile = DonorProfile(
            user_id=user.id,
            phone=form.phone.data,
            dob=form.dob.data,
            gender=form.gender.data,
            blood_group=form.blood_group.data,
            weight=form.weight.data,
            height=form.height.data,
            location=form.location.data,
            city=form.location.data.split(',')[0].strip(),
            is_available=form.blood_willing.data,
            is_platelet_donor=form.platelet_willing.data
        )
        profile.compute_rank_score()
        db.session.add(profile)
        db.session.commit()

        # Welcome notification
        from app.utils import send_in_app_notification
        send_in_app_notification(user.id, 'Welcome to BloodLife! 🎉',
                                 'Thank you for registering. Your first donation could save 3 lives!')
        session.pop('eligible', None)
        login_user(user)
        flash('Account created! Welcome to BloodLife.', 'success')
        return redirect(url_for('main.dashboard'))

    return render_template('auth/register.html', form=form)


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user and user.check_password(form.password.data):
            if user.is_blocked:
                flash('Your account has been blocked. Contact support.', 'danger')
                return redirect(url_for('auth.login'))
            from datetime import datetime
            user.last_login = datetime.utcnow()
            db.session.commit()
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            flash(f'Welcome back, {user.name}!', 'success')
            return redirect(next_page or url_for('main.dashboard'))
        flash('Invalid email or password.', 'danger')
    return render_template('auth/login.html', form=form)


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


@auth.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user:
            token = user.get_reset_token()
            reset_url = url_for('auth.reset_password', token=token, _external=True)
            send_reset_email(user, reset_url)
        flash('If that email exists, a reset link has been sent.', 'info')
        return redirect(url_for('auth.login'))
    return render_template('auth/forgot_password.html', form=form)


@auth.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = User.verify_reset_token(token)
    if not user:
        flash('The reset link is invalid or has expired.', 'danger')
        return redirect(url_for('auth.forgot_password'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Password updated! Please log in.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', form=form)
