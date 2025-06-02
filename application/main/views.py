import os
import secrets
from flask import render_template, redirect, request, url_for, flash, session, jsonify
from flask_login import login_required, current_user, logout_user # type: ignore
from sqlalchemy.exc import IntegrityError
from sqlalchemy import desc, or_
from . import main
from ..forms import *
from ..models import *
from PIL import Image

PRODUCTS_PER_PAGE = 9

@login_manager.user_loader
def load_user(user_id):
    user_type = session.get('user_type')
    if user_type == 'pharmacy':
        return Pharmacy.query.get(int(user_id))
    elif user_type == 'customer':
        return User.query.get(int(user_id))
    return None 

def calculate_loyalty_points(user, sale_amount):
    points_earned = int(sale_amount // 10) #a point for each 10 spent
    user.loyalty_points = points_earned + int(user.loyalty_points or 0)

    db.session.commit()
    return points_earned

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
    post_image_path = os.path.join(current_app.root_path, current_app.config['UPLOAD_PAYMENT_PROOF'], post_img_fn)

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
    formpharm= Set_PharmacyForm()
    orders = Order.query.all()
    return render_template('customer/orderhistory.html', formpharm=formpharm, orders=orders)

@main.route('/myorder', methods=['GET', 'POST'])
@login_required
def myorders():
    user_id = current_user.id
    form2 = Search()
    formpharm=Set_PharmacyForm()
    pharmacy = Pharmacy.query.get_or_404(session.get('pharmacy_id'))
    formpharm.pharmacy.choices=[(-1, "Select a Pharmacy")] + [(p.id, p.name) for p in Pharmacy.query.all()]
    
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
                           user=user, total=total, formpharm=formpharm, pharmacy=pharmacy, form2=form2)


@main.route('/completed_orders')
@login_required
def completed_order():
    user_id = current_user.id
    formpharm=Set_PharmacyForm()
    pharmacy = Pharmacy.query.get_or_404(session.get('pharmacy_id'))
    formpharm.pharmacy.choices=[(-1, "Select a Pharmacy")] + [(p.id, p.name) for p in Pharmacy.query.all()]
    user = User.query.get_or_404(user_id)
    orders_completed = Order.query.filter(user_id==current_user.id, Order.status=="Ready").order_by(desc(Order.create_at)).all()
    return render_template('customer/updated_complete.html', user=user, formpharm=formpharm, pharmacy=pharmacy, orders_completed = orders_completed)


@main.route('/cancelled_orders', methods=['GET', 'POST'])
@login_required
def cancelled_orders():
    formpharm=Set_PharmacyForm()
    user_id = current_user.id
    pharmacy = Pharmacy.query.get_or_404(session.get('pharmacy_id'))
    formpharm.pharmacy.choices=[(-1, "Select a Pharmacy")] + [(p.id, p.name) for p in Pharmacy.query.all()]
    user = User.query.get_or_404(user_id)
    discount=0.00
    total = 0.00
    order = Order.query.filter_by(user_id=current_user.id, status="Cancelled").all()
    return render_template('customer/updated_cancelled.html', order=order,pharmacy=pharmacy, formpharm=formpharm, user=user)
 
@main.route('/home', methods=["POST", "GET"])
@login_required
def home():
    formpharm = Set_PharmacyForm()
    pharmacies = Pharmacy.query.all()
    formpharm.pharmacy.choices=[(-1, "Select a Pharmacy")] + [(p.id, p.name) for p in Pharmacy.query.all()]
    pharmacy_id = session.get('pharmacy_id')
    count = Cart.query.filter(Cart.user_id==current_user.id, Cart.pharmacy_id == pharmacy_id).first()
    if count:
        count = sum(item.quantity for item in count.cart_items)

    return render_template("customer/home.html", user=current_user, total_count=count, pharmacies=pharmacies, formpharm=formpharm)


