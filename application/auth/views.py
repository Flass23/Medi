from flask import render_template, redirect, url_for, session, request, flash, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from ..models import User
from flask_bcrypt import Bcrypt
from flask_login import login_user, current_user, login_required
from . import auth

from ..forms import LoginForm, RegistrationForm
from .. import (login_manager, db)
from sqlalchemy.exc import IntegrityError
from flask_mail import Message, Mail
from smtplib import SMTPAuthenticationError
from itsdangerous import URLSafeTimedSerializer, SignatureExpired

s = URLSafeTimedSerializer('ad40898f84d46bd1d109970e23c0360e')

bcrypt = Bcrypt()

mail = Mail()


def adduser(form, is_admin):
    hashed_password = bcrypt.generate_password_hash(form.Password.data).decode('utf-8')
    print(is_admin)
    if is_admin:
        user = User(username=form.username.data,
                    firstname=form.firstName.data,
                    lastname=form.lastName.data,
                    email=form.Email.data,
                    isadmin=True,
                    password=hashed_password
                    )
        return user
    elif not is_admin:
        user = User(username=form.username.data,
                    firstname=form.firstName.data,
                    lastname=form.lastName.data,
                    email=form.Email.data,
                    isadmin=False,
                    password=hashed_password
                    )
        return user
    else:
        return 'something was incorrect'




def send_email(form):
    token = s.dumps(form.Email.data)
    msg = Message('Confirm Email', sender='pitechcorp7@gmail.com', recipients=[form.Email.data])
    link = url_for('auth.confirm_email', token=token, _external=True)
    msg.subject = "Email confirmation"
    msg.body = ('Your email was recently used to sign up for VitalWay Pharmacy, if you didnt do this ignore '
                'this email, But if you did.'
                'The next step is to click the following link to check if Your your email real/ '
                'link is {}. We are really glad you choose us.').format(
        link)
    try:
        mail.send(msg)
        print("message sent")
    except SMTPAuthenticationError as e:
        print('error 1')
        flash("Failed to send email: Authentication Error. Check your email/password settings.")
        print(e)
    except Exception as e:
        flash("Failed to send email due to unexpected error.")
        print('error 2')
        print(e)
    return token



@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))                                                                                                                                 



@auth.route("/register", methods=["POST", "GET"])
def register():
    form = RegistrationForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            ##encrypt password
            isadmin = form.option.data
            token = ''
            if isadmin:
                users = adduser(form, isadmin)
                print("Authenticating...")
                db.session.add(users)
                try:
                    db.session.commit()
                    user = User.query.filter_by(email=form.Email.data).first()
                    if user.confirmed:
                        return redirect(url_for('auth.newlogin'))  ##this is just for testing
                    else:
                        token = send_email(form)
                        return redirect(url_for('auth.unconfirmed', token=token))
                except IntegrityError:
                    db.session.rollback()
                    flash('Username or email already exist')
                except TimeoutError:
                    db.session.rollback()
                    flash('Timeout error')
                    return redirect(url_for('auth.register'))
            else:
                users = adduser(form, isadmin)
                db.session.add(users)

                try:
                    db.session.commit()
                    user = User.query.filter_by(email=form.Email.data).first()
                    if user.confirmed:
                        return redirect(url_for('auth.newlogin'))  ##this is just for testing
                    else:
                        token = send_email(form)
                        return redirect(url_for('auth.unconfirmed', token=token))
                except IntegrityError:
                    db.session.rollback()
                    flash('Username or email already exist')
                    return redirect(url_for('auth.register'))
                # print("Done...")
                flash("Registration done, you can now login")
                return redirect(url_for('auth.newlogin'))
        else:
            flash("Failed to register")
            return redirect(url_for('auth.register'))
    form = RegistrationForm(formdata=None)
    return render_template('auth/register.html', form=form)

@auth.route('/newlogin', methods=['GET', 'POST'])
def newlogin():
    form = LoginForm()

    if form.validate_on_submit():
        if request.method == "POST":
            password = form.password.data
            email = form.email.data
            user = User.query.filter_by(email=email).first()
            if user and bcrypt.check_password_hash(user.password, password):

                if user.isadmin:
                    login_user(user)
                    session["email"] = form.email.data
                    flash("Login Successful")
                    return redirect(url_for('admin.adminpage'))
                else:
                    login_user(user)
                    session["email"] = form.email.data
                    flash("Login Successful")
                    return redirect(url_for('main.home'))

            else:
                flash("Either Password or Email entered is be wrong")
                print("Either Password or Email entered is be wrong")
    return render_template('auth/newlogin.html', form=form)



def confirm_token(token, expiration=3600):
    try:
        email = s.loads(token, max_age=expiration)
        return email
    except Exception:
        return False


from flask import flash, redirect, url_for, render_template
from itsdangerous import SignatureExpired
from flask_login import login_user


@auth.route('/confirm_email/<token>', methods=['GET'])
def confirm_email(token):
    try:
        # Decode the token to retrieve the email
        email = s.loads(token, max_age=5000)

        # Find the user by email (no need to use user_id separately)
        user = User.query.filter_by(email=email).first()

        if user:
            # Mark the user as confirmed
            user.confirmed = True
            flash('Account was successfully confirmed')
            # Log the user in (if necessary)
            login_user(user)
            return redirect(url_for('auth.newlogin'))
        else:
            flash('Something went wrong. User not found.')
            print('Something went wrong: User not found.')
            return redirect(url_for('auth.register'))  # Redirect to a registration or error page

    except SignatureExpired:
        return '<h1>The token expired</h1>'  # Show a message if the token is expired
    except Exception as e:
        flash(f"Error: {str(e)}")
        print(f"Error: {str(e)}")
        return render_template('auth/email/confirm_email.html')

    # In case no valid user is found or other errors
    return render_template('auth/email/confirm_email.html')


@auth.route('/unconfirmed')
def unconfirmed():
    return render_template('auth/email/unconfirmed.html')
    

                                                                                                                                                                                                                                                                                                                                                                                        
                                                                                                                                                                                                                                                                                                
