from authy.api import AuthyApiClient
from flask import (
    abort,
    Blueprint,
    flash,
    jsonify,
    g,
    render_template,
    redirect,
    request,
    session,
    url_for
)
from flask import current_app as app
from . import utils
from payfriend import db
from payfriend.decorators import (
    display_flash_messages,
    login_required, 
    verification_required,
    verify_authy_request
)
from payfriend.forms import PaymentForm
from payfriend.models import Payment, User


bp = Blueprint('payments', __name__, url_prefix='/payments')


@bp.before_app_request
def load_logged_in_user():
    """
    If a user id is stored in the session, load the user object from
    the database into ``g.user``.
    """
    user_id = session.get('user_id')

    if user_id is None:
        g.user = None
    else:
        g.user = User.query.filter_by(id=user_id).first()

        

@bp.route('/callback', methods=["POST"])
@verify_authy_request
def callback():
    """
    Used by Twilio to send a notification when the user 
    approves or denies a push authorization in the Authy app
    """
    request_id = request.json.get('uuid')
    status = request.json.get('status')

    payment = Payment.query.filter_by(id=request_id).first()

    if not payment:
        abort(404)

    payment.status = status
    db.session.commit()
    
    if status == 'approved':
        return ('Successfully authorized payment {}'.format(request_id), 200)
    if status == 'denied':
        return ('Payment authorization denied.', 200)

    abort(400)


@bp.route('/status', methods=["GET", "POST"])
@login_required
def status():
    """
    Used by AJAX requests to check the OneTouch verification status of a payment
    """
    request_id = request.args.get('request_id')
    payment = Payment.query.filter_by(id=request_id).first()
    return payment.status


@bp.route('/send', methods=["GET", "POST"])
@login_required
@verification_required
@display_flash_messages
def send():
    form = PaymentForm(request.form)
    if form.validate_on_submit():
        send_to = form.send_to.data
        amount = form.amount.data
        authy_id = session.get('authy_id')

        (request_id, errors) = utils.send_push_auth(authy_id, send_to, amount)
        if request_id:
            payment = Payment(request_id, authy_id, send_to, amount)
            db.session.add(payment)
            db.session.commit()
            return jsonify({
                "success": True,
                "request_id": request_id
            })
        else:
            flash("Error sending authorization. {}".format(errors))
            return jsonify({"success": False})
    
    return render_template("payments/send.html", form=form)


@bp.route('/', methods=["GET", "POST"])
@login_required
@display_flash_messages
def list_payments():
    user_payments = db.session.query(Payment, User) \
        .join(User) \
        .filter_by(email=g.user.email) \
        .all()

    payments = []
    for (payment, user) in user_payments:
        payments.append({
            "email": user.email,
            "id": payment.id,
            "send_to": payment.send_to,
            "amount": payment.amount,
            "status": payment.status
        })

    return render_template('payments/list.html', payments=payments)
