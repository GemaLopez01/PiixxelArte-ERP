import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_login import login_user, logout_user, login_required, current_user
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

# Load env variables
load_dotenv()

from app.extensions import db, login_manager, migrate
from app.models.user import User
import app.models  # Ensure all models are loaded

app = Flask(__name__, template_folder='app/templates', static_folder='app/static')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default-secret-key-for-dev')
# Use PostgreSQL if provided, otherwise fallback to SQLite for immediate functionality
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///piixxelarte.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads', 'products')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db.init_app(app)
migrate.init_app(app, db)
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Por favor inicie sesión para acceder a esta página.'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@app.route("/", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Credenciales inválidas. Por favor, intente de nuevo.', 'danger')

    return render_template("login.html")

@app.route("/dashboard")
@login_required
def dashboard():
    from datetime import date
    from app.models.order import Order
    from app.models.billing import Invoice
    
    # Calculate metrics
    pending_orders = Order.query.filter_by(status='Pendiente').count()
    in_production = Order.query.filter_by(status='Producción').count()
    ready_orders = Order.query.filter_by(status='Listo').count()
    
    pending_payments = Invoice.query.filter_by(status='Pendiente').count()
    
    # Today's deliveries
    today = date.today()
    today_deliveries = Order.query.filter(db.func.date(Order.delivery_date) == today).count()
    
    metrics = {
        'pending_orders': pending_orders,
        'in_production': in_production,
        'ready_orders': ready_orders,
        'pending_payments': pending_payments,
        'today_deliveries': today_deliveries
    }
    
    # Recent orders
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
    
    # Date formatting for string
    dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    date_string = f"{dias[today.weekday()]} {today.day} de {meses[today.month - 1]}"

    return render_template(
        "dashboard.html", 
        metrics=metrics, 
        recent_orders=recent_orders,
        date_string=date_string
    )

@app.route("/customers")
@login_required
def customers_index():
    from app.models.customer import Customer
    customers = Customer.query.order_by(Customer.created_at.desc()).all()
    return render_template("customers/index.html", customers=customers)

@app.route("/customers/new", methods=["GET", "POST"])
@login_required
def new_customer():
    from app.models.customer import Customer
    
    if request.method == "POST":
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        
        requires_invoice = request.form.get('requires_invoice') == 'on'
        rfc = request.form.get('rfc') if requires_invoice else None
        business_name = request.form.get('business_name') if requires_invoice else None
        tax_regime = request.form.get('tax_regime') if requires_invoice else None
        zip_code = request.form.get('zip_code') if requires_invoice else None
        billing_address = request.form.get('billing_address') if requires_invoice else None
        
        new_cust = Customer(
            name=name,
            email=email,
            phone=phone,
            requires_invoice=requires_invoice,
            rfc=rfc,
            business_name=business_name,
            tax_regime=tax_regime,
            zip_code=zip_code,
            billing_address=billing_address
        )
        db.session.add(new_cust)
        db.session.commit()
        
        flash('Cliente registrado exitosamente.', 'success')
        return redirect(url_for('customers_index'))
        
    return render_template("customers/form.html", customer=None)

@app.route("/customers/<int:customer_id>/edit", methods=["GET", "POST"])
@login_required
def edit_customer(customer_id):
    from app.models.customer import Customer
    
    customer = Customer.query.get_or_404(customer_id)
    
    if request.method == "POST":
        customer.name = request.form.get('name')
        customer.email = request.form.get('email')
        customer.phone = request.form.get('phone')
        
        customer.requires_invoice = request.form.get('requires_invoice') == 'on'
        if customer.requires_invoice:
            customer.rfc = request.form.get('rfc')
            customer.business_name = request.form.get('business_name')
            customer.tax_regime = request.form.get('tax_regime')
            customer.zip_code = request.form.get('zip_code')
            customer.billing_address = request.form.get('billing_address')
        else:
            customer.rfc = None
            customer.business_name = None
            customer.tax_regime = None
            customer.zip_code = None
            customer.billing_address = None
            
        db.session.commit()
        flash('Cliente actualizado correctamente.', 'success')
        return redirect(url_for('customers_index'))
        
    return render_template("customers/form.html", customer=customer)

