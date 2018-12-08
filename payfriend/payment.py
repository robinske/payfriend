from authy.api import AuthyApiClient
from flask import (
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
from payfriend import db
from payfriend.auth import login_required
from payfriend.forms import PaymentForm
from payfriend.models import Payment, User


bp = Blueprint('payments', __name__, url_prefix='/payments')


def push_auth(authy_id_str, send_to, amount):
    details = {
        "Sending to": send_to,
        "Transaction amount": str(amount)
    }

    authy_id = int(authy_id_str)
    message = "Please authorize payment to {}".format(send_to)
    seconds_to_expire = 1200

    api = AuthyApiClient(app.config['AUTHY_API_KEY'])
    resp = api.one_touch.send_request(
        authy_id,
        message,
        seconds_to_expire=seconds_to_expire,
        details=details
    )

    if resp.ok():
        request_id = resp.content['approval_request']['uuid']
        payment = Payment(request_id, authy_id, send_to, amount)
        db.session.add(payment)
        db.session.commit()
        return (request_id, {})
    else:
        return (None, resp.errors())
        

@bp.route('/callback', methods=["POST"])
def callback():
    request_id = request.json.get('uuid')
    status = request.json.get('status')

    payment = Payment.query.filter_by(id=request_id).first()

    if not payment:
        return ('Could not find a payment to authorize.', 404)

    payment.status = status
    db.session.commit()
    
    if status == 'approved':
        return ('Successfully authorized payment {}'.format(request_id), 200)
    if status == 'denied':
        return ('Payment authorization denied.', 200)

    return ('Error authorizing payment.', 400)


@bp.route('/send', methods=["GET", "POST"])
@login_required
def send():
    if 'redirect_message' in request.form:
        message = request.form.get("redirect_message")
        flash(message)

    form = PaymentForm(request.form)

    if 'send-payment-submit' in request.form and form.validate_on_submit():
        send_to = form.send_to.data
        amount = form.amount.data
        authy_id = session.get('authy_id')

        (request_id, errors) = push_auth(authy_id, send_to, amount)
        if request_id:
            return jsonify({
                "success": True,
                "request_id": request_id
            })
        else:
            flash("Error sending authorization. {}".format(errors))
            return jsonify({"success": False})
    
    return render_template("payments/send.html", form=form)


@bp.route('/status', methods=["GET", "POST"])
@login_required
def status():
    """
    Used by AJAX requests to check the OneTouch verification status of a payment
    """
    request_id = request.args.get('request_id')
    payment = Payment.query.filter_by(id=request_id).first()
    return payment.status


@bp.route('/', methods=["GET", "POST"])
@login_required
def list_payments():
    if request.method == "POST":
        message = request.form.get("redirect_message")
        flash(message)

    user_payments = db.session.query(Payment, User) \
        .join(User) \
        .all()

    payments = [payment for (payment,user) in user_payments]
    return render_template('payments/list.html', payments=payments)
