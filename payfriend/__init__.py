import os

from flask import Flask, render_template, g

from dotenv import load_dotenv, find_dotenv


def create_app(test_config=None):
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        # store the database in the instance folder
        DATABASE=os.path.join(app.instance_path, 'payfriend.sqlite'),
    )

    load_dotenv(find_dotenv())

    try:
        # Secret key
        app.secret_key = os.environ['SECRET_KEY']

        # Authy API key
        app.config['AUTHY_API_KEY'] = os.environ['AUTHY_API_KEY']
    except KeyError:
        raise Exception(
            'Missing environment variables. See .env.example for details')

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # register the database commands
    from payfriend import db
    db.init_app(app)

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/users')
    def list_users():
        database = db.get_db()
        users = database.execute('SELECT * FROM users').fetchall()
        return render_template('users.html', users=users)

    # apply the blueprints to the app
    from payfriend import auth, payment
    app.register_blueprint(payment.bp)
    app.register_blueprint(auth.bp)

    # add error routing
    from payfriend import error
    app.register_error_handler(401, error.unauthorized)
    app.register_error_handler(403, error.forbidden)
    app.register_error_handler(404, error.page_not_found)
    app.register_error_handler(500, error.internal_error)

    return app
