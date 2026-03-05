"""
SQLAlchemy database models for BloodLife Donor Management System
"""
from datetime import datetime, date, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db


# ─────────────────────────────────────────────────────────────────────────────
# Helper constants
# ─────────────────────────────────────────────────────────────────────────────
BLOOD_COOLDOWN = 90   # days
PLATELET_COOLDOWN = 30  # days

BLOOD_GROUPS = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']


# ─────────────────────────────────────────────────────────────────────────────
# User model
# ─────────────────────────────────────────────────────────────────────────────
class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(10), default='user')          # 'user' | 'admin'
    is_active = db.Column(db.Boolean, default=True)
    is_blocked = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    # ── Relationships ──────────────────────────────────────────────────────
    profile = db.relationship('DonorProfile', back_populates='user',
                               uselist=False, cascade='all, delete-orphan')
    blood_requests = db.relationship('BloodRequest', back_populates='requester',
                                      foreign_keys='BloodRequest.user_id',
                                      cascade='all, delete-orphan')
    donation_history = db.relationship('DonationHistory', back_populates='donor',
                                        cascade='all, delete-orphan')
    platelet_donations = db.relationship('PlateletDonation', back_populates='donor',
                                          cascade='all, delete-orphan')
    notifications = db.relationship('Notification', back_populates='user',
                                     cascade='all, delete-orphan')
    eligibility_checks = db.relationship('EligibilityCheck', back_populates='user',
                                          cascade='all, delete-orphan')

    # ── Password helpers ──────────────────────────────────────────────────
    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    # ── Token helpers (for password reset) ───────────────────────────────
    def get_reset_token(self, expires_sec=1800):
        from itsdangerous import URLSafeTimedSerializer
        from flask import current_app
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        return s.dumps(self.email, salt='password-reset-salt')

    @staticmethod
    def verify_reset_token(token, expires_sec=1800):
        from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
        from flask import current_app
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        try:
            email = s.loads(token, salt='password-reset-salt', max_age=expires_sec)
        except (BadSignature, SignatureExpired):
            return None
        return User.query.filter_by(email=email).first()

    @property
    def is_admin(self):
        return self.role == 'admin'

    def __repr__(self):
        return f'<User {self.email}>'


# ─────────────────────────────────────────────────────────────────────────────
# Donor Profile model
# ─────────────────────────────────────────────────────────────────────────────
class DonorProfile(db.Model):
    __tablename__ = 'donor_profiles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)

    phone = db.Column(db.String(20))
    dob = db.Column(db.Date)
    gender = db.Column(db.String(10))
    blood_group = db.Column(db.String(5), index=True)
    weight = db.Column(db.Float)     # kg
    height = db.Column(db.Float)     # cm
    location = db.Column(db.String(200))
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))

    # Availability & readiness
    is_available = db.Column(db.Boolean, default=True)
    is_platelet_donor = db.Column(db.Boolean, default=False)

    # Donation tracking
    last_blood_donation = db.Column(db.Date)
    last_platelet_donation = db.Column(db.Date)
    total_blood_donations = db.Column(db.Integer, default=0)
    total_platelet_donations = db.Column(db.Integer, default=0)
    emergency_responses = db.Column(db.Integer, default=0)

    # Ranking scores (computed periodically)
    blood_rank_score = db.Column(db.Float, default=0.0)
    platelet_rank_score = db.Column(db.Float, default=0.0)

    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # ── Relationships ──────────────────────────────────────────────────────
    user = db.relationship('User', back_populates='profile')

    # ── Computed properties ────────────────────────────────────────────────
    @property
    def bmi(self) -> float | None:
        if self.weight and self.height and self.height > 0:
            h_m = self.height / 100
            return round(self.weight / (h_m * h_m), 1)
        return None

    @property
    def age(self) -> int | None:
        if not self.dob:
            return None
        today = date.today()
        return today.year - self.dob.year - (
            (today.month, today.day) < (self.dob.month, self.dob.day)
        )

    @property
    def next_blood_eligible_date(self) -> date:
        if self.last_blood_donation:
            return self.last_blood_donation + timedelta(days=BLOOD_COOLDOWN)
        return date.today()

    @property
    def next_platelet_eligible_date(self) -> date:
        if self.last_platelet_donation:
            return self.last_platelet_donation + timedelta(days=PLATELET_COOLDOWN)
        return date.today()

    @property
    def blood_days_until_eligible(self) -> int:
        delta = (self.next_blood_eligible_date - date.today()).days
        return max(0, delta)

    @property
    def platelet_days_until_eligible(self) -> int:
        delta = (self.next_platelet_eligible_date - date.today()).days
        return max(0, delta)

    @property
    def is_blood_eligible(self) -> bool:
        return self.is_available and self.blood_days_until_eligible == 0

    @property
    def is_platelet_eligible(self) -> bool:
        return self.is_platelet_donor and self.is_available and self.platelet_days_until_eligible == 0

    def compute_rank_score(self):
        """Calculate blood rank score: donations×10 + emergency×15 + availability×5"""
        self.blood_rank_score = (
            (self.total_blood_donations or 0) * 10 +
            (self.emergency_responses or 0) * 15 +
            (5 if self.is_available else 0)
        )
        self.platelet_rank_score = (
            (self.total_platelet_donations or 0) * 10 +
            (self.emergency_responses or 0) * 5 +
            (5 if self.is_platelet_donor else 0)
        )

    def __repr__(self):
        return f'<DonorProfile user_id={self.user_id} blood={self.blood_group}>'