@app.route("/customers/<int:customer_id>/delete", methods=["POST"])
@login_required
def delete_customer(customer_id):
    from app.models.customer import Customer
    from app.models.order import Order
    
    customer = Customer.query.get_or_404(customer_id)
    
    # Check if they have orders
    orders_count = Order.query.filter_by(customer_id=customer.id).count()
    if orders_count > 0:
        flash(f'No se puede eliminar el cliente porque tiene {orders_count} pedido(s) asociado(s).', 'danger')
    else:
        db.session.delete(customer)
        db.session.commit()
        flash('Cliente eliminado correctamente.', 'success')
        
    return redirect(url_for('customers_index'))

@app.route("/orders")
@login_required
def orders_index():
    from app.models.order import Order
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template("orders/index.html", orders=orders)

@app.route("/orders/new", methods=["GET", "POST"])
@login_required
def new_order():
    from app.models.customer import Customer
    from app.models.product import Product
    from app.models.order import Order, OrderItem
    from datetime import datetime
    
    if request.method == "POST":
        customer_id = request.form.get('customer_id')
        title = request.form.get('title')
        
        delivery_date_str = request.form.get('delivery_date')
        delivery_date = datetime.strptime(delivery_date_str, '%Y-%m-%d') if delivery_date_str else None
        has_design = request.form.get('has_design') == 'on'
        
        # Arrays from dynamic table fields
        product_ids = request.form.getlist('product_id[]')
        quantities = request.form.getlist('quantity[]')
        widths = request.form.getlist('width[]')
        heights = request.form.getlist('height[]')
        
        discount_amount_str = request.form.get('discount_amount')
        discount_amount = float(discount_amount_str) if discount_amount_str else 0.0
        
        # We start with 0, we'll accumulate throughout the loop
        total_amount = 0.0
        
        # Create Order (Base)
        new_order = Order(
            customer_id=customer_id,
            user_id=current_user.id,
            title=title,
            has_design=has_design,
            delivery_date=delivery_date,
            total_amount=0.0, # Will be updated after saving items
            status='Pendiente'
        )
        db.session.add(new_order)
        db.session.flush() # Get the new_order.id
        
        # Loop over the items
        for i in range(len(product_ids)):
            if not product_ids[i]: # Skip empty rows
                continue
                
            p_id = product_ids[i]
            qty = int(quantities[i]) if quantities[i] else 1
            w = float(widths[i]) if widths[i] else None
            h = float(heights[i]) if heights[i] else None
            
            product = db.session.get(Product, p_id)
            if not product:
                continue

            # Calculate effective price per piece based on dimensions and min_price
            unit_price = product.calculate_unit_price(width=w, height=h)
            subtotal = unit_price * qty

            # Add implicit tax logic (if desired later, could accumulate here, assuming base_price includes tax or is subtotal) # TODO
            if product.has_tax:
                subtotal = subtotal * 1.16

            # Automatic discount logic
            discount_applied = False
            if product.min_qty_discount and product.discount_percentage:
                if qty >= product.min_qty_discount:
                    discount_fraction = float(product.discount_percentage) / 100.0
                    subtotal = subtotal * (1.0 - discount_fraction)
                    discount_applied = True

            total_amount += subtotal

            # Create OrderItem
            new_item = OrderItem(
                order_id=new_order.id,
                product_id=p_id,
                quantity=qty,
                width=w,
                height=h,
                unit_price=unit_price,
                discount_applied=discount_applied,
                subtotal=subtotal
            )
            db.session.add(new_item)
            
        new_order.subtotal_amount = total_amount
        new_order.discount_amount = discount_amount
        new_order.total_amount = total_amount - discount_amount
        db.session.commit()
        
        flash('Pedido creado exitosamente con múltiples productos.', 'success')
        return redirect(url_for('orders_index'))
        
    # GET: fetch customers and products for the dropdowns
    customers = Customer.query.order_by(Customer.name.asc()).all()
    products = Product.query.order_by(Product.name.asc()).all()
    
    return render_template("orders/new.html", customers=customers, products=products)


