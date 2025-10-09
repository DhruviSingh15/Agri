from app import app, db, User
from werkzeug.security import generate_password_hash

with app.app_context():
    # Find the user with username 'hari'
    user = User.query.filter_by(username='hari').first()
    if user:
        # Update the password
        user.password = generate_password_hash('admin123')
        db.session.commit()
        print("Password updated successfully for user 'hari'.")
    else:
        print("User 'hari' not found.")