# ─────────────────────────────────────────────────────────────────────────────
# Eligibility Check model
# ─────────────────────────────────────────────────────────────────────────────
class EligibilityCheck(db.Model):
    __tablename__ = 'eligibility_checks'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    session_id = db.Column(db.String(100))   # for anonymous checks

    # Yes/No answers stored as JSON-like flags
    q_age = db.Column(db.Boolean)
    q_weight = db.Column(db.Boolean)
    q_health = db.Column(db.Boolean)
    q_medication = db.Column(db.Boolean)
    q_sleep = db.Column(db.Boolean)
    q_alcohol = db.Column(db.Boolean)
    q_tattoo = db.Column(db.Boolean)
    q_surgery = db.Column(db.Boolean)
    q_infectious = db.Column(db.Boolean)
    q_heart = db.Column(db.Boolean)

    is_eligible = db.Column(db.Boolean, default=False)
    fail_reason = db.Column(db.String(200))
    checked_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', back_populates='eligibility_checks')

    @property
    def all_passed(self) -> bool:
        return all([self.q_age, self.q_weight, self.q_health, self.q_medication,
                    self.q_sleep, self.q_alcohol, self.q_tattoo, self.q_surgery,
                    self.q_infectious, self.q_heart])

    def __repr__(self):
        return f'<EligibilityCheck user_id={self.user_id} eligible={self.is_eligible}>'


# ─────────────────────────────────────────────────────────────────────────────
# Blood Request model
# ─────────────────────────────────────────────────────────────────────────────
class BloodRequest(db.Model):
    __tablename__ = 'blood_requests'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    blood_group = db.Column(db.String(5), nullable=False)
    units = db.Column(db.Integer, nullable=False, default=1)
    hospital = db.Column(db.String(200), nullable=False)
    location = db.Column(db.String(300))
    need_date = db.Column(db.Date, nullable=False)
    need_time = db.Column(db.String(10))
    contact = db.Column(db.String(20))
    notes = db.Column(db.Text)
    is_urgent = db.Column(db.Boolean, default=False)
    request_type = db.Column(db.String(10), default='blood')   # 'blood' | 'platelet'
    status = db.Column(db.String(20), default='active')        # 'active' | 'fulfilled' | 'closed'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # ── Relationships ──────────────────────────────────────────────────────
    requester = db.relationship('User', back_populates='blood_requests',
                                 foreign_keys=[user_id])
    responses = db.relationship('RequestResponse', back_populates='request',
                                 cascade='all, delete-orphan')

    @property
    def accepted_count(self):
        return sum(1 for r in self.responses if r.action == 'accept')

    def __repr__(self):
        return f'<BloodRequest {self.blood_group} {self.hospital}>'


class RequestResponse(db.Model):
    """Tracks which donors accepted/declined a blood request."""
    __tablename__ = 'request_responses'

    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('blood_requests.id'), nullable=False)
    donor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(10))   # 'accept' | 'decline'
    responded_at = db.Column(db.DateTime, default=datetime.utcnow)

    request = db.relationship('BloodRequest', back_populates='responses')
    donor = db.relationship('User')


# ─────────────────────────────────────────────────────────────────────────────
# Donation History model
# ─────────────────────────────────────────────────────────────────────────────
class DonationHistory(db.Model):
    __tablename__ = 'donation_history'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    donation_type = db.Column(db.String(10))   # 'blood' | 'platelet'
    donation_date = db.Column(db.Date, nullable=False)
    location = db.Column(db.String(200))
    blood_group = db.Column(db.String(5))
    units = db.Column(db.Float, default=1)
    notes = db.Column(db.Text)
    is_emergency = db.Column(db.Boolean, default=False)
    request_id = db.Column(db.Integer, db.ForeignKey('blood_requests.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    donor = db.relationship('User', back_populates='donation_history')

    def __repr__(self):
        return f'<DonationHistory {self.donation_type} on {self.donation_date}>'


# ─────────────────────────────────────────────────────────────────────────────
# Platelet Donation model
# ─────────────────────────────────────────────────────────────────────────────
class PlateletDonation(db.Model):
    __tablename__ = 'platelet_donations'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    donation_date = db.Column(db.Date, nullable=False)
    location = db.Column(db.String(200))
    hemoglobin = db.Column(db.Float)
    platelet_count = db.Column(db.Float)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    donor = db.relationship('User', back_populates='platelet_donations')

    def __repr__(self):
        return f'<PlateletDonation user_id={self.user_id} on {self.donation_date}>'


# ─────────────────────────────────────────────────────────────────────────────
# Notification model
# ─────────────────────────────────────────────────────────────────────────────
class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notif_type = db.Column(db.String(30), default='info')  # 'info' | 'request' | 'reminder' | 'alert'
    related_id = db.Column(db.Integer)                     # optional FK to request/donation
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', back_populates='notifications')

    def __repr__(self):
        return f'<Notification user_id={self.user_id} read={self.is_read}>'


# ─────────────────────────────────────────────────────────────────────────────
# Blood Stock / Inventory model
# ─────────────────────────────────────────────────────────────────────────────
class BloodStock(db.Model):
    __tablename__ = 'blood_stock'

    id = db.Column(db.Integer, primary_key=True)
    blood_group = db.Column(db.String(5), unique=True, nullable=False)
    units_available = db.Column(db.Float, default=0)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    def __repr__(self):
        return f'<BloodStock {self.blood_group}: {self.units_available} units>'
