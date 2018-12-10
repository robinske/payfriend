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


@bp.route('/send', methods=["GET", "POST"])
@login_required
def send():
    form = PaymentForm(request.form)

    if form.validate_on_submit():
        send_to = form.send_to.data
        amount = form.amount.data
        user_id = session['user_id']

        payment = Payment(user_id, send_to, amount)
        db.session.add(payment)
        db.session.commit()

        return redirect(url_for('payments.list_payments'))
    
    return render_template("payments/send.html", form=form)


@bp.route('/', methods=["GET", "POST"])
@login_required
def list_payments():
    user_payments = db.session.query(Payment, User) \
        .join(User) \
        .filter_by(id=session['user_id']) \
        .all()

    payments = []
    for (p, u) in user_payments:
        payment = {
            "email": u.email,
            "send_to": p.send_to,
            "amount": p.amount
        }
        payments.append(payment)

    return render_template('payments/list.html', 
                           payments=payments)
