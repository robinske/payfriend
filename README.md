# Payment Authorization with Authy

Sample application that shows how to use Authy Push to validate actions like payment transactions.

## Install

    python3 -m venv venv
    . venv/bin/activate

Or on Windows cmd:

    py -3 -m venv venv
    venv\Scripts\activate.bat

Install Requirements:

    pip install -r requirements.txt

## Run

    export FLASK_APP=payfriend
    export FLASK_ENV=development
    flask init-db
    flask run

Or on Windows cmd:

    set FLASK_APP=payfriend
    set FLASK_ENV=development
    flask init-db
    flask run

Open http://127.0.0.1:5000 in a browser.
