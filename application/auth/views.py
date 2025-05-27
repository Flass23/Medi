from flask import render_template, redirect, url_for, session, request, flash, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from ..models import User, Pharmacy, DeliveryGuy
from flask_bcrypt import Bcrypt # type: ignore
from flask_login import login_user, current_user, login_required # type: ignore
from . import auth

from ..forms import LoginForm, RegistrationForm, PharmacyRegistrationForm, Set_PharmacyForm
from .. import (login_manager, db)
from sqlalchemy.exc import IntegrityError
from flask_mail import Message, Mail # type: ignore
from smtplib import SMTPAuthenticationError
from itsdangerous import URLSafeTimedSerializer, SignatureExpired

s = URLSafeTimedSerializer('ad40898f84d46bd1d109970e23c0360e')

bcrypt = Bcrypt()

mail = Mail()



def adduser(form, option):
    hashed_password = bcrypt.generate_password_hash(form.Password.data).decode('utf-8')
    user = User(username=form.username.data,
                        firstname=form.firstName.data,
                        lastname=form.lastName.data,
                        email=form.Email.data,
                        isadmin=False,
                        password=hashed_password
                        )
    return user
def addpharma(form):
    hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')

    pharma = Pharmacy(
                name=form.pharmacy_name.data,
                licence_num=form.licence_number.data,
                email=form.email.data,
                phone=form.phone.data,
                address=form.address.data,
                openinghours=form.opening_hours_and_days.data,
                password=hashed_password)
    return pharma


def send_email(form):
    token = s.dumps(form.Email.data)
    msg = Message('Confirm Email', sender='pitechcorp7@gmail.com', recipients=[form.Email.data])
    link = url_for('auth.confirm_email', token=token, _external=True)
    msg.subject = "Email confirmation"
    msg.body = ('Your email was recently used to sign up for MediCart, if it was not you simply ignore this email'
                ', But if you did.'
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
        print(e)
        return redirect(url_for("auth.newlogin"))
    return token

    
@login_manager.user_loader
def load_user(user_id):
    user_type = session.get('user_type')
    if user_type == 'pharmacy':
        return Pharmacy.query.get(int(user_id))
    elif user_type == 'customer':
        return User.query.get(int(user_id))
    elif user_type == 'delivery':
        return DeliveryGuy.query.get(int(user_id))
    return None                                                                                                                                 


@auth.route("/registerpharmacy", methods=['POST', 'GET'])
def registerpharmacy():
    form = PharmacyRegistrationForm()
    if request.method == "POST":
        if form.validate_on_submit():
            token = ""
            new_pharmacy = addpharma(form)
            if new_pharmacy:
             #   new_pharmacy.latitude = form.lat.data
              #  new_pharmacy.longitude = form.lon.data
                db.session.add(new_pharmacy)
                try:
                    db.session.commit()
                    #check if pharmacy successfully committed
                    reg_pharma = Pharmacy.query.filter_by(email=form.email.data).first()
                    if reg_pharma:
                        flash('Account added successfully, login and fill further business details')
                        return redirect(url_for('auth.newlogin'))
                    else:
                        flash('There was an error creating your account. We are working on on this. Try again later.')
                except IntegrityError:
                    db.session.rollback()
                    flash('Check you input the correct details.')
                    return redirect(url_for('auth.registerpharmacy'))
            else:
                flash('Could not add your pharmacy, please try again')
                return redirect(url_for('auth.registerpharmacy'))
    return render_template('auth/registerphar.html', form=form)

    

@auth.route("/register", methods=["POST", "GET"])
def register():
    form = RegistrationForm()
    if request.method == "POST":
        if form.validate_on_submit():
            token = ""
            users = adduser(form)
            if users:
                db.session.add(users)
                try:
                    db.session.commit()
                    user = User.query.filter_by(email=form.Email.data).first()
                    if user.confirmed:
                        return redirect(url_for('auth.newlogin'))
                    else:
                        token = send_email(form)
                        flash('An email was sent to you email account.', 'success')
                        return redirect(url_for('auth.unconfirmed', token=token))
                except IntegrityError:
                    db.session.rollback()
                    flash('Username or email already exist')
                    return redirect(url_for('auth.register'))
                except TimeoutError:
                    flash('Timeout Error!')
                    return redirect(url_for('auth.register'))
            else:
                flash('User could not be created successfully')
                return redirect(url_for('auth.register'))
        else:
            flash('Form failed to validate on submit, please try again')
    return render_template('auth/register.html', form=form)

@auth.route('/newlogin', methods=['GET', 'POST'])
def newlogin():
    form = LoginForm()
    formpharma = Set_PharmacyForm()
    if form.validate_on_submit():
        if request.method == "POST":
            user = User.query.filter_by(email=form.email.data).first()
            pharmacy = Pharmacy.query.filter_by(email=form.email.data).first()
            delivery_guy = DeliveryGuy.query.filter_by(email=form.email.data).first()

            if user and bcrypt.check_password_hash(user.password, form.password.data):
                if user.isadmin:
                    login_user(user)
                    session["email"] = form.email.data
                    session['user_type'] = 'admin'
                    flash(f"Login Successful, welcome {user.username}")
                    return "<h1>Working on the admin page</h1>"
                else:
                    login_user(user)
                    session["email"] = form.email.data
                    session['user_type'] = 'customer'
                    flash(f'Login Successful, welcome {user.username}')
                    return redirect(url_for('main.home'))

            elif pharmacy and bcrypt.check_password_hash(pharmacy.password, form.password.data):
                login_user(pharmacy)
                session['user_type'] = 'pharmacy'
                session['pharmacy_id'] = pharmacy.id
                session['email'] = pharmacy.email
                flash(f'Login Successful, welcome {pharmacy.name}')
                return redirect(url_for('pharmacy.adminpage'))

            elif delivery_guy and bcrypt.check_password_hash(delivery_guy.password, form.password.data):
                login_user(delivery_guy)
                session['user_type'] = 'delivery_guy'
                session['delivery_guy_id'] = delivery_guy.id
                session['email'] = delivery_guy.email
                flash(f'Login Successful, welcome {delivery_guy.names}')
                return redirect(url_for('delivery.dashboard'))  # <-- create this route for delivery guy dashboard

            else:
                flash("Invalid login credentials", 'danger')

    return render_template('auth/newlogin.html', form=form, formpharm=formpharma)


def confirm_token(token, expiration=3600):
    try:
        email = s.loads(token, max_age=expiration)
        return email
    except Exception:
        return False


from flask import flash, redirect, url_for, render_template
from itsdangerous import SignatureExpired
from flask_login import login_user # type: ignore


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
            # Log the user in
            return redirect(url_for('auth.newlogin'))
        else:
            flash('User not found.')
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
    

                                                                                                                                                                                                                                                                                                                                                                                        
                                                                                                                                                                                                                                                                                                
