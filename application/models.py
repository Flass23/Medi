
import pytz
from flask_login import UserMixin  # type: ignore
from itsdangerous import TimedSerializer
from flask import current_app

from . import login_manager, db
from zoneinfo import ZoneInfo
import secrets
from datetime import datetime
from flask_migrate import Migrate  # type: ignore



def get_localTime(self):
    tz = pytz.timezone("Africa/Johannesburg")
    return datetime.now(tz)

def get_orderid():
    return "ORD-"+ secrets.token_hex(5).upper()




class Pharmacy(UserMixin, db.Model):
    __tablename__ = "pharmacy"
    __searchable__ = ['name', 'address']
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(50), nullable=False)
    address = db.Column(db.String(200))
    licence_num = db.Column(db.String(120), unique=True, nullable=False)
    openinghours = db.Column(db.String(100), nullable=False, default='09:00 to 18:30')
    registered_on = db.Column(db.DateTime, server_default=db.func.now())
    password = db.Column(db.String(200), nullable = False)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float) 

    ## payments from research
    
    #mpesa
    mpesa_shortcode = db.Column(db.String(100), nullable=False, default="None")
    mpesa_consumer_key = db.Column(db.String(200), nullable=False, default="None")
    mpesa_consumer_secret = db.Column(db.String(200), nullable=False, default="None")
    mpesa_pass_key = db.Column(db.String(200), nullable=False, default="None")
    #ecocash
    ecocash_api_key = db.Column(db.String(200), nullable=False, default="None")
    ecocash_api_secret = db.Column(db.String(100), nullable=False, default="None")
    ecocash_short_code = db.Column(db.String(100), nullable=False, default="None")
    
    pharma_logo = db.Column(db.String(100), nullable=True)
    registered_on = db.Column(db.DateTime, server_default=db.func.now())
    users = db.relationship('User', backref='pharmacy', lazy=True)  # a user will be tied to a pharmacy store they create
    products = db.relationship('Product', backref='pharmacy', lazy=True)
    orders = db.relationship('Order', backref='pharmacy', lazy=True)
    sales = db.relationship('Sales', backref='pharmacy', lazy=True)
    users = db.relationship('User', back_populates='pharmacy')
    confirmed = db.Column(db.Boolean, nullable=False, default=False)

    def __init__(self, name, licence_num, password, email, phone, address, openinghours):
        self.name = name
        self.email = email
        self.phone = phone
        self.address = address
        self.openinghours = openinghours
        self.licence_num = licence_num
        self.password = password


def update_warning(self, quantity):

    self.quantity = quantity
    if quantity < 10:

        db.session.commit()
        warning = 'low quantity'
        return warning
    else:
        return "good quantity"


class Product(db.Model):
    __searchable__ = ['productname', 'description', 'category']
    id = db.Column(db.Integer, primary_key=True)
    productname = db.Column(db.String(10), nullable=False)
    price = db.Column(db.Float, nullable=False)
    pictures = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer)
    description = db.Column(db.String(100), nullable=False)
    cart_items = db.relationship('CartItem', backref='product', lazy=True)
    order_items = db.relationship('OrderItem', backref='product', lazy=True)
    warning = db.Column(db.String(50), default=update_warning(quantity))
    category = db.Column(db.String(50), nullable=True, default='Uncategorized')
    pharmacy_id = db.Column(db.Integer, db.ForeignKey('pharmacy.id'))






class Sales(db.Model):
    __searchable__ = ['order_id', 'date_', 'user_id']
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_user_id'), nullable=False)
    product_name = db.Column(db.String(30), nullable=False)
    product_id = db.Column(db.Integer, nullable=False)
    date_ = db.Column(db.DateTime, nullable=False, default=get_localTime)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    pharmacy_id = db.Column(db.Integer, db.ForeignKey('pharmacy.id', name='fk_pharmact_id'), nullable=False)

class User(UserMixin, db.Model):
    __searchable__ = ['username', 'firstname', 'email', 'lastname']
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(18), nullable=False, unique=True)
    firstname = db.Column(db.String(30), nullable=False)
    lastname = db.Column(db.String(40), nullable=False)
    email = db.Column(db.String(30), unique=True, nullable=False)
    image_file = db.Column(db.String(140), nullable=True, default="account.png")
    password = db.Column(db.String(40), nullable=False, unique=False)
    isadmin = db.Column(db.Boolean, nullable=False, default=False)
    carts = db.relationship('Cart', backref='user', lazy=True)
    orders = db.relationship('Order', backref='user', lazy=True)
    confirmed = db.Column(db.Boolean, nullable=False, default=False)
    loyalty_points = db.Column(db.Integer, default=0)
    pharmacy_id = db.Column(db.Integer, db.ForeignKey('pharmacy.id'))
    pharmacy = db.relationship('Pharmacy', back_populates='users')

    def generate_confirmation_token(self, expiration=4600):
        s = TimedSerializer(current_app.config['SECRET_KEY'], expiration)