@app.route("/orders/<int:order_id>/edit", methods=["GET", "POST"])
@login_required
def edit_order(order_id):
    from app.models.customer import Customer
    from app.models.product import Product
    from app.models.order import Order, OrderItem
    from datetime import datetime

    order = Order.query.get_or_404(order_id)
    order_items = OrderItem.query.filter_by(order_id=order.id).all()

    if request.method == "POST":
        customer_id = request.form.get('customer_id')
        title = request.form.get('title')
        
        delivery_date_str = request.form.get('delivery_date')
        delivery_date = datetime.strptime(delivery_date_str, '%Y-%m-%d') if delivery_date_str else None
        has_design = request.form.get('has_design') == 'on'
        status = request.form.get('status') or order.status

        # Update base order
        order.customer_id = customer_id
        order.title = title
        order.has_design = has_design
        order.delivery_date = delivery_date
        order.status = status
        
        # Arrays from dynamic table fields
        product_ids = request.form.getlist('product_id[]')
        quantities = request.form.getlist('quantity[]')
        widths = request.form.getlist('width[]')
        heights = request.form.getlist('height[]')
        
        discount_amount_str = request.form.get('discount_amount')
        discount_amount = float(discount_amount_str) if discount_amount_str else 0.0
        
        # For simplicity in editing multiple items, we wipe existing items and recreate them
        OrderItem.query.filter_by(order_id=order.id).delete()
        
        total_amount = 0.0

        # Create new OrderItems
        for i in range(len(product_ids)):
            if not product_ids[i]: # Skip empty rows
                continue
                
            p_id = product_ids[i]
            qty = int(quantities[i]) if quantities[i] else 1
            w = float(widths[i]) if widths[i] else None
            h = float(heights[i]) if heights[i] else None
            
            product = db.session.get(Product, p_id)
            if not product:
                continue

            # Calculate effective price per piece based on dimensions and min_price
            unit_price = product.calculate_unit_price(width=w, height=h)
            subtotal = unit_price * qty

            # Add implicit tax logic (if desired later, could accumulate here, assuming base_price includes tax or is subtotal) # TODO
            if product.has_tax:
                subtotal = subtotal * 1.16

            # Automatic discount logic
            discount_applied = False
            if product.min_qty_discount and product.discount_percentage:
                if qty >= product.min_qty_discount:
                    discount_fraction = float(product.discount_percentage) / 100.0
                    subtotal = subtotal * (1.0 - discount_fraction)
                    discount_applied = True

            total_amount += subtotal

            # Create OrderItem
            new_item = OrderItem(
                order_id=order.id,
                product_id=p_id,
                quantity=qty,
                width=w,
                height=h,
                unit_price=unit_price,
                discount_applied=discount_applied,
                subtotal=subtotal
            )
            db.session.add(new_item)
            
        order.subtotal_amount = total_amount
        order.discount_amount = discount_amount
        order.total_amount = total_amount - discount_amount
        db.session.commit()
        
        flash('Pedido actualizado correctamente.', 'success')
        return redirect(url_for('orders_index'))

    customers = Customer.query.order_by(Customer.name.asc()).all()
    products = Product.query.order_by(Product.name.asc()).all()

    return render_template(
        "orders/edit.html",
        order=order,
        order_items=order_items,
        customers=customers,
        products=products
    )


@app.route("/orders/<int:order_id>/delete", methods=["POST"])
@login_required
def delete_order(order_id):
    from app.models.order import Order
    from app.models.billing import Invoice

    order = Order.query.get_or_404(order_id)

    # Remove invoices related to this order
    Invoice.query.filter_by(order_id=order.id).delete()

    db.session.delete(order)
    db.session.commit()

    flash('Pedido eliminado correctamente.', 'success')
    return redirect(url_for('orders_index'))

