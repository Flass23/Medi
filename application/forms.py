from flask_wtf import FlaskForm # type: ignore
from flask_wtf.file import FileField, FileAllowed # type: ignore
from wtforms import StringField, HiddenField,FloatField, PasswordField, SubmitField, BooleanField, TextAreaField, IntegerField,SelectField # type: ignore
from wtforms.validators import DataRequired, Length, Email # type: ignore

class PharmacyRegistrationForm(FlaskForm):
    pharmacy_name = StringField('Pharmacy Name', validators=[DataRequired()])
    licence_number = StringField('Licence Number', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired()])
    phone = StringField('Phone Number', validators=[DataRequired()])
    address = StringField('Address', validators=[DataRequired()])
    opening_hours_and_days = StringField('Opening Hours', validators=[DataRequired()])
    lat = FloatField('Latitude')
    lon = FloatField('Longitude')
    password = PasswordField('Password', validators=[DataRequired()])
    
    submit = SubmitField('Register Pharmacy')


class UpdateForm(FlaskForm):
    picture = FileField('Profile Picture')
    username = StringField("Username",
                           validators=[DataRequired(), Length(min=3, max=18)])
    firstName = StringField('Firstname',
                            validators=[DataRequired(),
                                        Length(min=2, max=16)])
    lastName = StringField('Lastname',
                           validators=[DataRequired(),
                                       Length(min=2, max=16)])

    Email = StringField('Email',
                        validators=[DataRequired(),
                                    Length(min=5, max=30)])

    submit = SubmitField('Update')

class Search(FlaskForm):
    keyword = StringField('keyword')
    submit = SubmitField('Search')


class RegistrationForm(FlaskForm):
    username = StringField("Username",
                           validators=[DataRequired(), Length(min=3, max=18)])
    firstName = StringField('Firstname',
                            validators=[DataRequired(),
                                        Length(min=2, max=16)])
    lastName = StringField('Lastname',
                           validators=[DataRequired(),
                                       Length(min=2, max=16)])
    
    Email = StringField('Email',
                        validators=[DataRequired(),
                                    Length(min=5, max=30)])

    Password = PasswordField('Password',
                             validators=[DataRequired()])

    submit = SubmitField('Register')

class Set_PharmacyForm(FlaskForm):
    pharmacy = SelectField('Choose Pharmacy', choices=[], coerce=int, validators=[DataRequired()], default=-1)
    submit = SubmitField('Continue')



class LoginForm(FlaskForm):
    email = StringField('Email',
                        validators=[DataRequired(), Length(min=5, max=30)])
    password = PasswordField('Password',
                             validators=[DataRequired()])

    submit = SubmitField('Login')

class CartlistForm(FlaskForm):
    submit = SubmitField('AddtoCart')


class removefromcart(FlaskForm):
    submit = SubmitField("-")


class clearcart(FlaskForm):
    submit = SubmitField('Clear Cart')

class addmore(FlaskForm):
    submit = SubmitField("+")

class update(FlaskForm):
    newname = StringField("New Name")
    newprice = FloatField("New Price: ")
    quantity = IntegerField("Quantity")
    newdescription = StringField("New Description: ")
    category = SelectField('Category', validators=[DataRequired()], choices=[('Prescription Medication', 'Prescription Medication')
                                                                        ,('Over-The-Counter', 'Over-The-Counter')
                                                                        ,('Supplements & Vitamins', 'Supplements & Vitamins')
                                                                        ,('Personal Care & Hygiene', 'Personal Care & Hygiene')
                                                                        ,('Medical Supplies & Devices', 'Medical Supplies & Devices'),
                                                                        ('Baby Care', 'Baby Care'),
                                                                        ('Health & Wellness', 'Health & Wellness'),
                                                                        ('Cosmetics & Beauty', 'Cosmetics & Beauty'),
                                                                        ('Alternative & Herbal Remedies', 'Alternative & Herbal Remedies'),
                                                                        ('Others', 'Others')

                                                                             ])
    picture = FileField('Upload Product Picture', validators=[FileAllowed(['jpg', 'jpeg', 'png', 'gif'])])

    submit = SubmitField("Commit Update")


