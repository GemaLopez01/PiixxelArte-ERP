from main import app
from app.extensions import db
from app.models.user import User

with app.app_context():
    # Verificar si el usuario admin ya existe
    admin = User.query.filter_by(email='admin@piixxelarte.com').first()
    if not admin:
        admin = User(name='Admin', email='admin@piixxelarte.com', role='Administrador')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print("Usuario admin creado exitosamente.")
    else:
        print("El usuario admin ya existe.")
