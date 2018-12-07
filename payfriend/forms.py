from flask_wtf import FlaskForm
from wtforms import (
    IntegerField, 
    PasswordField, 
    RadioField, 
    StringField, 
    validators
)
from payfriend.db import get_db


class RegisterForm(FlaskForm):
    """Form used for registering new users"""
    email = StringField(
        'Email', 
        validators=[validators.InputRequired(), 
                    validators.Email()])
    password = PasswordField(
        'Password', 
        validators=[validators.InputRequired()])
    phone_number = StringField(
        'Phone', 
        validators=[validators.InputRequired()])
    full_phone = StringField('Full Phone')
    channel = RadioField(
        'Channel',
        choices=[('sms', 'SMS'),('call', 'Call')],
        default='sms')

    def create_user(self, authy_user_id):
        db.execute(
            'INSERT INTO users (email, password, phone_number, authy_id) VALUES (?, ?, ?, ?)',
            (self.email.data, 
             generate_password_hash(self.password.data), 
             self.full_phone,
             authy_user_id))
        db.commit()
        return authy_user_id


class LoginForm(FlaskForm):
    """Form used for logging in existing users"""
    email = StringField('Email', validators=[validators.InputRequired(), validators.Email()])
    password = PasswordField('Password', validators=[validators.InputRequired()])


class VerifyForm(FlaskForm):
    """Form used to verify SMS codes"""
    verification_code = StringField(
        'Verification code',
        validators=[
            validators.InputRequired(),
            validators.Length(min=4, max=10)
        ]
    )

class PaymentForm(FlaskForm):
    """Form used to submit payments"""
    send_to = StringField('Send to', validators=[validators.InputRequired()])
    amount = IntegerField('Amount', validators=[validators.InputRequired()])