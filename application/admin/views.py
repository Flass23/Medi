from flask import render_template, redirect, url_for, request, flash, current_app, jsonify
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, extract, or_
from ..models import User, Product, Sales, Order, Cart, OrderItem
from datetime import datetime,timedelta
import calendar
from flask_login import login_required, current_user, logout_user,  LoginManager
from . import admin
from ..forms import addmore, removefromcart, UpdateForm, ProductForm, \
    updatestatusform, update,CartlistForm, Search
from ..models import db
import os
import secrets
from PIL import Image
from flask import current_app
import plotly.graph_objs as go
import plotly.offline as plot



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
    return User.query.get(int(user_id))


@admin.route('/adminpage', methods=["POST", "GET"])
@login_required
def adminpage():
    # Get today's date
    today = datetime.utcnow()
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
        previous_year = current_year -1
    else:
        previous_month = current_month -1
        previous_year = current_year
    start_of_prev_month = today.replace(year=previous_year, month=previous_month, day=1, hour=0, minute=0, microsecond=0)
    temp_next = start_of_prev_month.replace(day=28) + timedelta(days=4)
    end_of_prev_month = temp_next.replace(hour=23, minute=59, second=59, microsecond=999999)

    prev_monthly_sales = db.session.query(func.sum(Sales.price*Sales.quantity)).filter(Sales.date_ >= start_of_prev_month).scalar() or 0.0
    ## MoM Growth rate

    total_annual_sales = db.session.query(func.sum(Sales.price * Sales.quantity)) \
    .filter(Sales.date_ >= start_of_year, Sales.date_ <= end_of_year).scalar()
    total_annual_sales = total_annual_sales if total_annual_sales else 0.00


    # Query to calculate total sales in the current month
    total_sales = db.session.query(func.sum(Sales.price * Sales.quantity)) \
        .filter(Sales.date_ >= start_of_month, Sales.date_ <= end_of_month) \
        .scalar()

    # If no sales are found, return 0
    total_sales = total_sales if total_sales else 0.0
    pending_orders = len(Order.query.filter(
        extract('month', Order.create_at) == current_month,
        extract('year', Order.create_at) == current_year,
        (Order.status == "Pending")).all())
    if not pending_orders:
        pending_orders = 0


    username = current_user.username
    user_count = len(User.query.filter_by(isadmin=False).all())

    if prev_monthly_sales > 0:
        mom_growth = ((total_sales - prev_monthly_sales) / prev_monthly_sales) *100
    else:
        mom_growth = 0

    return render_template('admin/updated_dashboard.html', username = username, total_sales=total_sales,
                           current_year=today.year, current_month=today.strftime('%B'),
                           user_count=user_count, pending_orders=pending_orders, total_annual_sales=total_annual_sales, mom_growth=round(mom_growth, 2))


@admin.route('/search', methods=['POST', 'GET'])
@login_required
def search():
    form = CartlistForm()
    form2 = Search()
    keyword = form2.keyword.data
    item_picture = 'dfdfdf.jpg'
    total_count = 0
    count = Cart.query.filter_by(user_id=current_user.id).first()
    if count:
        total_count = sum(item.quantity for item in count.cart_items)
    products = Order.query.filter(
        Order.order_id.like(f'%{keyword}%')|
        Order.location.like(f'%{keyword}%' |
        Order.user_id.like(f'%{keyword}%') |
        Order.payment.like(f'%{keyword}%') |
        Order.user_email.like(f'%{keyword}%')
                            ).all())

    return render_template('admin/updated_orders.html', form=form, item_picture=item_picture,
                           total_count=total_count, products=products, form2=form2)





@admin.route('/updateproduct/<int:item_id>', methods=['GET', 'POST'])
@login_required
def updateproduct(item_id):
    if not current_user.isadmin:
        return redirect(url_for('home'))
    form = update()
    if form.validate_on_submit():

        product = Product.query.filter_by(id=item_id).first()
        if product:
            product.productname = form.newname.data
            product.description = form.newdescription.data
            product.category = form.category.data
            product.price = form.newprice.data

        try:
            db.session.commit()
            return redirect(url_for('admin.products'))
        except IntegrityError:
            db.session.rollback()

            return redirect(url_for('admin.products'))
    return render_template('admin/updated_updateproduct.html', form=form, item_id=item_id)