@main.route("/", methods=["POST", "GET"])
def landing():
    formpharm = Set_PharmacyForm()
    formpharm.pharmacy.choices=[(-1, "Select a Pharmacy")] + [(p.id, p.name) for p in Pharmacy.query.all()]
    return render_template('customer/landingpage.html', formpharm=formpharm)

@main.route('/cartlist', methods=['GET', 'POST'])
@login_required
def cart():
    form = CartlistForm()
    form2 = removefromcart()
    form3 = confirmpurchase()
    formpharm = Set_PharmacyForm()
    formpharm.pharmacy.choices=[(-1, "Select a Pharmacy")] + [(p.id, p.name) for p in Pharmacy.query.all()]
    pharmacy_id = session.get('pharmacy_id')
    user_id = current_user.id
    user = User.query.get_or_404(user_id)
    cart = Cart.query.filter(user_id==user.id, Cart.pharmacy_id == pharmacy_id).first()
    total_amount = 0.00
    total_count = 0
    count = Cart.query.filter(Cart.user_id==current_user.id, Cart.pharmacy_id == session.get('pharmacy_id')).first()
    if count:
        total_count = sum(item.quantity for item in count.cart_items)

    if cart:
        total_amount = sum(item.product.price * item.quantity for item in cart.cart_items)
        
        if total_amount > 250:
            #free delivery
            pass
        else:
            total_amount = total_amount + 13 ## include transportation fees
            


    return render_template('customer/updated_cartlist.html', form=form, form3=form3, form2=form2,
                           cart=cart, user=user,formpharm=formpharm, total_amount=total_amount, total_count=total_count)


@main.route('/about', methods=['POST', 'GET'])
def about():
    formpharm = Set_PharmacyForm()
    formpharm.pharmacy.choices=[(-1, "Select a Pharmacy")] + [(p.id, p.name) for p in Pharmacy.query.all()]
    return render_template('about.html', formpharm=formpharm)


@main.route('/contact', methods=['POST', 'GET'])
def contact():
    formpharm = Set_PharmacyForm()
    formpharm.pharmacy.choices=[(-1, "Select a Pharmacy")] + [(p.id, p.name) for p in Pharmacy.query.all()]    
    return render_template('customer/contact.html')


@main.route('/viewproduct/<int:product_id>', methods=['POST', 'GET'])
def viewproduct(product_id):
    formpharm = Set_PharmacyForm()
    formpharm.pharmacy.choices=[(-1, "Select a Pharmacy")] + [(p.id, p.name) for p in Pharmacy.query.all()]

    form = CartlistForm()
    product = Product.query.filter_by(id=product_id).first()
    pharmacy = Pharmacy.query.get_or_404(session.get('pharmacy_id'))
    item_picture = "dsdsqd"
    if product.pictures is not None:
        item_picture = url_for('static', filename=('css/images/products/' + product.pictures))
    return render_template('customer/updated_productview.html', product=product, pharmacy=pharmacy,
                           formpharm=formpharm, form=form, item_picture=item_picture)

@main.route('/search/<int:page_num>', methods=['POST', 'GET'])
@login_required
def search(page_num):
    form = CartlistForm()
    form2 = Search()
    formpharm=Set_PharmacyForm()
    pharmacy = Pharmacy.query.get_or_404(session.get('pharmacy_id'))
    formpharm.pharmacy.choices=[(-1, "Select a Pharmacy")] + [(p.id, p.name) for p in Pharmacy.query.all()]
    keyword = form2.keyword.data
    products = Product.query.filter(
        Product.productname.like(f'%{keyword}%') |
        Product.description.like(f'%{keyword}%')  |
        Product.category.like(f'%{keyword}%'), 
        Product.pharmacy_id == session.get('pharmacy_id')
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
                           page_num=page_num,formpharm=formpharm, form2=form2, pharmacy=pharmacy)


