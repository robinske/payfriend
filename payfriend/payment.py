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
from payfriend.db import get_db
from payfriend.auth import login_required


bp = Blueprint('payments', __name__, url_prefix='/payments')


def push_auth(authy_id, send_to, amount):
    details = {
        "Sending to": send_to,
        "Transaction amount": amount
    }

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
        db = get_db()
        db.execute(
            'INSERT INTO payments (request_id, authy_id, send_to, amount) VALUES (?, ?, ?, ?)',
            (request_id, authy_id, send_to, amount))
        db.commit()
        return request_id
    else:
        return ("Error sending One Touch request", 500)


@bp.route('/callback', methods=["POST"])
def callback():
    authy_id = request.json.get('authy_id')
    request_id = request.json.get('uuid')
    status = request.json.get('status')

    db = get_db()
    payment = db \
        .execute('SELECT * FROM payments WHERE authy_id = ? AND request_id = ?',
                 (authy_id, request_id, )
                 ).fetchone()

    if not payment:
        return ('', 404)

    if status != 'pending':
        db.execute(
            'UPDATE payments SET status = ? WHERE authy_id = ? AND request_id = ?',
            (status, authy_id, request_id, )
        )
        db.commit()
        return ('', 200)

    return ('', 400)


@bp.route('/send', methods=["GET", "POST"])
@login_required
def send():
    if request.method == "POST":
        sendto = request.form['sendto']
        amount = request.form['amount']
        authy_id = session['authy_id']

        request_id = push_auth(authy_id, sendto, amount)
        if request_id:
            return jsonify({
                "success": True,
                "request_id": request_id
            })
        else:
            return jsonify({"success": False})

    return render_template("payments/send.html")


@bp.route('/status', methods=["GET", "POST"])
@login_required
def status():
    """
    Used by AJAX requests to check the OneTouch verification status of a payment
    """
    request_id = request.args.get('request_id')
    payment = get_db() \
        .execute('SELECT * FROM payments WHERE request_id = ?', (request_id,)) \
        .fetchone()

    return payment['status']


@bp.route('/')
@login_required
def list_payments():
    db = get_db()
    payments = db.execute("""
        SELECT *
        FROM payments
        JOIN users
        ON payments.authy_id=users.authy_id
        WHERE users.id = ?
        """, (g.user['id'],)
    ).fetchall()
    return render_template('payments/list.html', payments=payments)
