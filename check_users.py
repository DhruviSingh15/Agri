from app import app, db, User

with app.app_context():
    # Get all users
    users = User.query.all()
    print("Current users:")
    for user in users:
        print(f"Username: {user.username}, Email: {user.email}")
