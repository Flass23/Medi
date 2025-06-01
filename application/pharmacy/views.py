import calendar
import os
import secrets
from datetime import datetime, timedelta

import plotly.graph_objs as go  # type: ignore
import plotly.offline as plot  # type: ignore
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


def get_annual_sales(pharmacy_id):
    today = datetime.today()
    start_of_year = datetime(datetime.today().year, 1, 1, 1)
    end_of_year = today.replace(month=12, day=31, hour=23, minute=59, second=59, microsecond=999999)
    total_annual_sales = db.session.query(func.sum(Sales.price * Sales.quantity)) \
    .filter(Sales.pharmacy_id == pharmacy_id, Sales.date_ >= start_of_year, Sales.date_ <= end_of_year).scalar() 
    total_annual_sales = total_annual_sales if total_annual_sales else 0.00
    return total_annual_sales

def get_mom_growth(pharmacy_id):
    today = datetime.today()
    current_month = today.month
    current_year = today.year

    this_month_start = datetime(today.year, today.month, 1)
    
    last_month = (this_month_start - timedelta(days=1)).replace(day=1)
    this_month_sales = db.session.query(func.sum(Sales.price * Sales.quantity)) \
        .filter(Sales.date_ >= this_month_start, Sales.date_ <= last_month) \
        .scalar()
    this_month_sales = this_month_sales if this_month_sales else 0.0
    if current_month == 1:
        previous_month = 12
        previous_year = current_year -1
    else:
        previous_month = current_month -1
        previous_year = current_year
    start_of_prev_month = today.replace(year=previous_year, month=previous_month, day=1, hour=0, minute=0, microsecond=0)

    prev_monthly_sales = db.session.query(func.sum(Sales.price*Sales.quantity)).filter(Sales.date_ >= start_of_prev_month, Sales.pharmacy_id==pharmacy_id).scalar() or 0.0

    if prev_monthly_sales > 0:
        mom_growth = ((this_month_sales - prev_monthly_sales) / prev_monthly_sales) *100
    else:
        mom_growth = 100

    return mom_growth


from flask import jsonify

@pharmacy.route('/pharmacy_order_alerts', methods=['GET'])
@login_required
def pharmacy_order_alerts():
    if session.get('user_type') != 'pharmacy':
        return jsonify({'status': 'unauthorized'}), 403

    pharmacy_id = current_user.id

    latest_pending = Order.query.filter_by(pharmacy_id=pharmacy_id, status='Pending') \
        .order_by(Order.create_at.desc()).first()

    latest_ready = Order.query.filter_by(pharmacy_id=pharmacy_id, status='Ready') \
        .order_by(Order.update_at.desc()).first()

    response = {}

    if latest_pending:
        response['pending_id'] = latest_pending.id
    if latest_ready:
        response['ready_id'] = latest_ready.id

    return jsonify(response)