@main.route('/addorder/<int:total_amount>', methods=['POST', 'GET'])
@login_required
def addorder(total_amount):
    form = confirmpurchase()
    formpharm = Set_PharmacyForm()

    pharmacy_id = session.get('pharmacy_id')
    pharm = Pharmacy.query.get_or_404(pharmacy_id)
    cart = Cart.query.filter_by(user_id=current_user.id).first()
    tyt = total_amount
    print(tyt)
    user = User.query.filter_by(id = current_user.id).first()
    if not cart:

        return redirect(url_for('main.menu'))

    existing_order = Order.query.filter_by(user_id=current_user.id, status='Pending', pharmacy_id=pharmacy_id).first()
    if existing_order:
        flash("You still have a pending order, wait for admin to approve before placing another.", "unsuccessful")
        return redirect(url_for('main.myorders', order_id=existing_order.id))
    else:
        print("Creating a new order")

        neworder = Order(user_id=current_user.id, payment=form.payment.data,
                            user_email=current_user.email, location=form.drop_address.data, pharmacy_id=pharm.id, 
                            source_pharmacy=pharm.name, logitude=form.logitude.data, latitude=form.latitude.data)
        pics = save_product_picture(form.payment_screenshot.data)
        neworder.screenshot = pics
        
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
            flash('Order successfully placed Order. Your payment will be verified shortly')
        except IntegrityError:
            db.session.rollback()
            flash('Happened again')
            print("integrity")
            return redirect(url_for('main.cart'))
        db.session.commit()

        total_amount = 0
        
        for item in cart.cart_items:
            order_item = OrderItem(order_id=neworder.id, product_id=item.product.id, product_name=item.product.productname,
                                   product_price=item.product.price, quantity=item.quantity)

            total_amount += item.product.price*item.quantity
            db.session.add(order_item)
            db.session.commit()

        for i in cart.cart_items:
            sale = Sales(order_id=neworder.id, product_id=i.product.id, product_name=i.product.productname,
            price=i.product.price, quantity=i.quantity, user_id=neworder.user_id, date_=neworder.create_at)
            sale.pharmacy_id = pharm.id
            product = Product.query.filter_by(id=i.product.id).first()
            if product:
                if product.quantity < 0:
                    flash(f'Product {product.productname} is low on quantity')
                    redirect(url_for('main.cart'))
                else:
                    product.quantity -= i.quantity
                    db.session.add(product)
            db.session.add(sale)
            points_earned = calculate_loyalty_points(user, total_amount)
            print(points_earned)
            flash("Purchase successful, you earned {} points.".format(points_earned) )
        CartItem.query.filter_by(cart_id=cart.id).delete()
        db.session.commit()
    flash('Order added and cart cleared')
    return redirect(url_for('main.myorders', total_amount=total_amount))



