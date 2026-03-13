from main import app
from app.extensions import db
from app.models.user import User

with app.app_context():
    # Check if admin already exists
    admin = User.query.filter_by(email='admin@piixxelarte.com').first()
    if not admin:
        admin = User(name='Admin', email='admin@piixxelarte.com', role='Administrador')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print("Admin user created successfully.")
    else:
        print("Admin user already exists.")