@pharmacy.route('/adminpage', methods=["POST", "GET"])
@login_required
#@role_required('Pharmacy')
def adminpage():
    #analysis
    mypharmacy = Pharmacy.query.get_or_404(current_user.id)
    # query the data
    today = datetime.today()

    current_month = today.month
    current_year = today.year
    sales = Sales.query.filter(Sales.pharmacy_id==current_user.id).all()
    hsales = [sale.price * sale.quantity for sale in sales]
    # Calculate the start of the current month (first day of the month)
    start_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Calculate the end of the current month (last day of the month)
    next_month = today.replace(day=28) + timedelta(days=4)  # this gets us to the next month
    end_of_month = next_month.replace(day=1) - timedelta(days=1)  # last day of the current month
    end_of_month = end_of_month.replace(hour=23, minute=59, second=59, microsecond=999999)

    start_of_year = today.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    end_of_year = today.replace(month=12, day=31, hour=23, minute=59, second=59, microsecond=999999)

    if current_month == 1:
        previous_month = 12
        previous_year = current_year - 1
    else:
        previous_month = current_month - 1
        previous_year = current_year
    start_of_prev_month = today.replace(year=previous_year, month=previous_month, day=1, hour=0, minute=0,
                                        microsecond=0)
    temp_next = start_of_prev_month.replace(day=28) + timedelta(days=4)
    end_of_prev_month = temp_next.replace(hour=23, minute=59, second=59, microsecond=999999)

    prev_monthly_sales = db.session.query(func.sum(Sales.price * Sales.quantity)).filter(
        Sales.date_ >= start_of_prev_month, Sales.pharmacy_id == session.get('pharmacy_id')).scalar() or 0.0
    ## MoM Growth rate

    total_annual_sales = db.session.query(func.sum(Sales.price * Sales.quantity)) \
        .filter(Sales.date_ >= start_of_year, Sales.date_ <= end_of_year,
                Sales.pharmacy_id == session.get('pharmacy_id')).scalar()
    total_annual_sales = total_annual_sales if total_annual_sales else 0.00

    # Query to calculate total sales in the current month
    total_sales = db.session.query(func.sum(Sales.price * Sales.quantity)) \
        .filter(Sales.date_ >= start_of_month, Sales.date_ <= end_of_month,
                Sales.pharmacy_id == session.get('pharmacy_id')) \
        .scalar()
    min_value = min(hsales)
    max_value = max(hsales)
    # If no sales are found, return 0
    total_sales = total_sales if total_sales else 0.0

    if prev_monthly_sales > 0:
        mom_growth = ((total_sales - prev_monthly_sales) / prev_monthly_sales) * 100
    else:
        mom_growth = 100

    results = (db.session.query(Product.productname,
                                func.sum(OrderItem.quantity * OrderItem.product_price).label('total Revenue')
                                )
               .join(Product, Product.id == OrderItem.product_id)
               .group_by(Product.productname)
               .order_by(func.sum(OrderItem.quantity * OrderItem.product_price).desc())
               .filter(Product.pharmacy_id == session.get('pharmacy_id'))).all()

    # separate the results into two lists for plotting

    product_names = [row[0] for row in results]

    revenues = [float(row[1]) for row in results]

    # create a bar chart using plotly

    bar = go.Bar(x=product_names, y=revenues, text=revenues, textposition='outside')
    layout = go.Layout(title="Top-Selling Products by revenue")
    fig = go.Figure(data=[bar], layout=layout)

    chart_div = plot.plot(fig, include_plotlyjs=True, output_type='div')

    results1 = (
        db.session.query(func.date(Sales.date_).label('date'),
                         func.sum(Sales.price).label('daily total'), (Sales.pharmacy_id == mypharmacy.id)
                         ).group_by(func.date(Sales.date_))
        .order_by(func.date(Sales.date_)).all()
    )

    # Format dates like "January 1", "January 2", etc.
    dates = [datetime.strptime(row[0], '%Y-%M-%d').strftime("%B %d") for row in results1]
    totals = [row[1] for row in results1]

    line = go.Scatter(x=dates, y=totals, mode='lines+markers')
    layout1 = go.Layout(title="monthly sales over time", xaxis=dict(title='Month'), yaxis=dict(title='Total Sales'))
    fig1 = go.Figure(data=[line], layout=layout1)
    fig1.update_layout(yaxis=dict(range=[min_value -10, max_value + 10]))
    chart_div1 = plot.plot(fig1, include_plotlyjs=True, output_type='div')

    results2 = (
        db.session.query(
            Order.payment, func.count(Order.id)
        ).group_by(Order.payment).filter(Order.pharmacy_id == mypharmacy.id).all()
    )
    methods = [row[0] for row in results2]
    counts = [row[1] for row in results2]

    pie = go.Pie(labels=methods, values=counts)
    layout2 = go.Layout(title="Payment Method Distribution")
    fig2 = go.Figure(data=[pie], layout=layout2)

    chart_div2 = plot.plot(fig2, include_plotlyjs=True, output_type='div')

    ##candle sticks
    daily_sales = (
        db.session.query(
            func.date(Sales.date_).label('sale_date'),
            func.sum(Sales.price).label('daily_total')
        ).group_by(func.date(Sales.date_))
        .order_by(func.date(Sales.date_)).filter(Sales.pharmacy_id == mypharmacy.id).all()
    )

    if not daily_sales:
        flash('There is no data yet')
        return redirect(url_for('pharmacy.adminpage'))

    pending_orders = len(Order.query.filter(
        extract('month', Order.create_at) == current_month,
        extract('year', Order.create_at) == current_year,
        (Order.status == "Pending"), (Order.pharmacy_id == mypharmacy.id)).all())
    if not pending_orders:
        pending_orders = 0

   #analysis
    mypharmacy = Pharmacy.query.get_or_404(session.get('pharmacy_id'))

    today = datetime.today()
    current_month = today.month
    current_year = today.year
    start_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Calculate the end of the current month (last day of the month)
    next_month = today.replace(day=28) + timedelta(days=4)  # this gets us to the next month
    end_of_month = next_month.replace(day=1) - timedelta(days=1)  # last day of the current month
    end_of_month = end_of_month.replace(hour=23, minute=59, second=59, microsecond=999999)
    # Get today's date

    # Calculate the start of the current month (first day of the month)
    total_sales = 0
    # If no sales are found, return 0
    total_sales = db.session.query(func.sum(Sales.price * Sales.quantity)) \
        .filter(Sales.date_ >= start_of_month, Sales.date_ <= end_of_month, Sales.pharmacy_id == session.get('pharmacy_id') ) \
        .scalar()


    total_sales = total_sales if total_sales else 0.0
    pending_orders = len(Order.query.filter(
        extract('month', Order.create_at) == current_month,
        extract('year', Order.create_at) == current_year,
        (Order.status == "Pending"), (Order.pharmacy_id==mypharmacy.id)).all())
    if not pending_orders:
        pending_orders = 0
    username = current_user.name
    pharmacy_id = session.get('pharmacy_id')
    pharmacy = Pharmacy.query.get_or_404(pharmacy_id)
    if not pharmacy:
        pharmacy = "Pharmacy not found"
    return render_template('pharmacy/updated_dashboard.html',chart1=chart_div1 , chart=chart_div,
                           chart2=chart_div2,
                           username = username, total_sales=total_sales,
                           current_year=today.year, current_month=today.strftime('%B'),
                            pending_orders=pending_orders, pharmacy=pharmacy, 
                            total_annual_sales=get_annual_sales(session.get('pharmacy_id')), mom_growth = round(get_mom_growth(session.get('pharmacy_id')), 2))



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


