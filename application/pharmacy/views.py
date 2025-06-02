import calendar
import os
import secrets
from flask import render_template, session
from datetime import datetime, timedelta
from sqlalchemy import func, extract, asc
import plotly.graph_objs as go
import plotly.offline as plot
from PIL import Image
from flask import current_app
from flask import render_template, redirect, url_for, session, request, flash
from flask_login import login_required, current_user, logout_user, LoginManager  # type: ignore
from sqlalchemy import func, extract
from sqlalchemy.exc import IntegrityError

from . import pharmacy
from ..forms import addmore, removefromcart, ProductForm, \
    updatestatusform, update, CartlistForm, Search
from ..models import User, Product, Sales, DeliveryGuy, Order, Cart, OrderItem, db, Pharmacy

mypharmacy_product = Pharmacy.products
mypharmacy_orders = Pharmacy.orders


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
    elif user_type == 'delivery_guy':
        return DeliveryGuy.query.get(int(user_id))
    return None 

from flask import jsonify



@pharmacy.route('/adminpage', methods=["POST", "GET"])
@login_required
def adminpage():
    mypharmacy = Pharmacy.query.get_or_404(current_user.id)
    today = datetime.today()
    current_month, current_year = today.month, today.year

    start_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    next_month = (today.replace(day=28) + timedelta(days=4)).replace(day=1)
    end_of_month = next_month - timedelta(seconds=1)
    start_of_year = today.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    end_of_year = today.replace(month=12, day=31, hour=23, minute=59, second=59, microsecond=999999)

    pharmacy_id = session.get('pharmacy_id')

    # Daily sales
    daily_sales = db.session.query(
            func.date(Sales.date_).label('date'),
            func.sum(Sales.price * Sales.quantity).label('total')
        ).filter(Sales.pharmacy_id == pharmacy_id).group_by(func.date(Sales.date_)).order_by(
            func.date(Sales.date_)).all()

    daily_data = {
            "dates": [row.date.strftime("%b %d") for row in daily_sales],
            "totals": [float(row.total) for row in daily_sales]
        }

    line = go.Scatter(x=daily_data["dates"], y=daily_data["totals"], mode='lines+markers', name='Daily Sales')
    line_layout = go.Layout(title="Daily Sales Trend")
    line_chart = plot.plot(go.Figure(data=[line], layout=line_layout), include_plotlyjs=True, output_type='div')

    candle_chart = 0
    # Candlestick chart
    if daily_sales:
        candle_data = []
        for row in daily_sales:
            open_ = row.total * 0.95
            high = row.total * 1.1
            low = row.total * 0.9
            close = row.total
            candle_data.append(
                dict(date=row.date.strftime("%Y-%m-%d"), open=open_, high=high, low=low, close=close))

            candlestick = go.Candlestick(
                x=[d["date"] for d in candle_data],
                open=[d["open"] for d in candle_data],
                high=[d["high"] for d in candle_data],
                low=[d["low"] for d in candle_data],
                close=[d["close"] for d in candle_data]
            )
            candle_layout = go.Layout(title="Sales Candlestick Chart")
            candle_chart = plot.plot(go.Figure(data=[candlestick], layout=candle_layout), include_plotlyjs=True,
                                     output_type='div')
    else:
        candle_chart = "<p>No sales data available for candlestick chart.</p>"

        # Total sales
    total_monthly_sales = db.session.query(func.sum(Sales.price * Sales.quantity)).filter(
            Sales.date_ >= start_of_month, Sales.date_ <= end_of_month,
            Sales.pharmacy_id == pharmacy_id
        ).scalar() or 0.0

    total_annual_sales = db.session.query(func.sum(Sales.price * Sales.quantity)).filter(
            Sales.date_ >= start_of_year, Sales.date_ <= end_of_year,
            Sales.pharmacy_id == pharmacy_id
        ).scalar() or 0.0

    today_sales = db.session.query(func.sum(Sales.price * Sales.quantity)).filter(
            func.date(Sales.date_) == today.date(),
            Sales.pharmacy_id == pharmacy_id
        ).scalar() or 0.0

        # Top 10 products
    top_products = db.session.query(
            Product.productname,
            func.sum(OrderItem.quantity * OrderItem.product_price).label('revenue')
        ).join(OrderItem, Product.id == OrderItem.product_id
               ).filter(Product.pharmacy_id == pharmacy_id
                        ).group_by(Product.productname
                                   ).order_by(func.sum(OrderItem.quantity * OrderItem.product_price).desc()
                                              ).limit(10).all()

    top_bar = go.Bar(
            x=[p[0] for p in top_products],
            y=[float(p[1]) for p in top_products],
            text=[f"{float(p[1]):.2f}" for p in top_products],
            textposition='auto'
        )
    top_layout = go.Layout(title="Top 10 Selling Products")
    top_chart = plot.plot(go.Figure(data=[top_bar], layout=top_layout), include_plotlyjs=True, output_type='div')

    pending_orders = len(Order.query.filter(
        extract('month', Order.create_at) == current_month,
        extract('year', Order.create_at) == current_year,
        (Order.status == "Pending"), (Order.pharmacy_id==mypharmacy.id)).all())
    if not pending_orders:
        pending_orders = 0

    return render_template(
            'pharmacy/updated_dashboard.html',
            chart1=line_chart,
            chart=candle_chart,
            chart2=top_chart,
            total_sales=total_monthly_sales,
            total_annual_sales=total_annual_sales,
            total_daily_sales=today_sales,
            total_monthly_sales=total_monthly_sales,
            pharmacy=mypharmacy,
        pending_orders=pending_orders
        )


