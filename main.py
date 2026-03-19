import os
import time
from flask import Flask, render_template, request, redirect, url_for, session, flash, g
from flask_login import login_user, logout_user, login_required, current_user
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

# Load env variables
load_dotenv()

from app.extensions import db, login_manager, migrate
from app.models.user import User
import app.models  # Ensure all models are loaded
from app.models.customer import Customer
from app.models.product import Product
from app.models.order import Order, OrderItem
from app.models.billing import Invoice
from app.models.inventory import Supplier, Material, InventoryMovement, Purchase, PurchaseItem
from datetime import datetime

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

@app.before_request
def log_and_prepare():
    g.start_time = time.time()
    app.logger.info("%s %s from %s", request.method, request.path, request.remote_addr)

@app.after_request
def set_security_headers(response):
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com https://cdnjs.cloudflare.com; "
        "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
        "img-src 'self' data:; "
        "connect-src 'self';"
    )
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=()"
    response.headers["Cache-Control"] = "no-store"
    if hasattr(g, 'start_time'):
        ms = int((time.time() - g.start_time) * 1000)
        app.logger.debug("Request processing time: %dms", ms)
    return response

@app.errorhandler(404)
def page_not_found(error):
    return render_template("404.html"), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template("500.html"), 500

@app.context_processor
def inject_alerts():
    if current_user.is_authenticated:
        try:
            alerts_count = Material.query.filter(Material.stock_quantity <= Material.min_stock).count()
            # Also count pending/producing items that are on demand
            from app.models.order import Order, OrderItem
            from app.models.product import Product
            
            on_demand_items_count = db.session.query(OrderItem).join(Order).join(Product).filter(
                Product.is_on_demand == True,
                Order.status.in_(['Pendiente', 'Producción'])
            ).count()
            
            total_alerts = alerts_count + on_demand_items_count
            return dict(
                low_stock_alerts_count=alerts_count,
                on_demand_alerts_count=on_demand_items_count,
                total_alerts_count=total_alerts
            )
        except Exception as e:
            return dict(low_stock_alerts_count=0, on_demand_alerts_count=0, total_alerts_count=0)
    return dict(low_stock_alerts_count=0, on_demand_alerts_count=0, total_alerts_count=0)

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
    
    # Financial metrics
    # Note: sum() returns a Decimal or None
    total_sales_result = db.session.query(db.func.sum(Order.total_amount)).scalar()
    total_sales = float(total_sales_result) if total_sales_result else 0.0

    total_advances_result = db.session.query(db.func.sum(Order.advance_payment)).scalar()
    total_advances = float(total_advances_result) if total_advances_result else 0.0

    pending_payments_count = Order.query.filter_by(payment_status='Pendiente de pago').count()
    partial_payments_count = Order.query.filter_by(payment_status='Parcial').count()
    pending_balance = total_sales - total_advances
    
    # Chart Data Preparation (Group by Method)
    methods_data = db.session.query(Order.payment_method, db.func.count(Order.id)).group_by(Order.payment_method).all()
    methods_dict = {method if method else 'No definido': count for method, count in methods_data}

    status_data = db.session.query(Order.payment_status, db.func.count(Order.id)).group_by(Order.payment_status).all()
    status_dict = {status if status else 'Desconocido': count for status, count in status_data}

    # Today's deliveries
    today = date.today()
    today_deliveries = Order.query.filter(db.func.date(Order.delivery_date) == today).count()
    
    metrics = {
        'pending_orders': pending_orders,
        'in_production': in_production,
        'ready_orders': ready_orders,
        'pending_payments': pending_payments_count + partial_payments_count,
        'today_deliveries': today_deliveries,
        'total_sales': total_sales,
        'total_advances': total_advances,
        'pending_balance': pending_balance
    }
    
    # Recent orders
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
    
    # Date formatting for string
    dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    date_string = f"{dias[today.weekday()]} {today.day} de {meses[today.month - 1]}"

    # Monthly sales for current year
    from sqlalchemy import extract
    current_year = today.year
    monthly_sales_data = db.session.query(
        extract('month', Order.created_at).label('month'),
        db.func.sum(Order.total_amount).label('total')
    ).filter(
        extract('year', Order.created_at) == current_year,
        Order.status != 'Cancelado' # Optional guard
    ).group_by(
        extract('month', Order.created_at)
    ).all()
    
    monthly_sales_dict = {mes: 0.0 for mes in meses}
    for row in monthly_sales_data:
        try:
            month_idx = int(row.month) - 1
            if 0 <= month_idx < 12:
                monthly_sales_dict[meses[month_idx]] = float(row.total or 0.0)
        except (ValueError, TypeError):
            pass

    return render_template(
        "dashboard.html", 
        metrics=metrics, 
        recent_orders=recent_orders,
        date_string=date_string,
        methods_dict=methods_dict,
        status_dict=status_dict,
        monthly_sales_dict=monthly_sales_dict
    )

