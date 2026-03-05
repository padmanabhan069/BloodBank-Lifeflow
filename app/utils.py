"""
Utility helpers: BMI, eligibility logic, QR code, PDF report, email, sample data
"""
from __future__ import annotations
import io
import os
from datetime import date, timedelta
from flask import current_app
from flask_mail import Message


# ─────────────────────────────────────────────────────────────────────────────
# BMI / Health helpers
# ─────────────────────────────────────────────────────────────────────────────

def calculate_bmi(weight_kg: float, height_cm: float) -> float:
    h = height_cm / 100
    return round(weight_kg / (h * h), 1)


def bmi_category(bmi: float) -> str:
    if bmi < 18.5:
        return 'Underweight'
    elif bmi < 25:
        return 'Normal'
    elif bmi < 30:
        return 'Overweight'
    return 'Obese'


def calculate_age(dob: date) -> int:
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def get_next_eligible_date(last_donation: date, cooldown_days: int) -> date:
    return last_donation + timedelta(days=cooldown_days)


def days_until_eligible(last_donation: date | None, cooldown: int) -> int:
    if not last_donation:
        return 0
    eligible = last_donation + timedelta(days=cooldown)
    delta = (eligible - date.today()).days
    return max(0, delta)


# ─────────────────────────────────────────────────────────────────────────────
# QR Code generator
# ─────────────────────────────────────────────────────────────────────────────

def generate_qr_code(data: str) -> bytes:
    """Return PNG bytes of a QR code for *data*."""
    try:
        import qrcode
        qr = qrcode.QRCode(version=1, box_size=8, border=4)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color='#C41E3A', back_color='white')
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        return buf.getvalue()
    except ImportError:
        return b''


# ─────────────────────────────────────────────────────────────────────────────
# PDF Report generator
# ─────────────────────────────────────────────────────────────────────────────