@pharmacy.route('/search', methods=['POST', 'GET'])
@login_required
#@role_required('Pharmacy')
def search():
    mypharmacy = Pharmacy.query.get(current_user.id)
    form = CartlistForm()
    form2 = Search()
    keyword = form2.keyword.data
    item_picture = 'dfdfdf.jpg'
    total_count = 0
    count = Cart.query.filter_by(user_id=current_user.id).first()
    if count:
        total_count = sum(item.quantity for item in count.cart_items)
    products = Order.query.filter(Order.pharmacy_id == mypharmacy.id,
        Order.order_id.like(f'%{keyword}%')|
        Order.location.like(f'%{keyword}%') |
        Order.user_id.like(f'%{keyword}%') |
        Order.payment.like(f'%{keyword}%') |
        Order.user_email.like(f'%{keyword}%')
                            ).all()

    return render_template('pharmacy/updated_orders.html', form=form, item_picture=item_picture,
                           total_count=total_count, products=products, form2=form2)





@pharmacy.route('/updateproduct/<int:item_id>', methods=['GET', 'POST'])
@login_required
#@role_required('Pharmacy')
def updateproduct(item_id):
    mypharmacy = Pharmacy.query.get(current_user.id)
    form = update()
    if form.validate_on_submit():

        product = Product.query.filter(id=item_id, pharmacy_id=mypharmacy.id).first()
        if product:
            product.productname = form.newname.data
            product.description = form.newdescription.data
            product.category = form.category.data
            product.price = form.newprice.data

        try:
            db.session.commit()
            return redirect(url_for('pharmacy.products'))
        except IntegrityError:
            db.session.rollback()

            return redirect(url_for('pharmacy.products'))
    pharmacy_id = session.get('pharmacy_id')

    return render_template('pharmacy/updated_updateproduct.html', form=form, item_id=item_id, pharmacy=pharmacy)


@pharmacy.route('/ActiveOrders')
@login_required
#@role_required('Pharmacy')
def ActiveOrders():
    form = updatestatusform()
    orders = Order.query.filter(Order.status=="Pending", Order.pharmacy_id == current_user.id).all()
    print(orders)
    approved_order = Order.query.filter(Order.status=="Approved", Order.pharmacy_id == current_user.id).all()
    pharmacy_id = session.get('pharmacy_id')

    return render_template("pharmacy/updated_orders.html", form=form, orders=orders, approved_order=approved_order, pharmacy=pharmacy)


@pharmacy.route('/delivered')
@login_required
#@role_required('Pharmacy')
def delivered_orders():
    pharmacy_id = session.get('pharmacy_id')
    pharmacy = Pharmacy.query.get_or_404(pharmacy_id)    
    form = updatestatusform()
    orders = Order.query.filter(Order.status=="Ready", Order.pharmacy_id == current_user.id).all()
    #total = sum(item.product.price * item.quantity for item in orders.order_items)
    return render_template("pharmacy/updated_Delivered.html", form=form, orders=orders, pharmacy=pharmacy)

@pharmacy.route('/cancelled')
@login_required
#@role_required('Pharmacy')
def cancelled_orders():
    pharmacy_id = session.get('pharmacy_id')
    pharmacy = Pharmacy.query.get_or_404(pharmacy_id)
    form = updatestatusform()
    orders = Order.query.filter(Order.status=="Cancelled", Order.pharmacy_id == current_user.id).all()
    #total = sum(item.product.price * item.quantity for item in orders.order_items)
    return render_template("pharmacy/updated_cancelled.html", form=form, orders=orders, pharmacy=pharmacy)


