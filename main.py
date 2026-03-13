import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_login import login_user, logout_user, login_required, current_user
from dotenv import load_dotenv

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
        product_id = request.form.get('product_id')
        quantity = int(request.form.get('quantity', 1))
        
        # Dimensions are optional but could be relevant based on product
        width = request.form.get('width')
        height = request.form.get('height')
        width = float(width) if width else None
        height = float(height) if height else None
        
        delivery_date_str = request.form.get('delivery_date')
        delivery_date = datetime.strptime(delivery_date_str, '%Y-%m-%d') if delivery_date_str else None
        
        has_design = request.form.get('has_design') == 'on'
        
        # Calculate subtotal based on product
        product = db.session.get(Product, product_id)
        unit_price = product.base_price
        
        # Very basic dynamic pricing concept (e.g for canvas/vinyl)
        if product.is_dynamic_pricing and width and height:
            # e.g price is per square meter
            area = (width / 100) * (height / 100)  # Convert cm to m
            subtotal = area * float(unit_price) * quantity
        else:
            subtotal = float(unit_price) * quantity
            
        # Create Order
        new_order = Order(
            customer_id=customer_id,
            user_id=current_user.id,
            title=title,
            has_design=has_design,
            delivery_date=delivery_date,
            total_amount=subtotal, # Since we only support 1 item per order screen for now
            status='Pendiente'
        )
        db.session.add(new_order)
        db.session.flush() # Get the new_order.id
        
        # Create OrderItem
        new_item = OrderItem(
            order_id=new_order.id,
            product_id=product.id,
            quantity=quantity,
            width=width,
            height=height,
            unit_price=unit_price,
            subtotal=subtotal
        )
        db.session.add(new_item)
        db.session.commit()
        
        flash('Pedido creado exitosamente.', 'success')
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
    order_item = OrderItem.query.filter_by(order_id=order.id).first()

    if request.method == "POST":
        customer_id = request.form.get('customer_id')
        product_id = request.form.get('product_id')
        quantity = int(request.form.get('quantity', 1))

        width = request.form.get('width')
        height = request.form.get('height')
        width = float(width) if width else None
        height = float(height) if height else None

        delivery_date_str = request.form.get('delivery_date')
        delivery_date = datetime.strptime(delivery_date_str, '%Y-%m-%d') if delivery_date_str else None

        status = request.form.get('status') or order.status

        # Update order
        order.customer_id = customer_id
        order.delivery_date = delivery_date
        order.status = status

        # Update order item (if exists)
        if order_item:
            order_item.product_id = product_id
            order_item.quantity = quantity
            order_item.width = width
            order_item.height = height

            # recalc subtotal based on product price and dimensions
            product = db.session.get(Product, product_id)
            unit_price = product.base_price
            order_item.unit_price = unit_price

            if product.is_dynamic_pricing and width and height:
                area = (width / 100) * (height / 100)
                order_item.subtotal = area * float(unit_price) * quantity
            else:
                order_item.subtotal = float(unit_price) * quantity

            order.total_amount = order_item.subtotal

        db.session.commit()
        flash('Pedido actualizado correctamente.', 'success')
        return redirect(url_for('orders_index'))

    customers = Customer.query.order_by(Customer.name.asc()).all()
    products = Product.query.order_by(Product.name.asc()).all()

    return render_template(
        "orders/edit.html",
        order=order,
        order_item=order_item,
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


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(debug=True)