# ==============================================================================
# INVENTORY: MATERIALS
# ==============================================================================
@app.route("/inventory/materials")
@login_required
def inventory_materials():
    materials = Material.query.order_by(Material.name.asc()).all()
    # Identificar aquellos que requieren reabastecimiento
    alerts_count = Material.query.filter(Material.stock_quantity <= Material.min_stock).count()
    
    # Obtener productos bajo demanda de pedidos activos
    from app.models.order import Order, OrderItem
    from app.models.product import Product
    on_demand_items = db.session.query(OrderItem).join(Order).join(Product).filter(
        Product.is_on_demand == True,
        Order.status.in_(['Pendiente', 'Producción'])
    ).all()

    return render_template("inventory/materials.html", 
                           materials=materials, 
                           alerts_count=alerts_count,
                           on_demand_items=on_demand_items)

@app.route("/inventory/materials/new", methods=["GET", "POST"])
@login_required
def new_material():
    if request.method == "POST":
        new_mat = Material(
            name=request.form.get("name"),
            category=request.form.get("category"),
            stock_quantity=request.form.get("stock_quantity", type=float),
            min_stock=request.form.get("min_stock", type=float),
            unit_measure=request.form.get("unit_measure"),
            location=request.form.get("location"),
            approx_cost=request.form.get("approx_cost", type=float),
            supplier_id=request.form.get("supplier_id") or None
        )
        db.session.add(new_mat)
        db.session.commit()
        flash("Material creado exitosamente", "success")
        return redirect(url_for('inventory_materials'))

    suppliers = Supplier.query.order_by(Supplier.name.asc()).all()
    return render_template("inventory/material_form.html", suppliers=suppliers, material=None)

@app.route("/inventory/materials/<int:material_id>/edit", methods=["GET", "POST"])
@login_required
def edit_material(material_id):
    material = Material.query.get_or_404(material_id)
    if request.method == "POST":
        material.name = request.form.get("name")
        material.category = request.form.get("category")
        material.stock_quantity = request.form.get("stock_quantity", type=float)
        material.min_stock = request.form.get("min_stock", type=float)
        material.unit_measure = request.form.get("unit_measure")
        material.location = request.form.get("location")
        material.approx_cost = request.form.get("approx_cost", type=float)
        material.supplier_id = request.form.get("supplier_id") or None
        
        db.session.commit()
        flash("Material actualizado", "success")
        return redirect(url_for('inventory_materials'))

    suppliers = Supplier.query.order_by(Supplier.name.asc()).all()
    return render_template("inventory/material_form.html", suppliers=suppliers, material=material)

# ==============================================================================
# INVENTORY: SUPPLIERS
# ==============================================================================
@app.route("/inventory/suppliers")
@login_required
def inventory_suppliers():
    suppliers = Supplier.query.order_by(Supplier.name.asc()).all()
    return render_template("inventory/suppliers.html", suppliers=suppliers)

@app.route("/inventory/suppliers/new", methods=["GET", "POST"])
@login_required
def new_supplier():
    if request.method == "POST":
        new_sup = Supplier(
            name=request.form.get("name"),
            contact_info=request.form.get("contact_info"),
            phone=request.form.get("phone"),
            email=request.form.get("email"),
            address=request.form.get("address")
        )
        db.session.add(new_sup)
        db.session.commit()
        flash("Proveedor creado exitosamente.", "success")
        return redirect(url_for('inventory_suppliers'))
    
    return render_template("inventory/supplier_form.html", supplier=None)

