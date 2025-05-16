import os
import secrets
from flask import render_template, redirect, url_for, flash
from flask_login import login_required, current_user, logout_user
from sqlalchemy.exc import IntegrityError
from sqlalchemy import desc, or_
from . import main
from ..forms import *
from ..models import *


PRODUCTS_PER_PAGE = 12
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def calculate_loyalty_points(user, sale_amount):
    points_earned = int(sale_amount // 10) #a point for each 10 spent
    user.loyalty_points = points_earned + int(user.loyalty_points or 0)

    db.session.commit()
    return points_earned

def save_update_profile_picture(form_picture):
    random_hex = secrets.token_hex(9)
    _, f_ex = os.path.splitext(form_picture.filename)
    post_img_Fn = random_hex + f_ex
    post_image_path = os.path.join(current_app.root_path, current_app.config['UPLOAD_PATH'], post_img_Fn)
    form_picture.save(post_image_path)
    return post_img_Fn

@main.route('/order_history')
@login_required
def order_history():
    orders = Order.query.all()
    return render_template('customer/orderhistory.html', orders=orders)

@main.route('/myorder', methods=['GET', 'POST'])
@login_required
def myorders():
    user_id = current_user.id
    form2 = Search()
    user = User.query.get_or_404(user_id)
    discount=0.00
    total = 0.00
    orders = Order.query.filter(Order.user_id==current_user.id, or_(Order.status=="Pending", Order.status=="Approved")).order_by(desc(Order.create_at)).all()

    for o in orders:
        total_amount = sum(item.product.price * item.quantity for item in o.order_items)
        if total_amount >= 180:
            discount = 0.15*total_amount
            total = total_amount - discount

        else:
            total = total_amount
    return render_template('customer/myorder.html',  order=orders,
                           user=user, total=total, form2=form2)


@main.route('/completed_orders')
@login_required
def completed_order():
    user_id = current_user.id
    user = User.query.get_or_404(user_id)
    orders_completed = Order.query.filter(user_id==current_user.id, Order.status=="Completed").order_by(desc(Order.create_at)).all()

    return render_template('customer/updated_complete.html', user=user, orders_completed = orders_completed)


@main.route('/cancelled_orders', methods=['GET', 'POST'])
@login_required
def cancelled_orders():
    user_id = current_user.id
    user = User.query.get_or_404(user_id)
    discount=0.00
    total = 0.00
    order = Order.query.filter_by(user_id=current_user.id, status="Cancelled").all()
    return render_template('customer/updated_cancelled.html', order=order,user=user)

@main.route('/home')
@login_required
def home():
    if current_user.isadmin:
        return redirect(url_for('admin.adminpage'))
    count = Cart.query.filter_by(user_id=current_user.id).first()
    if count:
        count = sum(item.quantity for item in count.cart_items)
    return render_template("customer/home.html", user=current_user, total_count=count)


@main.route("/", methods=["POST", "GET"])
def landing():
    return render_template('customer/landingpage.html')

@main.route('/cartlist', methods=['GET', 'POST'])
@login_required
def cart():
    form = CartlistForm()
    form2 = removefromcart()
    form3 = confirmpurchase()
    user_id = current_user.id
    user = User.query.get_or_404(user_id)
    cart = Cart.query.filter_by(user_id=user.id).first()
    total_amount = 0.00

    if cart:
        total_amount = sum(item.product.price * item.quantity for item in cart.cart_items)
        total_amount = total_amount + 30 ## include transportation fees


    return render_template('customer/updated_cartlist.html', form=form, form3=form3, form2=form2,
                           cart=cart, user=user, total_amount=total_amount)


@main.route('/about', methods=['POST', 'GET'])
def about():
    return render_template('about.html')


@main.route('/contact', methods=['POST', 'GET'])
def contact():
    return render_template('customer/contact.html')


@main.route('/viewproduct/<int:product_id>', methods=['POST', 'GET'])
def viewproduct(product_id):
    form = CartlistForm()
    product = Product.query.filter_by(id=product_id).first()
    item_picture = "dsdsqd"
    if product.pictures is not None:
        item_picture = url_for('static', filename=('css/images/products/' + product.pictures))
    return render_template('customer/updated_productview.html', product=product, form=form, item_picture=item_picture)

@main.route('/search/<int:page_num>', methods=['POST', 'GET'])
@login_required
def search(page_num):
    form = CartlistForm()
    form2 = Search()
    keyword = form2.keyword.data
    products = Product.query.filter(
        Product.productname.like(f'%{keyword}%') |
        Product.description.like(f'%{keyword}%')
    ).all()
    start = (page_num - 1) * PRODUCTS_PER_PAGE
    end = start + PRODUCTS_PER_PAGE
    current_products = products[start:end]

    total_pages = (len(products) // PRODUCTS_PER_PAGE) + (1 if len(products) % PRODUCTS_PER_PAGE > 0 else 0)

    user_id = current_user.id
    user = User.query.get_or_404(user_id)
    item_picture = 'dfdfdf.jpg'
    total_count = 0
    count = Cart.query.filter_by(user_id=current_user.id).first()
    if count:
        total_count = sum(item.quantity for item in count.cart_items)

    for post in products:
        if post.pictures is not None:
            item_picture = url_for('static', filename=('css/images/products/' + post.pictures))
    return render_template('customer/updated_menu.html', form=form, item_picture=item_picture,
                           total_count=total_count, products=current_products, total_pages=total_pages,
                           page_num=page_num, form2=form2)


@main.route('/addorder/<int:total_amount>', methods=['POST', 'GET'])
@login_required
def addorder(total_amount):
    form = confirmpurchase()
    cart = Cart.query.filter_by(user_id=current_user.id).first()
    tyt = total_amount
    print(tyt)
    user = User.query.filter_by(id = current_user.id).first()

    existing_order = Order.query.filter_by(user_id=current_user.id, status='Pending').first()
    if existing_order:
        flash("You still have a pending order, wait for admin to approve before placing another.", "unsuccessful")
        return redirect(url_for('main.myorders', order_id=existing_order.id))
    else:
        print("Creating a new order")

        neworder = Order(user_id=current_user.id, payment=form.payment.data,
                            user_email=current_user.email, location=form.drop_address.data)
        #hashed_order = flask_bcrypt.generate_password_hash(neworder.id)
        if form.transid.data:
            print("form id found")
            neworder.transactionID = form.transid.data
        else:
            print("no id")
            neworder.transactionID ='None'
        db.session.add(neworder)
        try:
            print('committing...')
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash('Happened again')
            print("integrity")
            return redirect(url_for('main.cart'))
        db.session.commit()

        total_amount = 0
        if not cart:
            flash("Can not add order, cart empty")
            return redirect(url_for('main.home'))

        for item in cart.cart_items:
            order_item = OrderItem(order_id=neworder.id, product_id=item.product.id, product_name=item.product.productname,
                                   product_price=item.product.price, quantity=item.quantity)

            total_amount += item.product.price*item.quantity
            db.session.add(order_item)
            db.session.commit()

        for i in cart.cart_items:
            sale = Sales(order_id=neworder.id, product_id=i.product.id, product_name=i.product.productname,
            price=i.product.price, quantity=i.quantity, user_id=neworder.user_id, date_=neworder.create_at)
            product = Product.query.filter_by(id=i.product.id).first()
            if product:
                if product.quantity > 0:
                    product.quantity -= i.quantity
                    db.session.add(product)
                else:
                    redirect(url_for('main.cart'))

            db.session.add(sale)
            points_earned = calculate_loyalty_points(user, total_amount)
            print(points_earned)
            flash("Purchase successful, you earned {} points.".format(points_earned) )
        db.session.commit()

        ## clear cart after order
        CartItem.query.filter_by(cart_id=cart.id).delete()
        db.session.commit()
    flash('Order added and cart cleared')
    return redirect(url_for('main.myorders', total_amount=total_amount))



@main.route("/menu/<int:page_num>", methods=["POST", "GET"])
@login_required
def menu(page_num=1):
    form = CartlistForm()
    form2 = Search()
    products = Product.query.all()
    start = (page_num - 1) * PRODUCTS_PER_PAGE
    end = start + PRODUCTS_PER_PAGE
    current_products = products[start:end]

    total_pages = (len(products) // PRODUCTS_PER_PAGE) + (1 if len(products) % PRODUCTS_PER_PAGE > 0 else 0)

    user_id = current_user.id
    user = User.query.get_or_404(user_id)
    item_picture = 'dfdfdf.jpg'
    total_count = 0
    count = Cart.query.filter_by(user_id=current_user.id).first()
    if count:
        total_count = sum(item.quantity for item in count.cart_items)

    for post in products:
        if post.pictures is not None:
            item_picture = url_for('static', filename=('css/images/products/' + post.pictures))
    return render_template('customer/updated_menu.html', form=form, item_picture=item_picture,
                           total_count=total_count, form2=form2, products=current_products, total_pages=total_pages, page_num=page_num)


@main.route('/add_to_cart/<int:item_id>', methods=['POST','GET'])
@login_required
def add_to_cart(item_id):
    form = CartlistForm()
    userid = current_user.id
    page_num = 1
    print('starting...')
    product = Product.query.get_or_404(item_id)
    cart = Cart.query.filter_by(user_id=current_user.id).first()
    if not cart:
        print('cart dont exist, creating one')
        cart = Cart(user_id=current_user.id)
        print('creation done')
        db.session.add(cart)

    print('checking cart item...')
    cart_item = CartItem.query.filter_by(cart_id=cart.id, product_id=product.id).first()
    if cart_item:
        print('product exists on cart')
        cart_item.quantity+=1

    else:
        print('adding product to cart')
        cart_item = CartItem(cart_id=cart.id, product_id=product.id, quantity=1)

        db.session.add(cart_item)
    total_amount = sum(item.product.price * item.quantity for item in cart.cart_items)
    db.session.commit()
    print('donee')

    return redirect(url_for('main.menu', user_id=current_user.id, form=form, page_num=page_num, total_amount=total_amount))


@main.route('/remove_from_cart/<int:item_id>', methods=['POST', 'GET'])
@login_required
def remove_from_cart(item_id):
    cart = Cart.query.filter_by(user_id=current_user.id).first()
    #cart_ = CartItem.query.filter_by(cart_id=cart.id, product_id=item_id).first()
    product = CartItem.query.filter_by(id=item_id).first()
    if product:
        product.quantity -= 1
        db.session.add(product)
        if product.quantity <= 0:
            db.session.delete(product)
    db.session.commit()        #db.session.delete()
    db.session.commit()
    return redirect(url_for('main.cart', user_id=current_user.id))



@main.route("/account", methods=["GET", "POST"])
@login_required
def account():
    form = UpdateForm()
    user = User.query.filter_by(id=current_user.id).first()
    if form.validate_on_submit():
        image_file = save_update_profile_picture(form.picture.data)
        current_user.image_file = image_file
        db.session.commit()
        flash("Account Details Updated sucessfully.", "success")
        return redirect(url_for('main.account'))

    image_file = url_for('static', filename='static/images/profiles/ ' + user.image_file)
    return render_template('customer/updated_acc.html', user=user, image_file=image_file, form=form)

@main.route("/logout")
@login_required
def logout():
    logout_user()
    flash('You have successfully logged out.', 'success')
    return redirect(url_for('main.landing'))