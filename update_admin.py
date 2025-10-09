from app import app, db, User

with app.app_context():
    # Find the admin user
    admin = User.query.filter_by(username='admin').first()
    if admin:
        # Update the username
        admin.username = 'hari'
        db.session.commit()
        print("Admin username updated to 'hari' successfully.")
    else:
        print("Admin user not found.")
