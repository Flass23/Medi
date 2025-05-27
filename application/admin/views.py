from flask import render_template, redirect, url_for, request, flash, current_app, jsonify,session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, extract, or_
from ..models import User, Product, Sales, Order, Cart, OrderItem, Pharmacy
from datetime import datetime,timedelta
import calendar
from flask_login import login_required, current_user, logout_user,  LoginManager # type: ignore
from . import admin
from ..forms import addmore, removefromcart, UpdateForm, ProductForm, \
    updatestatusform, update,CartlistForm, Search
from ..models import db
import os
import secrets
from PIL import Image
from flask import current_app
import plotly.graph_objs as go # type: ignore
import plotly.offline as plot # type: ignore



def save_product_picture(file):
    # Set the desired size for resizing
    size = (300, 300)

    # Generate a random hex string for the filename
    random_hex = secrets.token_hex(9)

    # Get the file extension
    _, f_ex = os.path.splitext(file.filename)

    # Generate the final filename (random + extension)
    post_img_fn = random_hex + f_ex

    # Define the path to save the file (UPLOAD_PRODUCTS should be configured in your Flask app)
    post_image_path = os.path.join(current_app.root_path, current_app.config['UPLOAD_PRODUCTS'], post_img_fn)

    try:
        # Open the image
        img = Image.open(file)

        # Resize the image to fit within the size (thumbnail)
        img.thumbnail(size)

        # Save the resized image
        img.save(post_image_path)

        return post_img_fn  # Return the filename to store in the database
    except Exception as e:
        # If an error occurs during image processing, handle it
        print(f"Error saving image: {e}")
        return None

login_manager = LoginManager()
login_manager.session_protection = 'strong'
login_manager.login_view = 'auth.newlogin'

@login_manager.user_loader
def load_user(user_id):
    user_type = session.get('user_type')
    if user_type == 'pharmacy':
        return Pharmacy.query.get(int(user_id))
    elif user_type == 'customer':
        return User.query.get(int(user_id))
    return None 
