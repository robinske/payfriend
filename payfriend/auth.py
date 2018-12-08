import functools
import phonenumbers
from authy.api import AuthyApiClient
from flask import (
    Blueprint,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for
)
from flask import current_app as app
from payfriend import db
from payfriend.forms import RegisterForm, LoginForm, VerifyForm
from payfriend.models import User


bp = Blueprint('auth', __name__, url_prefix='/auth')


def login_required(view):
    """View decorator that redirects anonymous users to the login page."""
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('auth.login'))

        return view(**kwargs)

    return wrapped_view


def start_verification(country_code, phone, channel='sms'):
    api = AuthyApiClient(app.config['AUTHY_API_KEY'])
    api.phones.verification_start(phone, country_code, via=channel)


def check_verification(country_code, phone, code):
    api = AuthyApiClient(app.config['AUTHY_API_KEY'])
    try:
        verification = api.phones.verification_check(phone, country_code, code)
        if verification.ok():
            flash('Your phone number has been verified! Please login to continue.')
    except Exception as e:
        flash("Error validating code: {}".format(e))


def create_authy_user(email, country_code, phone):
    api = AuthyApiClient(app.config['AUTHY_API_KEY'])
    authy_user = api.users.create(email, phone, country_code)
    if authy_user.ok():
        return authy_user.id
    else:
        flash("Error creating Authy user: {}".format(authy_user.errors()))
        return None


@bp.before_app_request
def load_logged_in_user():
    """If a user id is stored in the session, load the user object from
    the database into ``g.user``."""
    user_id = session.get('user_id')

    if user_id is None:
        g.user = None
    else:
        g.user = User.query.filter_by(id=user_id).first()


@bp.route('/register', methods=('GET', 'POST'))
def register():
    """Register a new user.

    Validates that the email is not already taken. Hashes the
    password for security.
    """
    form = RegisterForm(request.form)

    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        full_phone = form.full_phone.data
        channel = form.channel.data

        # Authy API requires separate country code
        pn = phonenumbers.parse(full_phone)
        phone = pn.national_number
        country_code = pn.country_code

        session['phone'] = phone
        session['full_phone'] = full_phone
        session['country_code'] = country_code
        session['email'] = email
        try:
            # use Authy API to send verification code to the user's phone
            start_verification(country_code, phone, channel)
            user = User(email, password, full_phone)
            db.session.add(user)
            db.session.commit()
            return redirect(url_for('auth.verify'))
        except Exception as e:
            flash('Error sending phone verification. {}'.format(e))

    return render_template('auth/register.html', form=form)



@bp.route('/verify', methods=('GET', 'POST'))
def verify():
    """Verify a user on registration with their phone number"""
    form = VerifyForm(request.form)

    if form.validate_on_submit():
        email = session.get('email')
        phone = session.get('phone')
        country_code = session.get('country_code')
        code = form.verification_code.data

        # use Authy API to check the verification code
        check_verification(country_code, phone, code)
        
        # if verification passes, create the authy user
        authy_id = create_authy_user(email, country_code, phone)

        # update the database with the authy id
        user = User.query.filter_by(email=email).first()
        user.authy_id = authy_id
        db.session.commit()

        return redirect(url_for('auth.login'))

    return render_template('auth/verify.html', form=form)


@bp.route('/login', methods=('GET', 'POST'))
def login():
    """Log in a registered user by adding the user id to the session."""
    form = LoginForm(request.form)

    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        
        error = None
        user = User.query.filter_by(email=email).first()
        if user is None:
            error = 'Incorrect email.'
        elif not user.verify_password(password):
            error = 'Incorrect password.'

        if error is None:
            # store the user id in a new session
            # redirect to payments
            session.clear()
            session['user_id'] = user.id
            session['authy_id'] = user.authy_id
            return redirect(url_for('payments.send'))

        flash(error)

    return render_template('auth/login.html', form=form)


@bp.route('/logout')
def logout():
    """Clear the current session, including the stored user id."""
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for('auth.login'))
