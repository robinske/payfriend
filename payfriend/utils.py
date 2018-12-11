import phonenumbers
from authy.api import AuthyApiClient
from flask import current_app as app
from flask import flash


def parse_phone_number(full_phone):
    """
    Parses the phone number from E.164 format

    :param full_phone: phone number in E.164 format
    :returns: tuple (country_code, phone)
    """
    pn = phonenumbers.parse(full_phone)
    return (pn.country_code, pn.national_number)


def get_authy_client():
    return AuthyApiClient(app.config['AUTHY_API_KEY'])


def start_verification(country_code, phone, channel='sms'):
    """
    Sends a verification code to the user's phone number 
    via the specified channel

    :param country_code: country code for the phone number
    :param phone: national format phone number
    :param channel: either 'sms' or 'call'
    """
    api = get_authy_client()
    try: 
        verification = api.phones.verification_start(
            phone, country_code, via=channel)
        if verification.ok():
            flash(verification.content['message'])
        else:
            flash(verification.errors()['message'])
    except Exception as e:
        flash("Error sending code: {}".format(e))


def check_verification(country_code, phone, code):
    """
    Validates a verification code

    :param country_code: country code for the phone number
    :param phone: national format phone number
    :param code: verification code from user input
    """
    api = get_authy_client()
    try:
        verification = api.phones.verification_check(
            phone, country_code, code)
        if verification.ok():
            flash(verification.content['message'])
            return True
        else:
            flash(verification.errors()['message'])
    except Exception as e:
        flash("Error validating code: {}".format(e))
    
    return False


def create_authy_user(email, country_code, phone):
    """
    Creates a user with the Authy API

    :param email: email to be associated with the user. 
        Used by the API for account recovery
    :param country_code: country code for the phone number
    :param phone: national format phone number
    :returns: the generated Authy ID
    """
    api = get_authy_client()
    authy_user = api.users.create(email, phone, country_code)
    if authy_user.ok():
        return authy_user.id
    else:
        flash("Error creating Authy user: {}".format(authy_user.errors()))
        return None


def send_sms_auth(authy_id, request_id):
    """
    Sends an SMS one time password (OTP) to the user's phone_number

    :returns (sms_id, errors): tuple of sms_id (if successful)
                               and errors dict (if unsuccessful)
    """
    api = get_authy_client()
    resp = api.users.request_sms(authy_id, {'force': True})
    if resp.ok():
        flash(resp.content['message'])
        return True
    else:
        flash(resp.errors()['message'])
        return False


def check_sms_auth(authy_id, code):
    """
    Validates an one time password (OTP)
    """
    api = get_authy_client()
    try: 
        resp = api.tokens.verify(authy_id, code)
        if resp.ok():
            flash(resp.content['message'])
            return True
        else:
            flash(resp.errors()['message'])
    except Exception as e:
        flash("Error validating code: {}".format(e))
    
    return False


def send_push_auth(authy_id_str, send_to, amount):
    """
    Sends a push authorization with payment details to the user's Authy app

    :returns (request_id, errors): tuple of request_id (if successful)
                                   and errors dict (if unsuccessful)
    """
    details = {
        "Sending to": send_to,
        "Transaction amount": str(amount)
    }

    api = get_authy_client()
    resp = api.one_touch.send_request(
        user_id=int(authy_id_str),
        message="Please authorize payment to {}".format(send_to),
        seconds_to_expire=1200,
        details=details
    )

    if resp.ok():
        request_id = resp.content['approval_request']['uuid']
        return (request_id, {})
    else:
        flash(resp.errors()['message'])
        return (None, resp.errors())