@app.route("/products")
@login_required
def products_index():
    from app.models.product import Product
    products = Product.query.order_by(Product.name.asc()).all()
    return render_template("products/index.html", products=products)

@app.route("/products/new", methods=["GET", "POST"])
@login_required
def new_product():
    from app.models.product import Product
    
    if request.method == "POST":
        code = request.form.get('code')
        name = request.form.get('name')
        description = request.form.get('description')
        base_price = request.form.get('base_price')
        unit_measure = request.form.get('unit_measure', 'Pieza')
        has_tax = request.form.get('has_tax') == 'on'
        
        min_qty_discount = request.form.get('min_qty_discount')
        discount_percentage = request.form.get('discount_percentage')
        min_qty_discount = int(min_qty_discount) if min_qty_discount else None
        discount_percentage = float(discount_percentage) if discount_percentage else None
        
        min_price = request.form.get('min_price')
        min_price = float(min_price) if min_price else None
        
        # Handle file upload
        image_path = None
        if 'image' in request.files:
            file = request.files['image']
            if file.filename != '':
                filename = secure_filename(file.filename)
                # To avoid collisions we could prepend a timestamp, but let's keep it simple
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_path = f'uploads/products/{filename}'
        
        # dynamic pricing flag compatibility based on unit
        is_dynamic = unit_measure.lower() in ['m2', 'metro lineal']
        
        new_prod = Product(
            code=code,
            name=name,
            description=description,
            base_price=float(base_price),
            unit_measure=unit_measure,
            has_tax=has_tax,
            image_path=image_path,
            is_dynamic_pricing=is_dynamic,
            min_qty_discount=min_qty_discount,
            discount_percentage=discount_percentage,
            min_price=min_price
        )
        db.session.add(new_prod)
        db.session.commit()
        
        flash('Producto agregado exitosamente.', 'success')
        return redirect(url_for('products_index'))
        
    return render_template("products/form.html", product=None)

@app.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
@login_required
def edit_product(product_id):
    from app.models.product import Product
    
    product = Product.query.get_or_404(product_id)
    
    if request.method == "POST":
        product.code = request.form.get('code')
        product.name = request.form.get('name')
        product.description = request.form.get('description')
        product.base_price = float(request.form.get('base_price'))
        product.unit_measure = request.form.get('unit_measure', 'Pieza')
        product.has_tax = request.form.get('has_tax') == 'on'
        
        min_qty_discount = request.form.get('min_qty_discount')
        product.min_qty_discount = int(min_qty_discount) if min_qty_discount else None
        
        discount_percentage = request.form.get('discount_percentage')
        product.discount_percentage = float(discount_percentage) if discount_percentage else None
        
        min_price = request.form.get('min_price')
        product.min_price = float(min_price) if min_price else None
        
        product.is_dynamic_pricing = product.unit_measure.lower() in ['m2', 'metro lineal']
        
        if 'image' in request.files:
            file = request.files['image']
            if file.filename != '':
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                product.image_path = f'uploads/products/{filename}'
                
        db.session.commit()
        flash('Producto actualizado correctamente.', 'success')
        return redirect(url_for('products_index'))
        
    return render_template("products/form.html", product=product)

@app.route("/products/<int:product_id>/delete", methods=["POST"])
@login_required
def delete_product(product_id):
    from app.models.product import Product
    from app.models.order import OrderItem
    
    product = Product.query.get_or_404(product_id)
    
    # Check dependencies
    if OrderItem.query.filter_by(product_id=product.id).count() > 0:
        flash('No se puede eliminar el producto porque está siendo utilizado en pedidos.', 'danger')
    else:
        db.session.delete(product)
        db.session.commit()
        flash('Producto eliminado correctamente.', 'success')
        
    return redirect(url_for('products_index'))


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(debug=True)