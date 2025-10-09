from app import app, db, User
from werkzeug.security import generate_password_hash

with app.app_context():
    # Create admin user
    admin_username = 'admin'
    admin_password = 'admin123'
    admin_email = 'admin@example.com'
    
    # Check if admin already exists
    existing_admin = User.query.filter_by(username=admin_username).first()
    if existing_admin:
        print(f"Admin user '{admin_username}' already exists.")
    else:
        # Create new admin user
        admin = User(
            username=admin_username,
            email=admin_email,
            password=generate_password_hash(admin_password)
        )
        db.session.add(admin)
        db.session.commit()
        print(f"Admin user '{admin_username}' created successfully.")