@pharmacy.route('/top_selling')
@login_required
#@role_required('Pharmacy')
def top_selling():
    mypharmacy = Pharmacy.query.get_or_404(current_user.id)
    #query the data
    today = datetime.today()
    current_month = today.month
    current_year = today.year
    # Calculate the start of the current month (first day of the month)
    start_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Calculate the end of the current month (last day of the month)
    next_month = today.replace(day=28) + timedelta(days=4)  # this gets us to the next month
    end_of_month = next_month.replace(day=1) - timedelta(days=1)  # last day of the current month
    end_of_month = end_of_month.replace(hour=23, minute=59, second=59, microsecond=999999)

    start_of_year = today.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    end_of_year = today.replace(month=12, day=31, hour=23, minute=59, second=59, microsecond=999999)

    if current_month == 1:
        previous_month = 12
        previous_year = current_year - 1
    else:
        previous_month = current_month - 1
        previous_year = current_year
    start_of_prev_month = today.replace(year=previous_year, month=previous_month, day=1, hour=0, minute=0,
                                        microsecond=0)
    temp_next = start_of_prev_month.replace(day=28) + timedelta(days=4)
    end_of_prev_month = temp_next.replace(hour=23, minute=59, second=59, microsecond=999999)

    prev_monthly_sales = db.session.query(func.sum(Sales.price * Sales.quantity)).filter(
        Sales.date_ >= start_of_prev_month, Sales.pharmacy_id == session.get('pharmacy_id')).scalar() or 0.0
    ## MoM Growth rate

    total_annual_sales = db.session.query(func.sum(Sales.price * Sales.quantity)) \
        .filter(Sales.date_ >= start_of_year, Sales.date_ <= end_of_year, Sales.pharmacy_id == session.get('pharmacy_id') ).scalar()
    total_annual_sales = total_annual_sales if total_annual_sales else 0.00

    # Query to calculate total sales in the current month
    total_sales = db.session.query(func.sum(Sales.price * Sales.quantity)) \
        .filter(Sales.date_ >= start_of_month, Sales.date_ <= end_of_month, Sales.pharmacy_id == session.get('pharmacy_id') ) \
        .scalar()

    # If no sales are found, return 0
    total_sales = total_sales if total_sales else 0.0



    if prev_monthly_sales > 0:
        mom_growth = ((total_sales - prev_monthly_sales) / prev_monthly_sales) * 100
    else:
        mom_growth = 100

    results = (db.session.query(Product.productname, func.sum(OrderItem.quantity*OrderItem.product_price).label('total Revenue')
                                )
               .join(Product, Product.id == OrderItem.product_id)
               .group_by(Product.productname)
               .order_by(func.sum(OrderItem.quantity*OrderItem.product_price).desc())
               .filter(Product.pharmacy_id==session.get('pharmacy_id'))).all()

    #separate the results into two lists for plotting

    product_names = [row[0] for row in results]

    revenues = [float(row[1]) for row in results]

    #create a bar chart using plotly

    bar = go.Bar(x=product_names, y=revenues, text=revenues, textposition='outside')
    layout = go.Layout(title="Top-Selling Products by revenue")
    fig = go.Figure(data=[bar], layout=layout)

    chart_div = plot.plot(fig, include_plotlyjs=True, output_type='div')

    results1 = (
        db.session.query(func.date(Sales.date_).label('date'),
                         func.sum(Sales.price).label('daily total'), (Sales.pharmacy_id == mypharmacy.id)
                         ).group_by(func.date(Sales.date_))
        .order_by(func.date(Sales.date_)).all()
    )

    # Format dates like "January 1", "January 2", etc.
    dates = [datetime.strptime(row[0], '%Y-%M-%d').strftime("%B %d") for row in results1]
    totals = [row[1] for row in results1]

    line = go.Scatter(x=dates, y=totals, mode='lines+markers')
    layout1 = go.Layout(title="monthly sales over time", xaxis=dict(title='Month'), yaxis=dict(title='Total Sales'))
    fig1 = go.Figure(data=[line], layout=layout1)
    chart_div1 = plot.plot(fig1, include_plotlyjs=True, output_type='div')

    results2 = (
        db.session.query(
            Order.payment, func.count(Order.id)
        ).group_by(Order.payment).filter(Order.pharmacy_id == mypharmacy.id).all()
    )
    methods = [row[0] for row in results2]
    counts = [row[1] for row in results2]

    pie = go.Pie(labels=methods, values=counts)
    layout2 = go.Layout(title="Payment Method Distribution")
    fig2 = go.Figure(data=[pie], layout=layout2)

    chart_div2 = plot.plot(fig2, include_plotlyjs=True, output_type='div')

    pending_orders = len(Order.query.filter(
        extract('month', Order.create_at) == current_month,
        extract('year', Order.create_at) == current_year,
        (Order.status == "Pending"), (Order.pharmacy_id==mypharmacy.id)).all())
    if not pending_orders:
        pending_orders = 0
    pharmacy_id = session.get('pharmacy_id')
    pharmacy = Pharmacy.query.get_or_404(pharmacy_id)    
    return render_template('pharmacy/updated_reports.html', chart1=chart_div1 , chart=chart_div,
                           chart2=chart_div2, total_sales=total_sales,
                           total_annual_sales=get_annual_sales(mypharmacy.id), pending_orders=pending_orders,
                           pharmacy=pharmacy)



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