@admin.route('/orders')
@login_required
def orders():
    form = updatestatusform()
    form2 = Search()
    orders = Order.query.filter(Order.status=="Pending").all()
    approved_order = Order.query.filter_by(status="Approved").all()

    #total = sum(item.product.price * item.quantity for item in orders.order_items)
    return render_template("admin/updated_orders.html", form=form,form2=form2, orders=orders, approved_order=approved_order)

@admin.route('/delivered')
@login_required
def delivered_orders():
    form = updatestatusform()
    orders = Order.query.filter_by(status="Completed").all()
    #total = sum(item.product.price * item.quantity for item in orders.order_items)
    return render_template("admin/updated_Delivered.html", form=form, orders=orders)

@admin.route('/cancelled')
@login_required
def cancelled_orders():
    form = updatestatusform()
    orders = Order.query.filter_by(status="Cancelled").all()
    #total = sum(item.product.price * item.quantity for item in orders.order_items)
    return render_template("admin/updated_cancelled.html", form=form, orders=orders)


@admin.route('/orders/updatestatus/<int:order_id>', methods=['POST'])
@login_required
def updatestatus(order_id):

    form = updatestatusform()
    if form.validate_on_submit():
        order = Order.query.get_or_404(order_id)
        order.status = form.status.data


        print('done updating')
        db.session.add(order)
        db.session.commit()
    return redirect(url_for('admin.orders'))


@admin.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('auth.newlogin'))



@admin.route('/addproducts', methods=["POST", "GET"])
@login_required
def addproducts():
    if not current_user.isadmin:
        return redirect(url_for('main.home'))

    form = ProductForm()
    if request.method == 'POST':
        if form.is_submitted():
            if form.validate_on_submit:
                product = Product(productname=form.product_name.data, price=form.product_price.data, quantity=form.product_quantity.data,
                                  description=form.product_description.data)
                file = form.product_pictures.data
                product.category = form.category.data

                _image = save_product_picture(file)
                product.pictures = _image
                db.session.add(product)
                db.session.commit()
                print('picture saved')

                return redirect(url_for("admin.products"))
        else:
            flash("An error occurred")
    return render_template("admin/updated_addProduct.html", form=form)


@admin.route('/userorders/<int:order_id>', methods=['post', 'get'])
@login_required
def vieworders(order_id):
    cart = Cart.query.filter_by(user_id=current_user.id).first()
    user_order = Order.query.filter_by(id=order_id).first()
    total = 0.00
    if user_order:

        gross_total = sum(item.product.price * item.quantity for item in user_order.order_items)

        total=gross_total
    else:
        flash('Order does no longer exist')
        db.session.delete(user_order)
        db.session.commit()
        return redirect(url_for('admin.orders'))
    return render_template('admin/updated_vieworders.html', user_order=user_order, total=total)