@main.route("/menu/<int:page_num>", methods=["POST", "GET"])
@login_required
def menu(page_num=1):
    formpharm = Set_PharmacyForm()
    formpharm.pharmacy.choices=[(-1, "Select a Pharmacy")] + [(p.id, p.name) for p in Pharmacy.query.all()]    
    form = CartlistForm()
    form2 = Search()
    products = Product.query.filter(Product.pharmacy_id == session.get('pharmacy_id')).all()
    start = (page_num - 1) * PRODUCTS_PER_PAGE
    end = start + PRODUCTS_PER_PAGE
    current_products = products[start:end]

    total_pages = (len(products) // PRODUCTS_PER_PAGE) + (1 if len(products) % PRODUCTS_PER_PAGE > 0 else 0)

    user_id = current_user.id
    user = User.query.get_or_404(user_id)
    item_picture = 'dfdfdf.jpg'
    total_count = 0
    count = Cart.query.filter(Cart.user_id==current_user.id, Cart.pharmacy_id == session.get('pharmacy_id')).first()
    if count:
        total_count = sum(item.quantity for item in count.cart_items)
    for post in products:
        if post.pictures is not None:
            item_picture = url_for('static', filename=('css/images/products/' + post.pictures))
    mypharmacy = Pharmacy.query.get_or_404(session.get('pharmacy_id'))

    return render_template('customer/updated_menu.html', form=form, item_picture=item_picture,
                           total_count=total_count, form2=form2, formpharm=formpharm, products=current_products, 
                            total_pages=total_pages, page_num=page_num, user=user, pharmacy=mypharmacy)


@main.route('/add_to_cart/<int:item_id>', methods=['POST','GET'])
@login_required
def add_to_cart(item_id):
    form = CartlistForm()
    userid = current_user.id
    page_num = 1
    print('starting...')
    product = Product.query.get_or_404(item_id)
    pharmacy_id = session.get('pharmacy_id')
    cart = Cart.query.filter(Cart.user_id==current_user.id, Cart.pharmacy_id==pharmacy_id).first()
    if not cart:
        print('cart dont exist, creating one')
        cart = Cart(user_id=current_user.id, pharmacy_id=pharmacy_id)
        print('creation done')
        
        db.session.add(cart)

    print('checking cart item...')
    cart_item = CartItem.query.filter_by(cart_id=cart.id, product_id=product.id).first()
    if cart_item:
        print('product exists on cart and incremeted')
        cart_item.quantity+=1

    else:
        print('adding product to cart')
        cart_item = CartItem(cart_id=cart.id, product_id=product.id, quantity=1)
        db.session.add(cart_item)
    total_amount = sum(item.product.price * item.quantity for item in cart.cart_items)
    try:
        db.session.commit()
        flash('Products added to cart.')
    except IntegrityError:
        return redirect(url_for('main.menu',page_num=1))
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

    return redirect(url_for('main.cart', user_id=current_user.id))



@main.route("/account", methods=["GET", "POST"])
@login_required
def account():
    form = UpdateForm()
    formpharm = Set_PharmacyForm()
    formpharm.pharmacy.choices=[(-1, "Select a Pharmacy")] + [(p.id, p.name) for p in Pharmacy.query.all()] 
    
    user = User.query.filter_by(id=current_user.id).first()

    if form.validate_on_submit():
        image_file = save_update_profile_picture(form.picture.data)
        current_user.image_file = image_file
        db.session.commit()
        flash("Account Details Updated Successfully.", "success")
        return redirect(url_for('main.account'))

    image_file = url_for('static', filename='static/images/profiles/ ' + user.image_file)
    pharmacy = session.get('pharmacy_id')
    return render_template('customer/updated_acc.html', user=user, formpharm=formpharm, pharmacy=pharmacy, image_file=image_file, form=form)

   


@main.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have successfully logged out.', 'success')
    return redirect(url_for('main.landing'))


@main.route('/set_pharmacy', methods=['POST', 'GET'])
def set_pharmacy():
    formpharm = Set_PharmacyForm()
    formpharm.pharmacy.choices=[(-1, "Select a Pharmacy")] + [(p.id, p.name) for p in Pharmacy.query.all()]
    if formpharm.validate_on_submit():
        session['pharmacy_id'] = formpharm.pharmacy.data
        return redirect(url_for('main.home', pharmacy_id=formpharm.pharmacy.data))
    elif formpharm.errors:
        print(formpharm.errors)
        return formpharm.errors
    else:
        flash(f'{current_user.id} had a problem selecting your pharmacy, please try again later')
        return redirect(url_for('main.home'))


@main.route('/layout', methods=["POST", "GET"])
def layout():
    formpharm = Set_PharmacyForm()
    pharmacies = Pharmacy.query.all()
    total_count = 0
    pharmacy = Pharmacy.query.get_or_404(session.get('pharmacy_id'))
    count = Cart.query.filter_by(user_id=current_user.id).first()
    if count:
        total_count = sum(item.quantity for item in count.cart_items)
    formpharm.pharmacy.choices = [(p.id, p.name) for p in pharmacies]
    return render_template('layout.html', formpharm=formpharm, total_count=total_count, pharmacy=pharmacy)


    
