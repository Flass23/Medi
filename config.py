import os
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = 'ad40898f84d46bd1d109970e23c0360e2003'
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True
    ALLOWED_EXTENSIONS = {'png', 'jpeg', 'jpg', 'gif'}
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_sESSION_LIFETIME = 1800

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    DEBUG = True
    MAIL_SERVER='smtp.gmail.com'
    MAIL_PORT=587
    MAIL_USE_TLS = True
    #MAIL_USE_SSL=True
    MAIL_USERNAME = 'pitechcorp7@gmail.com'
    MAIL_PASSWORD = 'rljm azij wply ihrp'
    UPLOAD_PATH = 'static/css/images/profiles/'
    UPLOAD_PRODUCTS = 'static/css/images/products/'
    UPLOAD_DELIVERY = 'static/css/images/delivery/'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
                              'sqlite:///' + os.path.join(basedir, 'data-dev.sqlite.db')



class ProductionConfig(Config):
    MAIL_SERVER='smtp.gmail.com'
    MAIL_PORT=465
    MAIL_USE_TLS = False
    MAIL_USE_SSL=True
    MAIL_USERNAME = 'pitechcorp7@gmail.com'
    MAIL_PASSWORD = 'rljm azij wply ihrp'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
                              'sqlite:///' + os.path.join(basedir, 'data.sqlite')


config = {
 'development': DevelopmentConfig,
 'production': ProductionConfig,
 'default': DevelopmentConfig
}
