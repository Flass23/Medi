import os
from application import create_app, db
from application.models import User
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import IntegrityError
from livereload import Server

app = create_app(os.getenv('FLASK_CONFIG') or 'default')

migrate = Migrate(app, db)


def make_shell_context():
    return dict(app=app, db=db)



if __name__ == '__main__':
    server = Server(app.wsgi_app)
    #server.serve(port=8000, host='0.0.0.0')

    app.run(host='0.0.0.0', port=8080)
