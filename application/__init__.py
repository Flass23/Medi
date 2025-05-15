from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import *
from flask_mail import Mail

db = SQLAlchemy()
UPLOAD_PATH = 'static/css/images/profiles/'
UPLOAD_PRODUCTS = 'static/css/images/products/'

login_manager = LoginManager()
login_manager.session_protection = 'strong'
login_manager.login_view = "auth.newlogin"



def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    login_manager.init_app(app)
    app.config['UPLOAD_PATH'] = UPLOAD_PATH

    app.config['UPLOAD_PRODUCTS'] = UPLOAD_PRODUCTS

    db.init_app(app)
    mail = Mail(app)
    mail.init_app(app)

    #routes will go here
    #blueprint registration

    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)
    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')
    from .admin import admin as admin_blueprint
    app.register_blueprint(admin_blueprint, url_prefix='/admin')

    return app