@app.route("/inventory/suppliers/<int:supplier_id>/edit", methods=["GET", "POST"])
@login_required
def edit_supplier(supplier_id):
    supplier = Supplier.query.get_or_404(supplier_id)
    if request.method == "POST":
        supplier.name = request.form.get("name")
        supplier.contact_info = request.form.get("contact_info")
        supplier.phone = request.form.get("phone")
        supplier.email = request.form.get("email")
        supplier.address = request.form.get("address")
        
        db.session.commit()
        flash("Proveedor actualizado exitosamente.", "success")
        return redirect(url_for('inventory_suppliers'))
    
    return render_template("inventory/supplier_form.html", supplier=supplier)

# ==============================================================================
# INVENTORY: MOVEMENTS
# ==============================================================================
@app.route("/inventory/movements", methods=["GET", "POST"])
@login_required
def inventory_movements():
    if request.method == "POST":
        material_id = request.form.get("material_id")
        movement_type = request.form.get("movement_type")
        quantity = request.form.get("quantity", type=float)
        reason = request.form.get("reason")
        
        if not all([material_id, movement_type, quantity, reason]):
            flash("Todos los campos para el movimiento son obligatorios.", "danger")
            return redirect(url_for('inventory_movements'))
            
        material = Material.query.get_or_404(material_id)
        
        # Guardar en log de movimientos
        new_movement = InventoryMovement(
            material_id=material_id,
            movement_type=movement_type,
            quantity=quantity,
            reason=reason
        )
        db.session.add(new_movement)
        
        # Afectar el stock directamente
        if movement_type == 'Entrada':
            material.stock_quantity += quantity
        elif movement_type == 'Salida':
            material.stock_quantity -= quantity
            
        db.session.commit()
        flash("Movimiento de inventario registrado", "success")
        return redirect(url_for('inventory_movements'))

    movements = InventoryMovement.query.order_by(InventoryMovement.created_at.desc()).limit(100).all()
    materials = Material.query.order_by(Material.name.asc()).all()
    return render_template("inventory/movements.html", movements=movements, materials=materials)

# ==============================================================================
# INVENTORY: PURCHASES
# ==============================================================================
@app.route("/inventory/purchases")
@login_required
def inventory_purchases():
    purchases = Purchase.query.order_by(Purchase.created_at.desc()).all()
    return render_template("inventory/purchases.html", purchases=purchases)

@app.route("/inventory/purchases/new", methods=["GET", "POST"])
@login_required
def new_purchase():
    if request.method == "POST":
        supplier_id = request.form.get("supplier_id")
        material_ids = request.form.getlist("material_id[]")
        quantities = request.form.getlist("quantity[]")
        unit_costs = request.form.getlist("unit_cost[]")
        status = request.form.get("status", "Pendiente")
        
        purchase = Purchase(supplier_id=supplier_id, status=status)
        db.session.add(purchase)
        db.session.flush() # get ID
        
        total_amount = 0.0
        
        for i in range(len(material_ids)):
            if material_ids[i] and quantities[i] and unit_costs[i]:
                mat_id = int(material_ids[i])
                qty = float(quantities[i])
                cost = float(unit_costs[i])
                
                item = PurchaseItem(
                    purchase_id=purchase.id,
                    material_id=mat_id,
                    quantity=qty,
                    unit_cost=cost
                )
                db.session.add(item)
                
                item_total = qty * cost
                total_amount += item_total
                
                # Si se marca como Recibida desde la creación, inyectar el movimiento
                if status == "Recibida":
                    movement = InventoryMovement(
                        material_id=mat_id,
                        movement_type="Entrada",
                        quantity=qty,
                        reason=f"Compra #{purchase.id}"
                    )
                    db.session.add(movement)
                    
                    material = Material.query.get(mat_id)
                    if material:
                        material.stock_quantity += qty
                        
        purchase.total_amount = total_amount
        db.session.commit()
        
        flash("Compra registrada correctamente.", "success")
        return redirect(url_for('inventory_purchases'))
        
    suppliers = Supplier.query.order_by(Supplier.name.asc()).all()
    materials = Material.query.order_by(Material.name.asc()).all()
    return render_template("inventory/purchase_form.html", suppliers=suppliers, materials=materials)

@app.route("/inventory/purchases/<int:purchase_id>/receive", methods=["POST"])
@login_required
def receive_purchase(purchase_id):
    purchase = Purchase.query.get_or_404(purchase_id)
    if purchase.status == "Pendiente":
        purchase.status = "Recibida"
        
        for item in purchase.items:
            movement = InventoryMovement(
                material_id=item.material_id,
                movement_type="Entrada",
                quantity=item.quantity,
                reason=f"Recepción de Compra #{purchase.id}"
            )
            db.session.add(movement)
            
            material = Material.query.get(item.material_id)
            if material:
                material.stock_quantity += item.quantity
                
        db.session.commit()
        flash("Compra marcada como recibida y stock actualizado.", "success")
    else:
        flash("La compra ya había sido recibida.", "info")
        
    return redirect(url_for('inventory_purchases'))