#       serializer = TimedSerializer('your_secret_key', expires_in=3600)
        return s.dumps({'confirm': self.id})

    def confirm(self, token):
        s = TimedSerializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('confirm') != self.id:
            return False
        self.confirmed = True
        db.session.add(self)
        return True

    def __init__(self, username, firstname, lastname, email, isadmin, password):
        self.username = username
        self.firstname = firstname
        self.lastname = lastname
        self.email = email
        self.isadmin = isadmin
        self.password = password


class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cart_id = db.Column(db.ForeignKey('cart.id'), nullable=False)
    product_id = db.Column(db.ForeignKey('product.id', name='fk_prod_id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

class Order(db.Model):
    __searchable__ = ['order_id', 'location', 'user_id', 'status', 'payment', 'user_email']
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(10), nullable=False, default=get_orderid)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_userid_order'), nullable=False)
    create_at = db.Column(db.DateTime, default=get_localTime)
    location = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(40), nullable=False, default='Pending')
    payment = db.Column(db.String(40), nullable=False, default='None')
    transactionID = db.Column(db.String(90), default='Cash')
    user_email = db.Column(db.String(30), nullable=False)
    order_items = db.relationship('OrderItem', backref='order', lazy=True)
    pharmacy_id = db.Column(db.Integer, db.ForeignKey('pharmacy.id', name='fk_pharma_order'), nullable=False)
    source_pharmacy = db.Column(db.String(120))
    taken_by = db.Column(db.Integer, db.ForeignKey('deliveryguy.id', name='fk_pharma_order_deliver'))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    screenshot = db.Column(db.String(120))

    def get_localTime(self):
        return self.create_at.astimezone(ZoneInfo("Africa/Johannesburg"))

    def getpharmacyname(self, pharmacy_id):
        return Pharmacy.query.get_or_404(pharmacy_id) 


class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.ForeignKey('user.id', name='fk_cartuser'), nullable=False)
    date_created = db.Column(db.DateTime, default=get_localTime)
    cart_items = db.relationship('CartItem', backref='cart', lazy=True)
    pharmacy_id = db.Column(db.Integer, db.ForeignKey('pharmacy.id', name='fk_pharma_order'), nullable=False)
    def calculate_total(self):
       return self.order_items.product_price * self.order_items.quantity


class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.ForeignKey('order.id', name='fk_order_item'), nullable=False)
    product_id = db.Column(db.ForeignKey('product.id', name='fk_prod_item'), nullable=False)
    product_name = db.Column(db.String(20), nullable=False)
    product_price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

class DeliveryGuy(db.Model, UserMixin):
    __tablename__ = 'deliveryguy'
    id = db.Column(db.Integer, primary_key=True)
    names = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(30), unique=True, nullable=False)
    image_file = db.Column(db.String(140), nullable=True, default="account.png")
    password = db.Column(db.String(40), nullable=False, unique=False)
    deliveries = db.relationship('Delivery', back_populates='delivery_guy',overlaps='delivery_guy', lazy=True) 
    isfree = db.Column(db.Boolean, default=True)  

class Delivery(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    customer_name = db.Column(db.String(120))
    address = db.Column(db.String(100))
    status = db.Column(db.String(50), default='Out for delivery')
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    order_id = db.Column(db.String(30), db.ForeignKey('order.id', name='fk_delivery_order'))
    orders = db.relationship('Order', backref='delivery', lazy=True)
    delivery_guy_id = db.Column(db.Integer, db.ForeignKey('deliveryguy.id', name='fk_delivery_guy'))
    delivery_guy = db.relationship('DeliveryGuy', back_populates='deliveries', overlaps='deliveries', lazy=True)

    def to_dict(self):
        return {
        "id": self.id,
        "customer_name": self.customer_name,
        "address": self.address,
        "status": self.status,
        "latitude": self.latitude,
        "longitude": self.longitude,
        "order_id": self.order_id
    }
