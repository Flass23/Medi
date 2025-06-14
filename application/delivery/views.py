import os

from PIL import Image
from flask import render_template, redirect, url_for, flash, session
from flask_login import login_required, current_user, logout_user  # type: ignore
from sqlalchemy import desc
from sqlalchemy.exc import IntegrityError

from application.utils.notification import create_notification
from . import delivery
from .. import socketio
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
    deliveries = Delivery.query.filter_by(delivery_guy_id=current_user.id).all()

    total = len(deliveries)
    delivered = [d for d in deliveries if d.status == 'Delivered']
    revenue=len(delivered) * 10
    cancelled = [d for d in deliveries if d.status == 'Cancelled']
    in_progress = [d for d in deliveries if d.status not in ['Delivered', 'Cancelled']]

    success_rate = (len(delivered) / total * 100) if total !=0 else 0

    # Average delivery time (assumes Delivery model has `start_time` and `end_time` as datetime fields)
    #total_time = sum([(d.end_time - d.start_time).total_seconds() for d in delivered if d.start_time and d.end_time], 0)
    #avg_delivery_time = total_time / len(delivered) / 60 if delivered else 0  # in minutes

    #recent_deliveries = sorted(deliveries, key=lambda d: d.end_time or d.id, reverse=True)[:5]

    return render_template('delivery/deliverystats.html',
                           total=total,
                           delivered=len(delivered),
                           in_progress=len(in_progress),
                           cancelled=len(cancelled),
                           pharmacy=pharmacy,
                           revenue=revenue,
                           formpharm=formpharm,
                           success_rate=round(success_rate, 2),
                          )
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
        order_id=order.order_id,
        status="Out for Delivery")
    order.status = "Out for Delivery"

    try:
        db.session.add(order)
        db.session.add(new_delivery)
        db.session.commit()

        flash('Order taken successfully.')
    except IntegrityError:
        db.session.rollback()
        flash('An integrity error occurred.')
        return redirect(url_for('delivery.dashboard'))

    return redirect(url_for('delivery.dashboard'))

# In your delivery_routes.py or similar
from flask import jsonify

@delivery.route('/api/delivery/<order_id>', methods=['GET'])
@login_required
def get_delivery_status(order_id):
    delivery = Delivery.query.filter_by(order_id=order_id).first()
    if delivery:
        return jsonify(delivery.to_dict())
    return jsonify({"error": "Delivery not found"}), 404



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
  
    return render_template('delivery/ActiveOrder.html', myform=myform, pharmacy=pharmacy,
                           deliveries=deliveries, delivery_update=delivery_update,formpharm=formpharm)

@delivery.route('/ready orders')
@login_required
def ready_orders():
    pharmacy = Pharmacy.query.get_or_404(session.get('pharmacy_id'))
    myform = updatedeliveryform()
    delivery_update = updatedeliveryform()
    formpharm=Set_PharmacyForm()
    formpharm.pharmacy.choices=[(-1, "Select a Pharmacy")] + [(p.id, p.name) for p in Pharmacy.query.all()]
    ready = Order.query.filter(Order.status == "Ready ", Order.pharmacy_id == session.get('pharmacy_id')).all()
    return render_template('delivery/deliverydashboard.html', ready_orders=ready, myform=myform, pharmacy=pharmacy,
                           delivery_update=delivery_update,formpharm=formpharm)


@delivery.route('/update_delivery/<int:delivery_id>', methods=["GET", "POST"])
@login_required
def update_delivery(delivery_id):
    form = updatedeliveryform()
    delivery = Delivery.query.get_or_404(delivery_id)

    if form.validate_on_submit():
        new_status = form.status.data
        old_status = delivery.status

        if old_status == new_status:
            flash('Status is already up to date.')
            return redirect(url_for('delivery.mydeliveries'))

        delivery.status = new_status
        order = Order.query.filter(Order.order_id == delivery.order_id).first()
        order.status = form.status.data
        if form.delivery_prove.data:
            image_filename = save_delivery_picture(form.delivery_prove.data)
            delivery.customer_pic = image_filename
        try:
            db.session.add(delivery)
            db.session.add(order)
            db.session.commit()
            # 🔔 Message
            message = f"Delivery #{delivery.id} status changed from {old_status} to {new_status}"

            create_notification(user_type='customer', user_id=order.user_id, message=message)

            # 🔔 Notify pharmacy & emit event

            create_notification(user_type='pharmacy', user_id=order.pharmacy_id, message=message)

            flash('Delivery status successfully updated.')

        except IntegrityError:
            db.session.rollback()
            flash('An error occurred while updating the delivery. Please try again.')

        return redirect(url_for('delivery.mydeliveries'))

    flash("Form failed to validate.")
    return redirect(url_for('delivery.mydeliveries'))


@delivery.route('/deliverylayout', methods=["POST", "GET"])
def deliverylayout():
    formpharm = Set_PharmacyForm()
    pharmacies = Pharmacy.query.all()
    total_count = 0
    pharmacy = Pharmacy.query.get_or_404(session.get('pharmacy_id'))
    total_count = Order.query.filter(Order.pharmacy_id == session.get('pharmacy_id'), Order.status == "Ready").all().count()
    formpharm.pharmacy.choices = [(p.id, p.name) for p in pharmacies]
    return render_template('deliverylayout.html', formpharm=formpharm, total_count=total_count,
                           pharmacy=pharmacy)

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



