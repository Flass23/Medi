import os
import secrets
from flask import render_template, redirect, request, url_for, flash, session, jsonify
from flask_login import login_required, current_user, logout_user # type: ignore
from sqlalchemy.exc import IntegrityError
from application.models import Delivery, DeliveryGuy
from sqlalchemy import desc
from PIL import Image
from . import delivery
from ..forms import *
from ..models import *

@login_manager.user_loader
def load_user(user_id):
    user_type = session.get('user_type')
    if user_type == 'pharmacy':
        return Pharmacy.query.get(int(user_id))
    elif user_type == 'customer':
        return User.query.get(int(user_id))
    elif user_type == "delivery_guy":
        return DeliveryGuy.query.get(int(user_id))
    return None 

def save_delivery_picture(file):
    # Set the desired size for resizing
    size = (300, 300)

    # Generate a random hex string for the filename
    random_hex = secrets.token_hex(9)

    # Get the file extension
    _, f_ex = os.path.splitext(file.filename)

    # Generate the final filename (random + extension)
    post_img_fn = random_hex + f_ex

    # Define the path to save the file (UPLOAD_PRODUCTS should be configured in your Flask app)
    post_image_path = os.path.join(current_app.root_path, current_app.config['UPLOAD_DELIVERY'], post_img_fn)

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


@delivery.route('/dashboard', methods=["GET", "POST"])
@login_required
def dashboard():
    pharmacy = Pharmacy.query.get_or_404(session.get('pharmacy_id'))
    formpharm = Set_PharmacyForm()
    formpharm.pharmacy.choices=[(-1, "Select a Pharmacy")] + [(p.id, p.name) for p in Pharmacy.query.all()]

    #the dashboard will show orders
    ready_orders = Order.query.filter(Order.status=='Ready ', Order.pharmacy_id==session.get('pharmacy_id')).order_by(desc(Order.create_at)).all()

    return render_template('delivery/deliverydashboard.html',formpharm=formpharm, pharmacy=pharmacy, ready_orders=ready_orders)

@delivery.route('/takeorder/<int:order_id>', methods=["GET", "POST"])
@login_required
def takeorder(order_id):
    order = Order.query.filter(Order.id==order_id, Order.status=='Ready ', Order.pharmacy_id==session.get('pharmacy_id')).first()

    existing_deliveries_count = db.session.query(Delivery).join(Order).filter(Delivery.delivery_guy_id == current_user.id, Order.status == "Out for Delivery").count()
    
    if existing_deliveries_count >= 5:
        flash('You cannot take more than 5 orders at a time.')
        return redirect(url_for('delivery.dashboard'))
    user = User.query.get_or_404(order.user_id)
    cust_names=user.firstname + " " + user.lastname
    new_delivery = Delivery(customer_name = cust_names,
        address=order.location,
        latitude=order.latitude,
        longitude=order.longitude,
        delivery_guy_id=current_user.id,
        order_idd=order.order_id,
        status="Out for Delivery")
    order.status = "Out for Delivery"

    try:
        db.session.add(new_delivery)
        db.session.commit()
        flash('Order taken successfully.')
    except IntegrityError:
        db.session.rollback()
        flash('An integrity error occurred.')
        return redirect(url_for('delivery.dashboard'))

    return redirect(url_for('delivery.dashboard'))

@delivery.route('/mydeliveries', methods=["POST", "GET"])
@login_required
def mydeliveries():
    pharmacy = Pharmacy.query.get_or_404(session.get('pharmacy_id'))
    myform = updatedeliveryform()
    delivery_update = updatedeliveryform()
    deliveries = Delivery.query.filter(
        Delivery.delivery_guy_id == current_user.id,
        Delivery.status == "Out for Delivery"
    ).all()
    formpharm=Set_PharmacyForm()
    formpharm.pharmacy.choices=[(-1, "Select a Pharmacy")] + [(p.id, p.name) for p in Pharmacy.query.all()]
  
    return render_template('delivery/ActiveOrder.html', myform=myform, pharmacy=pharmacy, deliveries=deliveries, delivery_update=delivery_update,formpharm=formpharm)


@delivery.route('/update_delivery/<int:delivery_id>',methods=["POST", "GET"])
@login_required
def update_delivery(delivery_id):
    myform = updatedeliveryform()
    delivery = Delivery.query.get_or_404(delivery_id)
    if not delivery:
        flash('the delivery does not exist')
        return redirect(url_for('delivery.mydeliveries'))
    else:
        if myform.validate_on_submit():
            delivery.status = myform.status.data
            _image = save_delivery_picture(myform.delivery_prove.data)
           
            delivery.customer_pic =_image
            db.session.add(delivery)
            try:
                db.session.commit()
                flash('Delivery Status successfully updated.')
                return redirect(url_for('delivery.mydeliveries'))
            except IntegrityError:
                flash('Error occured. We working on solving it')
                return redirect(url_for('delivery.mydeliveries'))
        else:
            flash("form failed to validate after submission.")
            return redirect(url_for('delivery.mydeliveries'))

@delivery.route('/deliverylayout', methods=["POST", "GET"])
def deliverylayout():
    formpharm = Set_PharmacyForm()
    pharmacies = Pharmacy.query.all()
    total_count = 0
    pharmacy = Pharmacy.query.get_or_404(session.get('pharmacy_id'))
    total_count = Order.query.filter(Order.pharmacy_id == session.get('pharmacy_id'), Order.status == "Ready", )
    formpharm.pharmacy.choices = [(p.id, p.name) for p in pharmacies]
    return render_template('deliverylayout.html', formpharm=formpharm, total_count=total_count, pharmacy=pharmacy)

@delivery.route('/set_pharmacy', methods=['POST', 'GET'])
def set_pharmacy():
    formpharm = Set_PharmacyForm()
    formpharm.pharmacy.choices=[(-1, "Select a Pharmacy")] + [(p.id, p.name) for p in Pharmacy.query.all()]
    if formpharm.validate_on_submit():
        session['pharmacy_id'] = formpharm.pharmacy.data
        return redirect(url_for('delivery.dashboard', pharmacy_id=formpharm.pharmacy.data))
    elif formpharm.errors:
        print(formpharm.errors)
        return formpharm.errors
    else:
        flash(f'{current_user.id} had a problem selecting your pharmacy, please try again later')
        return redirect(url_for('delivery.dashboard'))


@delivery.route('/deliverystats')
@login_required
def deliverystats():
    pass

"""
@delivery.route('/api/orders')
def get_orders():
    delivery_position = globals().get("delivery_position", {})
    active_order_id = globals().get("active_order_id", None)

    orders = Delivery.query.filter_by(delivery_guy_id=current_user.id).all()

    return jsonify({
        "orders": [o.to_dict() for o in orders],
        "delivery": delivery_position,
        "target": active_order_id
    })

@delivery.route('/api/update_delivery', methods=['POST'])
def update_delivery():
    global delivery_position
    data = request.get_json()
    delivery_position = data
    return jsonify({"status": "updated"})

@delivery.route('/api/set_target/<int:order_id>', methods=['POST'])
def set_target(order_id):
    global active_order_id
    active_order_id = order_id
    return jsonify({"status": "target set", "target": order_id})
"""