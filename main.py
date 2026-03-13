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
    return f"Bienvenido, {current_user.name} (Rol: {current_user.role})"

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(debug=True)