def generate_donor_pdf(user, profile) -> bytes:
    """Generate a PDF donor report and return raw bytes."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.units import cm

        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle('title', fontSize=20, textColor=colors.HexColor('#C41E3A'),
                                     spaceAfter=12, fontName='Helvetica-Bold')
        elements = []

        elements.append(Paragraph('BloodLife — Donor Report', title_style))
        elements.append(Spacer(1, 0.5*cm))

        info = [
            ['Full Name', user.name],
            ['Email', user.email],
            ['Blood Group', profile.blood_group if profile else '—'],
            ['Age', str(profile.age) if profile and profile.age else '—'],
            ['Gender', profile.gender if profile else '—'],
            ['Location', profile.location if profile else '—'],
            ['Phone', profile.phone if profile else '—'],
            ['BMI', str(profile.bmi) if profile and profile.bmi else '—'],
            ['Total Blood Donations', str(profile.total_blood_donations) if profile else '0'],
            ['Total Platelet Donations', str(profile.total_platelet_donations) if profile else '0'],
            ['Availability', 'Available' if profile and profile.is_available else 'Unavailable'],
            ['Report Date', date.today().strftime('%B %d, %Y')],
        ]

        table = Table(info, colWidths=[5*cm, 10*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#FFE4E9')),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#C41E3A')),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (1, 0), (-1, -1), [colors.white, colors.HexColor('#FDF8F8')]),
            ('PADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(table)
        doc.build(elements)
        return buf.getvalue()
    except Exception as e:
        current_app.logger.error(f'PDF generation error: {e}')
        return b''


# ─────────────────────────────────────────────────────────────────────────────
# Email helpers
# ─────────────────────────────────────────────────────────────────────────────

def send_reset_email(user, reset_url: str):
    from app import mail
    msg = Message(
        subject='BloodLife — Password Reset',
        recipients=[user.email],
        html=f'''
        <h2 style="color:#C41E3A;">BloodLife Password Reset</h2>
        <p>Hi {user.name},</p>
        <p>Click the link below to reset your password. This link expires in 30 minutes.</p>
        <a href="{reset_url}" style="background:#C41E3A;color:white;padding:10px 20px;border-radius:8px;text-decoration:none;">
            Reset Password
        </a>
        <p style="color:grey;margin-top:20px;">If you did not request this, please ignore this email.</p>
        ''')
    try:
        mail.send(msg)
    except Exception as e:
        current_app.logger.warning(f'Email send failed: {e}')


def send_request_notification_email(donor, request):
    from app import mail
    msg = Message(
        subject=f'BloodLife — Urgent {request.blood_group} Blood Needed',
        recipients=[donor.email],
        html=f'''
        <h2 style="color:#C41E3A;">Emergency Blood Request</h2>
        <p>Hi {donor.name},</p>
        <p>An emergency request matching your blood group has been submitted.</p>
        <table>
            <tr><td><b>Blood Group:</b></td><td>{request.blood_group}</td></tr>
            <tr><td><b>Hospital:</b></td><td>{request.hospital}</td></tr>
            <tr><td><b>Location:</b></td><td>{request.location}</td></tr>
            <tr><td><b>Date:</b></td><td>{request.need_date}</td></tr>
            <tr><td><b>Contact:</b></td><td>{request.contact}</td></tr>
        </table>
        <p>Please log in to accept or decline this request.</p>
        ''')
    try:
        mail.send(msg)
    except Exception as e:
        current_app.logger.warning(f'Email send failed: {e}')


# ─────────────────────────────────────────────────────────────────────────────
# Notification helper
# ─────────────────────────────────────────────────────────────────────────────

def send_in_app_notification(user_id: int, title: str, message: str,
                              notif_type: str = 'info', related_id: int | None = None):
    from app import db
    from app.models import Notification
    n = Notification(user_id=user_id, title=title, message=message,
                     notif_type=notif_type, related_id=related_id)
    db.session.add(n)
    db.session.commit()


# ─────────────────────────────────────────────────────────────────────────────
# Ranking recalculation
# ─────────────────────────────────────────────────────────────────────────────

def recalculate_all_ranks():
    from app import db
    from app.models import DonorProfile
    profiles = DonorProfile.query.all()
    for p in profiles:
        p.compute_rank_score()
    db.session.commit()


def get_compatible_blood_groups(recipient_bg: str) -> list[str]:
    """Return list of donor blood groups compatible with recipient_bg."""
    matrix = {
        'A+': ['A+', 'A-', 'O+', 'O-'],
        'A-': ['A-', 'O-'],
        'B+': ['B+', 'B-', 'O+', 'O-'],
        'B-': ['B-', 'O-'],
        'AB+': ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'],
        'AB-': ['A-', 'B-', 'AB-', 'O-'],
        'O+': ['O+', 'O-'],
        'O-': ['O-']
    }
    return matrix.get(recipient_bg, [recipient_bg])


# ─────────────────────────────────────────────────────────────────────────────
# Sample data seeder
# ─────────────────────────────────────────────────────────────────────────────

def create_sample_data():
    """Seed the database with demo users if empty."""
    from app import db
    from app.models import User, DonorProfile, DonationHistory, BloodStock, Notification
    from datetime import datetime

    if User.query.count() > 0:
        return   # already seeded

    blood_groups = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']

    # Blood stock
    for bg in blood_groups:
        stock = BloodStock(blood_group=bg, units_available={'A+':15,'A-':8,'B+':12,'B-':6,
                                                             'AB+':4,'AB-':2,'O+':20,'O-':10}[bg])
        db.session.add(stock)

    # Admin user
    admin = User(name='Admin User', email='admin@bloodlife.com', role='admin')
    admin.set_password('admin123')
    db.session.add(admin)
    db.session.flush()
    admin_profile = DonorProfile(
        user_id=admin.id, phone='+91-9000000001',
        dob=date(1985, 3, 15), gender='male', blood_group='O+',
        weight=80, height=180, location='Mumbai, Maharashtra',
        city='Mumbai', state='Maharashtra', is_available=True,
        is_platelet_donor=True,
        last_blood_donation=date.today() - timedelta(days=95),
        last_platelet_donation=date.today() - timedelta(days=35),
        total_blood_donations=15, total_platelet_donations=8,
        emergency_responses=5
    )
    admin_profile.compute_rank_score()
    db.session.add(admin_profile)

    # Sample donors
    sample_donors = [
        dict(name='Priya Sharma',   email='priya@example.com',  bg='A+', city='Delhi',       days_ago=95,  total=7,  plat=3, avail=True,  platelet=True),
        dict(name='Rahul Verma',    email='rahul@example.com',  bg='B+', city='Bengaluru',   days_ago=30,  total=3,  plat=0, avail=True,  platelet=False),
        dict(name='Anjali Singh',   email='anjali@example.com', bg='O-', city='Chennai',     days_ago=100, total=12, plat=5, avail=True,  platelet=True),
        dict(name='Karan Mehta',    email='karan@example.com',  bg='AB+',city='Hyderabad',   days_ago=45,  total=4,  plat=2, avail=False, platelet=False),
        dict(name='Sneha Iyer',     email='sneha@example.com',  bg='A-', city='Pune',        days_ago=92,  total=9,  plat=0, avail=True,  platelet=False),
        dict(name='Vikram Nair',    email='vikram@example.com', bg='B-', city='Kolkata',     days_ago=200, total=6,  plat=4, avail=True,  platelet=True),
    ]

    for i, d in enumerate(sample_donors, start=2):
        u = User(name=d['name'], email=d['email'], role='user')
        u.set_password('user123')
        db.session.add(u)
        db.session.flush()
        p = DonorProfile(
            user_id=u.id, phone=f'+91-900000000{i}',
            dob=date(1990 + i, 1, 10 + i), gender='female' if i % 2 == 0 else 'male',
            blood_group=d['bg'], weight=55 + i*3, height=160 + i*2,
            location=f"{d['city']}, India", city=d['city'], state='India',
            is_available=d['avail'], is_platelet_donor=d['platelet'],
            last_blood_donation=date.today() - timedelta(days=d['days_ago']),
            last_platelet_donation=date.today() - timedelta(days=d['days_ago']//3) if d['plat'] > 0 else None,
            total_blood_donations=d['total'], total_platelet_donations=d['plat'],
            emergency_responses=d['total'] // 3
        )
        p.compute_rank_score()
        db.session.add(p)

        # Donation history
        for j in range(min(d['total'], 3)):
            dh = DonationHistory(
                user_id=u.id, donation_type='blood',
                donation_date=date.today() - timedelta(days=d['days_ago'] + j*100),
                location=f"{d['city']} Blood Bank",
                blood_group=d['bg'], units=1,
                notes='Regular donation', is_emergency=(j == 0)
            )
            db.session.add(dh)

        # Welcome notification
        notif = Notification(
            user_id=u.id, title='Welcome to BloodLife! 🎉',
            message='Thank you for registering. Your first donation could save 3 lives!',
            notif_type='info'
        )
        db.session.add(notif)

    db.session.commit()
    print('✅ Sample data created successfully!')