@app.route("/customers")
@login_required
def customers_index():
    from app.models.customer import Customer
    customers = Customer.query.order_by(Customer.created_at.desc()).all()
    return render_template("customers/index.html", customers=customers)

@app.route("/customers/new", methods=["GET", "POST"])
@login_required
def new_customer():
        
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
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template("orders/index.html", orders=orders)

@app.route("/orders/new", methods=["GET", "POST"])
@login_required
def new_order():
    
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
        
        # Financial fields
        advance_payment_str = request.form.get('advance_payment')
        advance_payment = float(advance_payment_str) if advance_payment_str else 0.0
        payment_method = request.form.get('payment_method')
        payment_status = request.form.get('payment_status') or 'Pendiente de pago'
        
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
            status='Pendiente',
            advance_payment=advance_payment,
            payment_method=payment_method,
            payment_status=payment_status
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
            
            # --- Inventory Auto-Discount Logic ---
            if product.material_id:
                material = db.session.get(Material, product.material_id)
                if material:
                    # Calculate quantity to deduct
                    deduction_qty = 0.0
                    if product.unit_measure in ['m2', 'metro lineal'] and w and h:
                        area = w * h
                        deduction_qty = area * qty
                    else:
                        deduction_qty = qty
                        
                    # Deduct from stock
                    material.stock_quantity -= deduction_qty
                    
                    # Create Movement log
                    movement = InventoryMovement(
                        material_id=material.id,
                        movement_type="Salida",
                        quantity=deduction_qty,
                        reason=f"Uso en pedido #{new_order.id}"
                    )
                    db.session.add(movement)
            # -----------------------------------
            
        new_order.subtotal_amount = total_amount
        new_order.discount_amount = discount_amount
        new_order.total_amount = total_amount - discount_amount
        new_order.tax_amount = 0.0  # TODO: Implement if global IVA checkbox added later
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
        
        # Financial fields
        advance_payment_str = request.form.get('advance_payment')
        order.advance_payment = float(advance_payment_str) if advance_payment_str else 0.0
        order.payment_method = request.form.get('payment_method')
        order.payment_status = request.form.get('payment_status') or 'Pendiente de pago'
        
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
            
            # --- Inventory Auto-Discount Logic ---
            if product.material_id:
                material = db.session.get(Material, product.material_id)
                if material:
                    # Calculate quantity to deduct
                    deduction_qty = 0.0
                    if product.unit_measure in ['m2', 'metro lineal'] and w and h:
                        area = w * h
                        deduction_qty = area * qty
                    else:
                        deduction_qty = qty
                        
                    # Deduct from stock
                    material.stock_quantity -= deduction_qty
                    
                    # Create Movement log
                    movement = InventoryMovement(
                        material_id=material.id,
                        movement_type="Salida",
                        quantity=deduction_qty,
                        reason=f"Uso en pedido editado #{order.id}"
                    )
                    db.session.add(movement)
            # -----------------------------------
            
        order.subtotal_amount = total_amount
        order.discount_amount = discount_amount
        order.total_amount = total_amount - discount_amount
        order.tax_amount = 0.0
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
    
    if request.method == "POST":
        code = request.form.get('code')
        name = request.form.get('name')
        description = request.form.get('description')
        base_price = request.form.get('base_price')
        unit_measure = request.form.get('unit_measure', 'Pieza')
        has_tax = request.form.get('has_tax') == 'on'
        is_on_demand = request.form.get('is_on_demand') == 'on'
        
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
            is_on_demand=is_on_demand,
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
    
    product = Product.query.get_or_404(product_id)
    
    if request.method == "POST":
        product.code = request.form.get('code')
        product.name = request.form.get('name')
        product.description = request.form.get('description')
        product.base_price = float(request.form.get('base_price'))
        product.unit_measure = request.form.get('unit_measure', 'Pieza')
        product.has_tax = request.form.get('has_tax') == 'on'
        product.is_on_demand = request.form.get('is_on_demand') == 'on'
        
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