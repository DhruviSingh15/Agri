from flask import Flask
from models import db, Listing, Offer, User

app = Flask(__name__)
app.config['SECRET_KEY'] = 'replace_this_with_a_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
db.init_app(app)

with app.app_context():
    db.create_all()
print("Marketplace tables created.")
