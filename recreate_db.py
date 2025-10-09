from models import db
from create_marketplace_db import app

with app.app_context():
    db.drop_all()
    db.create_all()