class confirmpurchase(FlaskForm):
    payment = SelectField("Payment Method", validators=[DataRequired()], choices=[('Mpesa', 'Mpesa'), ('Ecocash', 'Ecocash')])
    transid = StringField('Enter your Mpesa/Ecocash Transaction ID')
    payment_number = StringField('Phone Number Used for payment')
    latitude = HiddenField('Latitude')
    logitude = HiddenField('Longitude')
    payment_screenshot = FileField('Upload Proof of Payment', validators=[FileAllowed(['jpg', 'jpeg', 'png'])])

    drop_address = StringField('Delivery Address (be specific as possible - room number, village, landmarks, nearby places))')
    submit = SubmitField("Buy Cart")

class upload_prescription(FlaskForm):
    file = FileField('Upload Prescription', validators=[FileAllowed(['jpg', 'jpeg', 'png'])])

class redeempoints(FlaskForm):
    redeem = BooleanField('Redeem 150 points.')
    submit = SubmitField("Calculate Amount Payable")

class ProductForm(FlaskForm):
    product_name = StringField("Product Name", validators=[DataRequired()])
    product_description = StringField("Description", validators=[DataRequired()])
    product_quantity = IntegerField("Quantity",  validators=[DataRequired()])
    product_price = FloatField("Price", validators=[DataRequired()])
    product_pictures = FileField('Upload Product Picture', validators=[FileAllowed(['jpg', 'jpeg', 'png', 'gif'])])
    category = SelectField('Category', validators=[DataRequired()], choices=[('Prescription Medication', 'Prescription Medication')
                                                                        ,('Over-The-Counter', 'Over-The-Counter')
                                                                        ,('Supplements & Vitamins', 'Supplements & Vitamins')
                                                                        ,('Personal Care & Hygiene', 'Personal Care & Hygiene')
                                                                        ,('Medical Supplies & Devices', 'Medical Supplies & Devices'),
                                                                        ('Baby Care', 'Baby Care'),
                                                                        ('Health & Wellness', 'Health & Wellness'),
                                                                        ('Cosmetics & Beauty', 'Cosmetics & Beauty'),
                                                                        ('Alternative & Herbal Remedies', 'Alternative & Herbal Remedies'),
                                                                        ('Others', 'Others')

                                                                             ])
    submit = SubmitField("Add Product")


class updatestatusform(FlaskForm):
    status = SelectField('Status', validators=[DataRequired()], choices=[('Approved', 'Approved'),
                                                                        ('Ready ', 'Ready'),
                                                                        ('Out for Deliver', 'Out for Delivery'), 
                                                                        ('Delivered', 'Delivered'),
                                                                        ('Cancelled', 'Cancelled')])
    submit = SubmitField('Update Status')


class updatedeliveryform(FlaskForm):
    status = SelectField('Status', validators=[DataRequired()], choices=[ ('Delivered', 'Delivered'),
                                                                        ('Cancelled', 'Cancelled')])
    delivery_prove = FileField('Customer Photo With their Order',
                               validators=[FileAllowed(['jpg', 'jpeg', 'png'])])
    submit = SubmitField('Update Delivery Status')



class addstaffform(FlaskForm):
    names = StringField('Names:', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired()])
    role = SelectField('Assign Role', validators=[DataRequired()], choices=[('Manager', 'Manager'), ('Cashier', 'Cashier')])
    password = StringField('Password', validators=[DataRequired()])
    submit = SubmitField('Add Staff')

class UpdatePharmacyForm(FlaskForm):
    mpesacode = StringField("Mpesa Till No.", validators=[DataRequired()])
    ecocashcode = StringField("Ecocash Till No.", validators=[DataRequired()])
    submit = SubmitField('Save')
