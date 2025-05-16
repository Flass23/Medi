from enum import unique
from zoneinfo import ZoneInfo

import pytz
from flask_login import UserMixin
from itsdangerous import TimedSerializer
from flask import current_app

from . import login_manager, db
from zoneinfo import ZoneInfo
import secrets
from datetime import datetime
from flask_migrate import Migrate



def get_localTime(self):
    tz = pytz.timezone("Africa/Johannesburg")
    return datetime.now(tz)

def get_orderid():
    return "ORD-"+ secrets.token_hex(5).upper()

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
    warning = db.Column(db.String(50), default='quantity good')
    category = db.Column(db.String(50), nullable=True, default='Uncategorized')



class Sales(db.Model):
    __searchable__ = ['order_id', 'date_', 'user_id']
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_name = db.Column(db.String(30), nullable=False)
    product_id = db.Column(db.Integer, nullable=False)
    date_ = db.Column(db.DateTime, nullable=False, default=get_localTime)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

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
    product_id = db.Column(db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

class Order(db.Model):
    __searchable__ = ['order_id', 'location', 'user_id', 'status', 'payment', 'user_email']
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(10), nullable=False, default=get_orderid)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    create_at = db.Column(db.DateTime, default=get_localTime)
    location = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(40), nullable=False, default='Pending')
    payment = db.Column(db.String(40), nullable=False, default='Pick up')
    transactionID = db.Column(db.String(90), default='Cash')
    user_email = db.Column(db.String(30), nullable=False)
    order_items = db.relationship('OrderItem', backref='order', lazy=True)

    def get_localTime(self):
        return self.create_at.astimezone(ZoneInfo("Africa/Johannesburg"))


class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.ForeignKey('user.id'), nullable=False)
    date_created = db.Column(db.DateTime, default=get_localTime)
    cart_items = db.relationship('CartItem', backref='cart', lazy=True)

    def calculate_total(self):
       return self.order_items.product_price * self.order_items.quantity

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.ForeignKey('product.id'), nullable=False)
    product_name = db.Column(db.String(20), nullable=False)
    product_price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)


