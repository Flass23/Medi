import os
import secrets
from flask import render_template, redirect, request, url_for, flash, session, jsonify
from flask_login import login_required, current_user, logout_user # type: ignore
from sqlalchemy.exc import IntegrityError
from application.models import Delivery, DeliveryGuy
from sqlalchemy import desc
from . import delivery
from ..forms import *
from ..models import *
"""

@delivery.route('/dashboard', methods=["GET", "POST"])
@login_required
def dashboard():
    if session.get('user_type') != 'delivery_guy':
        flash("Unauthorized access", "danger")
        return redirect(url_for('auth.newlogin'))
    pharmacy = Pharmacy.query.get_or_404(session.get('pharmacy_id'))
    ready_orders = Order.query.filter(Order.status=='Ready', Order.pharmacy_id == pharmacy.id).order_by(desc(Order.create_at)).all()
    user_id = current_user.id
    form2 = Search()
    formpharm=Set_PharmacyForm()
    formpharm.pharmacy.choices=[(-1, "Select a Pharmacy")] + [(p.id, p.name) for p in Pharmacy.query.all()]
    user = User.query.get_or_404(user_id)

    #the dashboard will show orders
    return render_template('delivery/dashboard.html',formpharma=formpharm, form2=form2, ready_orders=ready_orders)

@delivery.route('/takeorder/<int:order_id>', methods=["GET"])
@login_required
def takeorder(order_id):
    order = Order.query.filter_by(id=order_id, status='Ready', pharmacy_id=session.get('pharmacy_id')).first()
    if not order:
        flash('Order not found or not ready.')
        return redirect(url_for('delivery.dashboard'))

    existing_deliveries_count = db.session.query(Delivery).join(Order).filter(Delivery.delivery_guy_id == current_user.id, Order.status == "Out for Delivery").count()
    
    if existing_deliveries_count >= 5:
        flash('You cannot take more than 5 orders at a time.')
        return redirect(url_for('delivery.dashboard'))

    new_delivery = Delivery(
        customer_name = order.user.firstname + " " + order.user.lastname
,  # Make sure this field exists in Order
        address=order.location,
        latitude=order.latitude,
        longitude=order.longitude,
        delivery_guy_id=current_user.id,
        order_id=order.id,
        status="Out for Delivery"
    )
    
    order.status = "Out for Delivery"

    try:
        db.session.add(new_delivery)
        db.session.commit()
        flash('Order taken successfully.')
    except IntegrityError:
        db.session.rollback()
        flash('An integrity error occurred.')

    return redirect(url_for('delivery.dashboard'))

@delivery.route('/mydeliveries')
@login_required
def mydeliveries():
    deliveries = Delivery.query.filter(
        Delivery.delivery_guy_id == current_user.id,
        Delivery.status == "Out for Delivery"
    ).all()

    return render_template('delivery/AvtiveOrder.html', deliveries=deliveries)


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