@admin.route('/top_selling')
@login_required
def top_selling():
    #query the data
    today = datetime.utcnow()
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
        Sales.date_ >= start_of_prev_month).scalar() or 0.0
    ## MoM Growth rate

    total_annual_sales = db.session.query(func.sum(Sales.price * Sales.quantity)) \
        .filter(Sales.date_ >= start_of_year, Sales.date_ <= end_of_year).scalar()
    total_annual_sales = total_annual_sales if total_annual_sales else 0.00

    # Query to calculate total sales in the current month
    total_sales = db.session.query(func.sum(Sales.price * Sales.quantity)) \
        .filter(Sales.date_ >= start_of_month, Sales.date_ <= end_of_month) \
        .scalar()

    # If no sales are found, return 0
    total_sales = total_sales if total_sales else 0.0
    pending_orders = len(Order.query.filter(
        extract('month', Order.create_at) == current_month,
        extract('year', Order.create_at) == current_year,
        (Order.status == "Pending")).all())
    if not pending_orders:
        pending_orders = 0

    username = current_user.username
    user_count = len(User.query.filter_by(isadmin=False).all())

    if prev_monthly_sales > 0:
        mom_growth = ((total_sales - prev_monthly_sales) / prev_monthly_sales) * 100
    else:
        mom_growth = 0

    results = (db.session.query(Product.productname, func.sum(OrderItem.quantity*OrderItem.product_price).label('total Revenue')
                                )
               .join(Product, Product.id == OrderItem.product_id)
               .group_by(Product.productname)
               .order_by(func.sum(OrderItem.quantity*OrderItem.product_price).desc())).all()

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
                         func.sum(Sales.price).label('daily total')
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
        ).group_by(Order.payment).all()
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
        .order_by(func.date(Sales.date_)).all()
    )

    if not daily_sales:

        flash('There is no data yet')

    else:

        monthly_data = {}
        for sale_date, daily_total in daily_sales:
            if isinstance(sale_date, str):
                sale_date = datetime.strptime(sale_date, "%Y-%m-%d").date()
                year = sale_date.year
                month = sale_date.month
                key = (year, month)
                if key not in monthly_data:
                    monthly_data[key] = []
                    monthly_data[key].append((sale_date, daily_total))

            x = []
            open_data = []
            high_data = []
            low_data = []
            close_data = []

            for (year, month), sales in sorted(monthly_data.items()):
                sales_sorted = sorted(sales, key=lambda x:x[0])
                daily_totals = [total for _, total in sales_sorted]
                open_price = daily_totals[0]
                close_price = daily_totals[-1]
                high_price = max(daily_totals)
                low_price = min(daily_totals)
                date_label = f"{calendar.month_name[month]} {year}"

                x.append(date_label)
                open_data.append(open_price)
                high_data.append(high_price)
                low_data.append(low_price)
                close_data.append(close_price)

                candlestick = go.Candlestick(x=x, open=open_data, high=high_data, low=low_data, close=close_data,
                                             increasing_line_color='green',
     decreasing_line_color='red')
                layout3 = go.Layout(title='Monthly Sales Candlestick chart', xaxis_title="Month", yaxis_title='Sales Amount', xaxis=dict(type='category')
                                    )
                fig = go.Figure(data=[candlestick], layout=layout3)
    chart_div3 = plot.plot(fig, include_plotlyjs=True, output_type='div')
    return render_template('admin/updated_reports.html', chart1=chart_div1 , chart=chart_div,
                           chart2=chart_div2, chart3=chart_div3, total_sales=total_sales,
                           total_annual_sales=total_annual_sales,pending_orders=pending_orders)



@admin.route('/products')
@login_required
def products():
    if not current_user.isadmin:
        return redirect(url_for('main.home'))
    form2 = removefromcart()
    form4 = Search()
    form3 = addmore()
    form = update()
    product = Product.query.all()

    return render_template('admin/updated_products.html', product=product, form4=form4, form=form, form2=form2, form3=form3)


@admin.route('/accounts')
@login_required
def accounts():
    # Query non-admin users with pagination
    non_admin_users = User.query.filter_by(isadmin=False).all()

    return render_template('admin/accounts.html', non_admin_users=non_admin_users)

    
@admin.route('/remove_from_products/<int:item_id>', methods=['POST', 'GET'])
@login_required
def remove_from_products(item_id):
    product = Product.query.filter_by(id=item_id).first()
    if product:
        product.quantity -= 1
        db.session.add(product)
        if product.quantity <= 0:
            db.session.delete(product)
    db.session.commit()
    return redirect(url_for('admin.products'))


@admin.route('/add_products/<int:item_id>', methods=['POST', 'GET'])
@login_required
def add_products(item_id):
    product = Product.query.filter_by(id=item_id).first()
    if product:
        product.quantity += 1
        if product.quantity <= 0:
            db.session.delete(product)

    db.session.commit()
    return redirect(url_for('admin.products'))

