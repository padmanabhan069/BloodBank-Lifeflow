"""
WTForms form definitions for BloodLife
"""
from flask_wtf import FlaskForm
from wtforms import (StringField, PasswordField, BooleanField, SelectField,
                     TextAreaField, FloatField, IntegerField, DateField,
                     TimeField, TelField, SubmitField)
from wtforms.validators import (DataRequired, Email, EqualTo, Length, Optional,
                                NumberRange, ValidationError, Regexp)
from app.models import User, BLOOD_GROUPS


BLOOD_GROUP_CHOICES = [('', 'Select Blood Group')] + [(g, g) for g in BLOOD_GROUPS]
GENDER_CHOICES = [('', 'Select Gender'), ('male', 'Male'),
                  ('female', 'Female'), ('other', 'Other')]


# ─── Auth Forms ───────────────────────────────────────────────────────────────

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')


class RegistrationForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(2, 100)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=150)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm Password',
                                     validators=[DataRequired(), EqualTo('password')])
    phone = TelField('Phone', validators=[
        DataRequired(), 
        Regexp(r'^\d{10}$', message="Phone number must be exactly 10 digits (e.g. 9876543210)")
    ])
    dob = DateField('Date of Birth', validators=[DataRequired()])
    gender = SelectField('Gender', choices=GENDER_CHOICES, validators=[DataRequired()])
    blood_group = SelectField('Blood Group', choices=BLOOD_GROUP_CHOICES,
                              validators=[DataRequired()])
    location = StringField('Location (City, State)', validators=[DataRequired(), Length(max=200)])
    weight = FloatField('Weight (kg)', validators=[DataRequired(), NumberRange(min=40, max=300)])
    height = FloatField('Height (cm)', validators=[DataRequired(), NumberRange(min=100, max=250)])
    platelet_willing = BooleanField('I am willing to donate platelets')
    blood_willing = BooleanField('I am willing to donate blood', default=True)
    submit = SubmitField('Create Account')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.lower()).first():
            raise ValidationError('Email is already registered.')


class ForgotPasswordForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Send Reset Link')


class ResetPasswordForm(FlaskForm):
    password = PasswordField('New Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm Password',
                                     validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Reset Password')


# ─── Donor Profile Form ───────────────────────────────────────────────────────

class ProfileUpdateForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(2, 100)])
    phone = TelField('Phone', validators=[
        Optional(), 
        Regexp(r'^\d{10}$', message="Phone number must be exactly 10 digits")
    ])
    dob = DateField('Date of Birth', validators=[Optional()])
    gender = SelectField('Gender', choices=GENDER_CHOICES, validators=[Optional()])
    location = StringField('Location', validators=[Optional(), Length(max=200)])
    weight = FloatField('Weight (kg)', validators=[Optional(), NumberRange(min=40, max=300)])
    height = FloatField('Height (cm)', validators=[Optional(), NumberRange(min=100, max=250)])
    platelet_willing = BooleanField('Willing to donate platelets')
    submit = SubmitField('Save Changes')


# ─── Blood Request Form ───────────────────────────────────────────────────────

class BloodRequestForm(FlaskForm):
    request_type = SelectField('Request Type', choices=[('blood', 'Whole Blood'), ('platelet', 'Platelet')],
                               default='blood', validators=[DataRequired()])
    blood_group = SelectField('Blood Group Required', choices=BLOOD_GROUP_CHOICES,
                              validators=[DataRequired()])
    units = IntegerField('Units Required', validators=[DataRequired(),
                                                       NumberRange(min=1, max=20)])
    hospital = StringField('Hospital Name', validators=[DataRequired(), Length(max=200)])
    location = StringField('Hospital Location', validators=[DataRequired(), Length(max=300)])
    need_date = DateField('Date Required', validators=[DataRequired()])
    need_time = StringField('Time Required', validators=[Optional()])
    contact = TelField('Contact Number', validators=[
        DataRequired(), 
        Regexp(r'^\d{10}$', message="Contact number must be exactly 10 digits")
    ])
    notes = TextAreaField('Additional Notes', validators=[Optional(), Length(max=1000)])
    is_urgent = BooleanField('Mark as Critical Emergency')
    submit = SubmitField('Submit Request')


# ─── Admin Forms ──────────────────────────────────────────────────────────────

class BloodStockUpdateForm(FlaskForm):
    blood_group = SelectField('Blood Group', choices=BLOOD_GROUP_CHOICES,
                              validators=[DataRequired()])
    units = FloatField('Units Available', validators=[DataRequired(),
                                                      NumberRange(min=0, max=10000)])
    submit = SubmitField('Update Stock')


class DonationRecordForm(FlaskForm):
    donation_type = SelectField('Donation Type',
                                choices=[('blood', 'Blood'), ('platelet', 'Platelet')],
                                validators=[DataRequired()])
    donation_date = DateField('Donation Date', validators=[DataRequired()])
    location = StringField('Location', validators=[Optional(), Length(max=200)])
    notes = TextAreaField('Notes', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Record Donation')
