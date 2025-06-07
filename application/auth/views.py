from smtplib import SMTPAuthenticationError

from flask import (session,
                   request)
from flask_bcrypt import Bcrypt  # type: ignore
from flask_login import login_user, current_user, login_required  # type: ignore
from flask_mail import Message, Mail  # type: ignore
from itsdangerous import URLSafeTimedSerializer
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import InternalServerError

from . import auth
from .. import (login_manager, db)
from ..forms import RegistrationForm, PharmacyRegistrationForm
from ..models import User, Pharmacy, DeliveryGuy, Staff

s = URLSafeTimedSerializer('ad40898f84d46bd1d109970e23c0360e')

bcrypt = Bcrypt()

mail = Mail()



def adduser(form):
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
def send_email_(form):
    try:
        token = s.dumps(form.email.data)
        msg = Message('Confirm Email', sender='pitechcorp7@gmail.com', recipients=[form.email.data])
        link = url_for('auth.confirm_email', token=token, _external=True)
        msg.subject = "Confirm your MediCart pharmacy account"
        msg.body = (
            "Hello,\n\n"
            "Thank you for registering your pharmacy with MediCart.\n\n"
            "To complete your registration and activate your account, please confirm your email address by clicking the link below:\n\n"
            "{}\n\n"
            "If you did not initiate this registration, you can safely ignore this email.\n\n"
            "We look forward to helping you connect with more customers and streamline your operations.\n\n"
            "Best regards,\n"
            "The MediCart Team"
        ).format(link)
    except InternalServerError:
        print('error 1')
        flash("Failed to send email due to unexpected error.")
        return redirect(url_for("auth.newlogin"))
    except InterruptedError:
        print('error 1')
        flash("Failed to send email due to unexpected error.")
        return redirect(url_for("auth.newlogin"))

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


def send_email(form):
    token = s.dumps(form.Email.data)
    msg = Message('Confirm Email', sender='pitechcorp7@gmail.com', recipients=[form.Email.data])
    link = url_for('auth.confirm_email', token=token, _external=True)
    msg.subject = "Confirm your MediCart email"
    msg.body = (
        f"Hi {form.username.data},\n\n"
        "We noticed your email was recently used to sign up for MediCart. If this wasn't you, feel free to ignore this message.\n\n"
        "If you did sign up, please confirm your email address by clicking the link below:\n\n"
        "{}\n\n"
        "Thanks for choosing MediCart — we're excited to have you on board!\n\n"
        "The MediCart Team"
    ).format(link)
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
    elif user_type == 'delivery_guy':
        return DeliveryGuy.query.get(int(user_id))
    elif user_type == 'pharmacy_staff':
        return Staff.query.get(int(user_id))
    return None


@auth.route("/registerpharmacy", methods=['POST', 'GET'])
def registerpharmacy():
    form = PharmacyRegistrationForm()
    if request.method == "POST":
        if form.validate_on_submit():
            token = ""
            testi = Pharmacy.query.filter_by(email=form.email.data).first()
            if testi:
                flash('Email already exists')
                return redirect(url_for('auth.registerpharmacy'))
            new_pharmacy = addpharma(form)
            if new_pharmacy:
                new_pharmacy.latitude = form.lat.data
                new_pharmacy.longitude = form.lon.data
                db.session.add(new_pharmacy)
                try:
                    db.session.commit()
                    #check if pharmacy successfully committed
                    reg_pharma = Pharmacy.query.filter_by(email=form.email.data).first()
                    if reg_pharma and reg_pharma.confirmed:
                        flash('Account added successfully, login and fill further business details')
                        return redirect(url_for('auth.newlogin'))
                    else:
                        token = send_email_(form)
                        flash('An email was sent to you email account.', 'success')
                        return redirect(url_for('auth.unconfirmed', token=token))
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
            userq = User.query.filter_by(email=form.Email.data).first()
            if userq:
                flash('Email already exists')
                return redirect(url_for('auth.register'))
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
            staff = Staff.query.filter_by(email=form.email.data).first()

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
            elif staff and bcrypt.check_password_hash(staff.password, form.password.data):
                login_user(staff)
                session['user_type'] = staff.role
                session['pharmacy_id'] = staff.pharmacy_id
                session['email'] = staff.email
                flash(f'Login Successful, welcome {staff.names}')
                return redirect(url_for('pharmacy.adminpage'))
            else:
                flash("Invalid login credentials", 'danger')
    return render_template('auth/newlogin.html', form=form, formpharm=formpharma)


from itsdangerous import BadSignature

def confirm_token(token, expiration=86400):
    try:
        email = s.loads(token, max_age=expiration)
        return email
    except SignatureExpired:
        # Token is valid but expired
        print("Token expired.")
        return False
    except BadSignature:
        # Token is invalid
        print("Invalid token.")
        return False



from flask import flash, redirect, url_for, render_template
from itsdangerous import SignatureExpired
from flask_login import login_user # type: ignore

from ..forms import LoginForm, Set_PharmacyForm

@auth.route('/confirm_email/<token>', methods=['GET'])
def confirm_email(token):
    form = LoginForm()
    formpharma = Set_PharmacyForm()
    try:
        email = s.loads(token, max_age=5000)
        user = User.query.filter_by(email=email).first()
        pham = Pharmacy.query.filter_by(email=email).first()

        if user:
            user.confirmed = True
            db.session.commit()
            flash('Your account has been successfully confirmed. You can now log in.', 'success')
            return render_template('auth/newlogin.html', form=form, formpharm=formpharma)

        elif pham:
            pham.confirmed = True
            db.session.commit()
            flash('Your pharmacy account has been successfully confirmed. You can now log in.', 'success')
            return render_template('auth/newlogin.html', form=form, formpharm=formpharma)

        else:
            flash('User not found.', 'danger')
            return redirect(url_for('auth.register'))

    except SignatureExpired:
        return '<h1>The confirmation link has expired.</h1>'
    except Exception as e:
        flash(f"Error: {str(e)}", 'danger')
        return render_template('auth/email/confirmed.html')

@auth.route('/unconfirmed')
def unconfirmed():
    return render_template('auth/email/unconfirmed.html')
    

                                                                                                                                                                                                                                                                                                                                                                                        
                                                                                                                                                                                                                                                                                                