@pharmacy.route('/orders/updatestatus/<int:order_id>', methods=['POST'])
@login_required
#@role_required('Pharmacy')
def updatestatus(order_id):
    form = updatestatusform()
    if form.validate_on_submit():
        order = Order.query.get_or_404(order_id)
        order.status = form.status.data
        print('done updating')
        db.session.add(order)
        try:
            db.session.commit()
            flash('Order status updated successfully')
            return redirect(url_for('pharmacy.orders'))
        except IntegrityError:
            flash("Failed to update Order Status.")
            return redirect(url_for('pharmacy.orders'))


    return redirect(url_for('pharmacy.ActiveOrders'))


@pharmacy.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('auth.newlogin'))



@pharmacy.route('/addproducts', methods=["POST", "GET"])
@login_required
#@role_required('Pharmacy')
def addproducts():
    form = ProductForm()
    mypharmacy = Pharmacy.query.get(current_user.id)
    if request.method == 'POST':
        if form.is_submitted():
            if form.validate_on_submit:
                product = Product(productname=form.product_name.data, price=form.product_price.data, quantity=form.product_quantity.data,
                                  description=form.product_description.data
                                  )
                file = form.product_pictures.data
                product.category = form.category.data
                product.pharmacy_id = mypharmacy.id
                _image = save_product_picture(file)
                product.pictures = _image
                db.session.add(product)
                try:

                    db.session.commit()
                    print('picture saved')

                    return redirect(url_for("pharmacy.products"))
                except IntegrityError:
                    flash('intergrity error', 'danger')
                    return redirect(url_for('pharmacy.addproducts'))
            else:
                flash("An error occurred")
        else:
            flash('form was not submitted successfully.try again later.')
    pharmacy_id = session.get('pharmacy_id')
    pharmacy = Pharmacy.query.get_or_404(pharmacy_id)    
    return render_template("pharmacy/updated_addProduct.html", form=form, pharmacy=pharmacy)


@pharmacy.route('/userorders/<int:order_id>', methods=['post', 'get'])
@login_required
#@role_required('Pharmacy')
def userorders(order_id):
   
    pharmacy_id = session.get('pharmacy_id')
    pharmacy = Pharmacy.query.get_or_404(pharmacy_id) 
    cart = Cart.query.filter_by(user_id=current_user.id, pharmacy_id=current_user.id).first()
    user_order = Order.query.filter(Order.id==order_id, Order.pharmacy_id==pharmacy_id).first()
    total = 0.00
    if user_order:

        gross_total = sum(item.product.price * item.quantity for item in user_order.order_items)

        total=gross_total
    else:
        flash('Cant view details')

        return redirect(url_for('pharmacy.ActiveOrders'))
  
    return render_template('pharmacy/updated_vieworders.html', pharmacy=pharmacy, user_order=user_order, total=total)


@pharmacy.route('/products')
@login_required
#@role_required('Pharmacy')
def products():
    mypharmacy = Pharmacy.query.get(current_user.id)
    form2 = removefromcart()
    form4 = Search()
    form3 = addmore()
    form = update()
    product = Product.query.filter(Product.pharmacy_id==mypharmacy.id).all()

    pharmacy_id = session.get('pharmacy_id')
    pharmacy = Pharmacy.query.get_or_404(pharmacy_id)
    return render_template('pharmacy/updated_products.html', product=product, form4=form4, form=form, 
                           pharmacy=pharmacy, form2=form2, form3=form3)



@pharmacy.route('/remove_from_products/<int:item_id>', methods=['POST', 'GET'])
@login_required
#@role_required('Pharmacy')
def remove_from_products(item_id):
    product = Product.query.filter_by(id=item_id).first()
    if product:
        db.session.delete(product)
        db.session.commit()
    return redirect(url_for('pharmacy.products'))

    
@pharmacy.route('/decrement/<int:item_id>', methods=['POST', 'GET'])
@login_required
#@role_required('Pharmacy')
def decrement_product(item_id):
    product = Product.query.filter_by(id=item_id).first()
    if product:
        product.quantity -= 1
        db.session.add(product)
        if product.quantity <= 0:
            db.session.delete(product)
    db.session.commit()
    return redirect(url_for('pharmacy.products'))


@pharmacy.route('/add_products/<int:item_id>', methods=['POST', 'GET'])
@login_required
#@role_required('Pharmacy')
def add_products(item_id):
    product = Product.query.filter_by(id=item_id).first()
    if product:
        product.quantity += 1
        if product.quantity <= 0:
            db.session.delete(product)

    db.session.commit()
    return redirect(url_for('pharmacy.products'))

