# PiixxelArte ERP Backend Foundation Plan

## Goal Description
Build the foundational database schema and authentication system for PiixxelArte's Flask/PostgreSQL ERP web application. The schema will handle Users, Customers, Products, Orders, Inventory, and Billing. The authentication will securely log in users based on their assigned roles (Administrador, Operativo/Diseño, Producción).

## Proposed Changes

### Database Configuration & Initialization
#### [NEW] [app/extensions.py](file:///c:/Users/amegl/OneDrive/Escritorio/PiixxeArte/app/extensions.py)
Create a centralized file to initialize Flask extensions like `SQLAlchemy` and `Bcrypt/Werkzeug` to avoid circular imports.
#### [MODIFY] [app.py](file:///c:/Users/amegl/OneDrive/Escritorio/PiixxeArte/app.py)
Update the main application file to load configurations (like `SQLALCHEMY_DATABASE_URI` from [.env](file:///c:/Users/amegl/OneDrive/Escritorio/PiixxeArte/.env)), initialize the database, and implement the login logic using the new [User](file:///c:/Users/amegl/OneDrive/Escritorio/PiixxeArte/app/models/user.py#6-29) model. Also configure `flask_login` or session mechanisms.

### Models
We will put the models in an `app/models/` directory. For simplicity in the first iteration, we can group related models.
#### [NEW] `app/models/user.py`
- `User`: `id`, `name`, `email`, `password_hash`, `role` (Admin, Operativo/Diseño, Producción), `is_active`, `created_at`.
#### [NEW] `app/models/customer.py`
- `Customer`: `id`, `name`, `email`, `phone`, `address`, `created_at`.
#### [NEW] `app/models/product.py`
- `Product`: `id`, `name`, `description`, `base_price`, `is_dynamic_pricing` (boolean to flag products sold by meter like vinyl/canvas), `created_at`.
#### [NEW] `app/models/order.py`
- `Order`: `id`, `customer_id`, `user_id`, `status` (pendiente, diseño, producción, listo, entregado), `delivery_date`, `created_at`, `total_amount`.
- `OrderItem`: `id`, `order_id`, `product_id`, `quantity`, `width` (optional for dynamic area), `height` (optional for dynamic area), `unit_price`, `subtotal`.
#### [NEW] `app/models/inventory.py`
- `Supplier`: `id`, `name`, `contact_info`, `phone`.
- `Material`: `id`, `name`, `supplier_id`, `stock_quantity`, `unit_measure` (meters, units, etc.).
#### [NEW] `app/models/billing.py`
- `Invoice`: `id`, `order_id`, `total_amount`, `advance_payment`, `remaining_payment`, `status` (paid, pending).

### Authentication Route
#### [MODIFY] `app.py`
Update the `/` (login) route to verify the input `email` and `password` against the database `User` table using password hash verification. Set the user identity in the Flask session.

---

## Dashboard Details & Execution

### Backend Logic (`main.py`)
Update the `/dashboard` route to dynamically calculate metrics from the Database models instead of passing hardcoded text.

### Frontend Design (`app/templates/` & `app/static/`)
#### [NEW] `app/templates/base.html`
Create a base layout featuring a modern sidebar (for navigation to distinct ERP modules) and a top navigation bar (for user profile and logout). The content block will hold the dashboard.
#### [NEW] `app/static/css/style.css`
A premium vanilla CSS design system featuring.
#### [MODIFY] `app/templates/dashboard.html`
Build the specific HTML structure following the requested sections.

---

## Orders (Pedidos) Module Execution
Based on the requested data (Nombre, piezas, material, medidas, fecha de entrega y diseño), we need to update our base design to accommodate this simplified flow. A "Pedido" form will create both the `Order` and its `OrderItem` at the same time.

### Schema Updates
#### [MODIFY] `app/models/order.py`
Add two new fields to the `Order` model:
- `title = db.Column(db.String(150), nullable=True)`: Para guardar el "Nombre" del trabajo.
- `has_design = db.Column(db.Boolean, default=False)`: Para el checkbox de "¿Ya tienen diseño?".

We will run `flask db migrate` and `flask db upgrade` to apply this to PostgreSQL.

---

## Customers (Clientes) Module Execution
Based on the requirement, the Customer form will primarily ask for Name and Phone. A checkbox "Requiere Factura" will toggle additional fiscal data fields.

### Schema Updates
#### [MODIFY] `app/models/customer.py`
We need to add the following fields to handle billing information:
- `requires_invoice = db.Column(db.Boolean, default=False)`
- `rfc = db.Column(db.String(20), nullable=True)`
- `business_name = db.Column(db.String(150), nullable=True)` (Razón Social)
- `tax_regime = db.Column(db.String(100), nullable=True)` (Régimen Fiscal)
- `zip_code = db.Column(db.String(10), nullable=True)`
- `billing_address = db.Column(db.Text, nullable=True)`

Run `flask db migrate` and `flask db upgrade` to update the DB.

### Backend Routes (`main.py`)
- **[NEW] `GET /customers`**: List all customers in a data table (Name, Phone, Email, Invoice status, Actions).
- **[NEW] `GET/POST /customers/new`**: Render creation form and save the customer to the DB.
- **[NEW] `GET/POST /customers/<id>/edit`**: Edit existing customer details.
- **[NEW] `POST /customers/<id>/delete`**: Soft or hard delete depending on whether they have attached orders.

### Frontend UI (`app/templates/customers/`)
- **[NEW] `app/templates/customers/index.html`**: The customer directory view.
- **[NEW] `app/templates/customers/form.html`**: A reusable form (to be included by `new.html` and `edit.html`). 
  - Contains standard fields: Name, Phone, Email.
  - Contains a Checkbox: **¿Requiere Factura?**.
  - Contains a div `#billing-fields` (RFC, Razón Social, Régimen, CP, Dirección).
  - Contains Vanilla JavaScript mapping an EventListener to the checkbox to toggle the `display` property of the `#billing-fields` div, keeping the interface clean for standard clients.

---

## Products (Productos) Module Execution
Based on the provided requirements, the Products model needs substantial changes to capture codes, taxes, custom units, and an optional image path.

### Schema Updates
#### [MODIFY] `app/models/product.py`
We need to modify the `Product` model entirely:
- `code = db.Column(db.String(50), nullable=True, unique=True)`
- `name = db.Column(db.String(150), nullable=False)`
- `description = db.Column(db.Text, nullable=True)`
- `base_price = db.Column(db.Numeric(10, 2), nullable=False)` (Precio)
- `unit_measure = db.Column(db.String(50), default='Pieza')` (Unidad de medida: m2, metro lineal, pieza)
- `has_tax = db.Column(db.Boolean, default=False)` (Impuestos: 16% checkbox)
- `image_path = db.Column(db.String(255), nullable=True)` (Relative path for image storage)

Run `flask db migrate` and `flask db upgrade` to apply these schema updates.

### Backend Routes (`main.py`)
To handle file uploads safely, we will use Werkzeug's `secure_filename`.
- **[NEW] `GET /products`**: To list all products featuring an image thumbnail.
- **[NEW] `GET/POST /products/new`**: Form submission handling multipart/form-data for the image upload.
- **[NEW] `GET/POST /products/<id>/edit`**: Edit existing product details and replace the image if a new one is uploaded. 
- **[NEW] `POST /products/<id>/delete`**: Remove product logically or entirely.
Images will be saved into `app/static/uploads/products/`.

### Frontend UI (`app/templates/products/`)
- **[NEW] `app/templates/products/index.html`**: The products listing view, showcasing a sleek card grid or modern table. 
- **[NEW] `app/templates/products/form.html`**: A clean, unified form handling file uploads (`enctype="multipart/form-data"`), codes, prices, the unit selector dropdown, and the tax toggle switch.

---

## Multiple Order Items (Multiproducto en Pedidos)
In order to handle more than one product per order, the structure of the Order form needs to transform from standard `<input>` groups to a dynamic HTML `<table id="items-table">`.

### Backend Adjustments (`main.py`)
Both `/orders/new` and `/orders/<id>/edit` will be updated to:
- Receive form data as arrays, e.g. `request.form.getlist('product_id[]')`, `request.form.getlist('quantity[]')`.
- Loop through the arrays. For each index, instantiate an `OrderItem` tied to the primary `Order.id`.
- The `Order.total_amount` must be the sum of all `OrderItem.subtotal` elements processed in the loop.

### Frontend Enhancements (`app/templates/orders/`)
- Remove the static "Material / Piezas / Medidas" inputs layout.
- Introduce a `<table class="modern-table">` where the table header has columns for Producto, Cantidad, Ancho, Alto, y Acciones (botón eliminar).
- Introduce a button `<button type="button" id="add-item-btn"><i class="fa fa-plus"></i> Añadir Producto</button>`.
- Use Vanilla JS to:
  1. Clone a template row whenever the "Add Item" button is clicked.
  2. Map the `<select>` of Products, `<input type="number">` of Quantity, Width, and Height with the name array syntax (`name="product_id[]"`).
  3. Include a "Trash" icon per row to delete that specific row before form submission.
- Ensure the backend receives correctly structured lists for all added rows.

## Minimum Price Implementation
- **Context**: Materials sold by square meter or linear meter often have a minimum charge (e.g., "The minimum we sell for a canvas is $100", even if the math yields $15).
- **Approach**: 
  1.  **Product Model**: Add an optional `min_price` (numeric) field to the Product model.
  2.  **Order Calculation (Backend)**: In `/orders/new` and `/orders/<id>/edit`, during the subtotal calculation for dynamic pricing elements (`m2` or `metro lineal`), after calculating `area * base_price` for a single piece, we check if it is less than `min_price`. If so, the single piece price becomes `min_price`. Then we multiply by `qty` (e.g. 2 tiny canvases = 2 * $100 = $200).
  3.  **UI Updates**: 
      - Products Form: Add a new input field `min_price`.
      - Orders Form: No visual changes strictly needed, though we should make sure the frontend JS also respects this minimum floor when calculating dynamically.

## Discount Implementation
- **Schema**: Add `min_qty_discount` (int) and `discount_percentage` (numeric) to `Product`. Let `Order` have `subtotal_amount` and `discount_amount`. Let `OrderItem` have `discount_applied`.
- **Products**: UI allows setting these discount thresholds. Backend passes them correctly.
- **Orders**: UI adds a global discount input field (amount, not percentage). Backend automatically calculates if any item met the threshold to get the discount on that item. Subtotal is the sum before global discounts. Total amount takes global discount into account.

## Verification Plan
### Automated Tests
- Run `flask shell` to create the database tables (`db.create_all()`).
- Create an initial `Admin` user to verify it hashes the password correctly.
- Test logging in from the web interface.
### Manual Verification
- Ensure the user gets redirected properly based on successful/failed authentication.
- Read from the database via PgAdmin or CLI to confirm all tables and foreign key constraints are created properly.
