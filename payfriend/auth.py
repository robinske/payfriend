import functools
import phonenumbers

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
from werkzeug.security import check_password_hash, generate_password_hash

from payfriend.db import get_db
from authy.api import AuthyApiClient


bp = Blueprint('auth', __name__, url_prefix='/auth')


def login_required(view):
    """View decorator that redirects anonymous users to the login page."""
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('auth.login'))

        return view(**kwargs)

    return wrapped_view


def start_verification(country_code, number, channel='sms'):
    print(channel)
    api = AuthyApiClient(app.config['AUTHY_API_KEY'])
    api.phones.verification_start(number, country_code, via=channel)


def check_verification(country_code, phone, code):
    api = AuthyApiClient(app.config['AUTHY_API_KEY'])
    try:
        verification = api.phones.verification_check(phone, country_code, code)

        if verification.ok():
            db = get_db()
            db.execute(
                'UPDATE users SET verified = 1 WHERE phone_number = ?',
                (phone,)
            )
            db.commit()
            flash('Your phone number has been verified! Please login to continue.')
    except Exception as e:
        flash("Error validating code: {}".format(e))


def create_authy_user(email, country_code, phone):
    api = AuthyApiClient(app.config['AUTHY_API_KEY'])
    user = api.users.create(email, phone, country_code)
    if user.ok():
        db = get_db()
        db.execute(
            'UPDATE users SET authy_id = ? WHERE email = ?',
            (user.id, email,)
        )
        db.commit()
        return user.id
    else:
        return None


@bp.before_app_request
def load_logged_in_user():
    """If a user id is stored in the session, load the user object from
    the database into ``g.user``."""
    user_id = session.get('user_id')

    if user_id is None:
        g.user = None
    else:
        g.user = get_db().execute(
            'SELECT * FROM users WHERE id = ?', (user_id,)
        ).fetchone()


@bp.route('/register', methods=('GET', 'POST'))
def register():
    """Register a new user.

    Validates that the email is not already taken. Hashes the
    password for security.
    """
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        full_phone = request.form['full_phone']
        pn = phonenumbers.parse(full_phone)
        phone = pn.national_number
        country_code = pn.country_code
        channel = request.form['channel']

        db = get_db()
        error = None

        if not email:
            error = 'Email is required.'
        elif not phone:
            error = 'Phone number is required'
        elif not password:
            error = 'Password is required.'
        elif db.execute(
            'SELECT id FROM users WHERE email = ?', (email,)
        ).fetchone() is not None:
            error = 'User {0} is already registered.'.format(email)

        if error is None:
            session['phone'] = phone
            session['country_code'] = country_code
            session['email'] = email
            try:
                # use Authy API to send verification code to the user's phone
                start_verification(country_code, phone, channel)
                db.execute(
                    'INSERT INTO users (email, password, phone_number) VALUES (?, ?, ?)',
                    (email, generate_password_hash(password), full_phone)
                )
                db.commit()
                return redirect(url_for('auth.verify'))
            except:
                error = 'Error sending phone verification.'

        flash(error)
    return render_template('auth/register.html')


@bp.route('/verify', methods=('GET', 'POST'))
def verify():
    """Verify a user on registration with their phone number"""
    if request.method == 'POST':
        phone = session.get('phone')
        country_code = session.get('country_code')
        code = request.form['code']

        # use Authy API to check the verification code
        check_verification(country_code, phone, code)

        email = session.get('email')
        create_authy_user(email, country_code, phone)
        return redirect(url_for('auth.login'))

    return render_template('auth/verify.html')


@bp.route('/login', methods=('GET', 'POST'))
def login():
    """Log in a registered user by adding the user id to the session."""
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        db = get_db()
        error = None
        user = db.execute(
            'SELECT * FROM users WHERE email = ?', (email,)
        ).fetchone()

        if user is None:
            error = 'Incorrect email.'
        elif not check_password_hash(user['password'], password):
            error = 'Incorrect password.'

        if error is None:
            # store the user id in a new session
            # redirect to payments
            session.clear()
            session['user_id'] = user['id']
            session['authy_id'] = user['authy_id']
            return redirect(url_for('payments.send'))

        flash(error)

    return render_template('auth/login.html')


@bp.route('/logout')
def logout():
    """Clear the current session, including the stored user id."""
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for('auth.login'))
