from flask import Flask, render_template, request, redirect, url_for, flash
import requests
from flask import Flask, render_template, request, redirect, url_for, flash
import requests
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
# Set default method to avoid scrypt issues
DEFAULT_METHOD = 'pbkdf2:sha256'
from models import db, User, Listing, Offer

app = Flask(__name__)
app.config['SECRET_KEY'] = 'replace_this_with_a_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    api_key = '1ee7b46b8010dd48edcea0276bf14d22'
    city = request.args.get('city') or 'Delhi'
    # Crop advisory logic
    seasons = ['Rabi', 'Kharif', 'Zaid']
    soils = ['Alluvial', 'Black', 'Red', 'Laterite', 'Sandy', 'Clay']
    selected_season = request.form.get('season') or 'Rabi'
    selected_soil = request.form.get('soil') or 'Alluvial'
    # Crop recommendations (simple static mapping)
    crop_advisory = {
        ('Rabi', 'Alluvial'): {
            'crops': ['Wheat', 'Barley', 'Mustard'],
            'tips': 'Ensure timely sowing and use certified seeds.'
        },
        ('Kharif', 'Alluvial'): {
            'crops': ['Rice', 'Maize', 'Sugarcane'],
            'tips': 'Maintain proper field leveling for rice.'
        },
        ('Zaid', 'Alluvial'): {
            'crops': ['Watermelon', 'Cucumber', 'Moong'],
            'tips': 'Irrigate frequently during hot months.'
        },
        ('Rabi', 'Black'): {
            'crops': ['Wheat', 'Gram', 'Linseed'],
            'tips': 'Use organic manure to enrich soil.'
        },
        ('Kharif', 'Black'): {
            'crops': ['Cotton', 'Soybean', 'Jowar'],
            'tips': 'Monitor for pest attacks in cotton.'
        },
        ('Zaid', 'Black'): {
            'crops': ['Sunflower', 'Sesame'],
            'tips': 'Apply fertilizer after soil testing.'
        },
        # ... (add more combinations as needed)
    }
    advisory = crop_advisory.get((selected_season, selected_soil), {
        'crops': ['Wheat', 'Rice', 'Maize'],
        'tips': 'Consult local experts for best results.'
    })
    # Weather and forecast logic
    weather = None
    forecast = []
    try:
        # Current weather
        url = f'https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric'
        resp = requests.get(url)
        if resp.status_code == 200:
            data = resp.json()
            weather = {
                'city': city,
                'temp': data['main']['temp'],
                'humidity': data['main']['humidity'],
                'desc': data['weather'][0]['description'].title(),
                'icon': data['weather'][0]['icon'],
                'wind': data['wind']['speed']
            }
        else:
            flash('Could not get weather for that city.', 'danger')
        
        # 3-day forecast
        url2 = f'https://api.openweathermap.org/data/2.5/forecast?q={city}&appid={api_key}&units=metric'
        resp2 = requests.get(url2)
        if resp2.status_code == 200:
            data2 = resp2.json()
            # Get forecast for next 3 days at 12:00
            for item in data2['list']:
                if '12:00:00' in item['dt_txt'] and len(forecast) < 3:
                    forecast.append({
                        'date': item['dt_txt'].split(' ')[0],
                        'temp': item['main']['temp'],
                        'desc': item['weather'][0]['description'].title(),
                        'icon': item['weather'][0]['icon'],
                        'humidity': item['main']['humidity'],
                        'wind': item['wind']['speed']
                    })
    except Exception:
        flash('Error fetching weather.', 'danger')
    return render_template('dashboard.html', weather=weather, forecast=forecast, city=city, seasons=seasons, soils=soils, selected_season=selected_season, selected_soil=selected_soil, advisory=advisory)

@app.route('/mandi-prices')
@login_required
def mandi_prices():
    return render_template('mandi-prices.html')

@app.route('/schemes')
@login_required
def schemes():
    return render_template('schemes.html')

from models import Listing, Offer
import random

@app.route('/marketplace', methods=['GET', 'POST'])
@login_required
def marketplace():
    if request.method == 'POST':
        # Handle listing creation
        if 'crop' in request.form:
            crop = request.form.get('crop')
            quantity = request.form.get('quantity')
            price = request.form.get('price')
            
            if not crop or not quantity or not price:
                flash('Please fill in all fields', 'danger')
                return redirect(url_for('marketplace'))
            
            try:
                quantity = float(quantity)
                price = float(price)
            except ValueError:
                flash('Please enter valid numbers for quantity and price', 'danger')
                return redirect(url_for('marketplace'))
            
            listing = Listing(
                user_id=current_user.id,
                crop=crop,
                quantity=quantity,
                price=price,
                status='Available'
            )
            db.session.add(listing)
            db.session.commit()
            flash('Crop listed successfully!', 'success')
            return redirect(url_for('marketplace'))
        
        # Handle offer submission
        if 'offer_price' in request.form:
            offer_price = request.form.get('offer_price')
            listing_id = request.form.get('offer_listing_id')
            
            if not offer_price or not listing_id:
                flash('Invalid offer', 'danger')
                return redirect(url_for('marketplace'))
            
            try:
                offer_price = float(offer_price)
                listing_id = int(listing_id)
            except ValueError:
                flash('Invalid offer amount', 'danger')
                return redirect(url_for('marketplace'))
            
            listing = Listing.query.get(listing_id)
            if not listing:
                flash('Listing not found', 'danger')
                return redirect(url_for('marketplace'))
            
            offer = Offer(
                user_id=current_user.id,
                listing_id=listing_id,
                offer_price=offer_price
            )
            db.session.add(offer)
            db.session.commit()
            flash('Offer submitted successfully!', 'success')
            return redirect(url_for('marketplace'))
    
    # Show all listings with offers
    listings = Listing.query.order_by(Listing.created_at.desc()).all()
    offers_by_listing = {l.id: Offer.query.filter_by(listing_id=l.id).all() for l in listings}
    users = {u.id: u for u in User.query.all()}
    # Demo trend
    trends = ['Stable', 'Rising', 'Falling']
    return render_template('marketplace.html', listings=listings, offers_by_listing=offers_by_listing, users=users, trends=trends)

@app.route('/marketplace/cancel-offer', methods=['POST'])
@login_required
def cancel_offer():
    offer_id = request.form.get('offer_id')
    if not offer_id:
        flash('Invalid offer', 'danger')
        return redirect(url_for('marketplace'))
    
    try:
        offer_id = int(offer_id)
    except ValueError:
        flash('Invalid offer ID', 'danger')
        return redirect(url_for('marketplace'))
    
    offer = Offer.query.get(offer_id)
    if not offer:
        flash('Offer not found', 'danger')
        return redirect(url_for('marketplace'))
    
    if offer.user_id != current_user.id:
        flash('You can only cancel your own offers', 'danger')
        return redirect(url_for('marketplace'))
    
    if offer.status != 'pending':
        flash('This offer has already been processed', 'danger')
        return redirect(url_for('marketplace'))
    
    db.session.delete(offer)
    db.session.commit()
    flash('Offer cancelled successfully!', 'success')
    return redirect(url_for('marketplace'))

@app.route('/marketplace/accept-offer', methods=['POST'])
@login_required
def accept_offer():
    offer_id = request.form.get('offer_id')
    if not offer_id:
        flash('Invalid offer', 'danger')
        return redirect(url_for('marketplace'))
    
    try:
        offer_id = int(offer_id)
    except ValueError:
        flash('Invalid offer ID', 'danger')
        return redirect(url_for('marketplace'))
    
    offer = Offer.query.get(offer_id)
    if not offer:
        flash('Offer not found', 'danger')
        return redirect(url_for('marketplace'))
    
    if offer.listing.user_id != current_user.id:
        flash('You can only accept offers on your own listings', 'danger')
        return redirect(url_for('marketplace'))
    
    if offer.status != 'pending':
        flash('This offer has already been processed', 'danger')
        return redirect(url_for('marketplace'))
    
    # Update offer status
    offer.status = 'accepted'
    db.session.commit()
    
    # Update listing status
    offer.listing.status = 'Sold'
    db.session.commit()
    
    flash('Offer accepted successfully!', 'success')
    return redirect(url_for('marketplace'))

@app.route('/marketplace/reject-offer', methods=['POST'])
@login_required
def reject_offer():
    offer_id = request.form.get('offer_id')
    if not offer_id:
        flash('Invalid offer', 'danger')
        return redirect(url_for('marketplace'))
    
    try:
        offer_id = int(offer_id)
    except ValueError:
        flash('Invalid offer ID', 'danger')
        return redirect(url_for('marketplace'))
    
    offer = Offer.query.get(offer_id)
    if not offer:
        flash('Offer not found', 'danger')
        return redirect(url_for('marketplace'))
    
    if offer.listing.user_id != current_user.id:
        flash('You can only reject offers on your own listings', 'danger')
        return redirect(url_for('marketplace'))
    
    if offer.status != 'pending':
        flash('This offer has already been processed', 'danger')
        return redirect(url_for('marketplace'))
    
    offer.status = 'rejected'
    db.session.commit()
    flash('Offer rejected successfully!', 'success')
    return redirect(url_for('marketplace'))


# In-memory announcement for demo
announcement_data = {'text': 'Important: System maintenance scheduled on 15th May, 10PM-12AM.'}

# Add a demo offer if none exist (for demo purposes only)
@app.before_request
def add_demo_offer():
    # Only run for GET to '/' or '/admin' to avoid interfering with forms
    if request.method == 'GET' and request.path in ['/', '/admin']:
        # Ensure there is at least one user
        user = User.query.filter_by(username='hari').first()
        if not user:
            user = User(username='hari', email='hari@admin.com', password=generate_password_hash('admin', method='pbkdf2:sha256'))
            db.session.add(user)
            db.session.commit()
        # Ensure there is at least one listing
        listing = Listing.query.first()
        if not listing:
            listing = Listing(user_id=user.id, crop='Wheat', quantity=100, price=2500)
            db.session.add(listing)
            db.session.commit()
        # Ensure there is at least one offer
        offer = Offer.query.first()
        if not offer:
            offer = Offer(listing_id=listing.id, user_id=user.id, offer_price=2400)
            db.session.add(offer)
            db.session.commit()
        # Ensure announcement has a default
        if not announcement_data.get('text'):
            announcement_data['text'] = 'Important: System maintenance scheduled on 15th May, 10PM-12AM.'

@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin():
    if current_user.username.lower() != 'hari':
        flash('Access denied: Only admin user Hari can access this page.', 'danger')
        return redirect(url_for('dashboard'))
    # Remove user
    if request.method == 'POST' and request.form.get('remove_user'):
        user_id = int(request.form.get('remove_user'))
        user = User.query.get(user_id)
        if user and user.username.lower() != 'hari':
            db.session.delete(user)
            db.session.commit()
            flash('User removed.', 'success')
        else:
            flash('Cannot remove admin user.', 'danger')
        return redirect(url_for('admin'))
    # Remove listing
    if request.method == 'POST' and request.form.get('remove_listing'):
        listing_id = int(request.form.get('remove_listing'))
        listing = Listing.query.get(listing_id)
        if listing:
            db.session.delete(listing)
            db.session.commit()
            flash('Listing removed.', 'success')
        return redirect(url_for('admin'))
    # Remove offer
    if request.method == 'POST' and request.form.get('remove_offer'):
        offer_id = int(request.form.get('remove_offer'))
        offer = Offer.query.get(offer_id)
        if offer:
            db.session.delete(offer)
            db.session.commit()
            flash('Offer removed.', 'success')
        return redirect(url_for('admin'))
    # Edit announcement
    if request.method == 'POST' and request.form.get('announcement') is not None:
        announcement_data['text'] = request.form.get('announcement').strip()
        flash('Announcement updated.', 'success')
        return redirect(url_for('admin'))
    users = User.query.order_by(User.username).all()
    listings = Listing.query.order_by(Listing.created_at.desc()).all()
    offers = Offer.query.order_by(Offer.created_at.desc()).all()
    # Eager load relationships for template
    for l in listings:
        _ = l.user
    for o in offers:
        _ = o.user
        _ = o.listing
        _ = o.listing.user
    return render_template('admin.html', users=users, listings=listings, offers=offers, announcement=announcement_data['text'])

@app.route('/weather', methods=['GET'])
@login_required
def weather():
    api_key = '1ee7b46b8010dd48edcea0276bf14d22'
    city = request.args.get('city') or 'Delhi'
    weather = None
    forecast = []
    try:
        # Current weather
        url = f'https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric'
        resp = requests.get(url)
        if resp.status_code == 200:
            data = resp.json()
            weather = {
                'city': city,
                'temp': data['main']['temp'],
                'humidity': data['main']['humidity'],
                'desc': data['weather'][0]['description'].title(),
                'icon': data['weather'][0]['icon'],
                'wind': data['wind']['speed']
            }
        else:
            flash('Could not get weather for that city.', 'danger')
        # 3-day forecast
        url2 = f'https://api.openweathermap.org/data/2.5/forecast?q={city}&appid={api_key}&units=metric'
        resp2 = requests.get(url2)
        if resp2.status_code == 200:
            data2 = resp2.json()
            # Get forecast for next 3 days at 12:00
            for item in data2['list']:
                if '12:00:00' in item['dt_txt'] and len(forecast) < 3:
                    forecast.append({
                        'date': item['dt_txt'].split(' ')[0],
                        'temp': item['main']['temp'],
                        'desc': item['weather'][0]['description'].title(),
                        'icon': item['weather'][0]['icon']
                    })
    except Exception:
        flash('Error fetching weather.', 'danger')
    return render_template('weather.html', weather=weather, city=city, forecast=forecast)

@app.route('/prices', methods=['GET', 'POST'])
@login_required
def prices():
    import requests
    from flask import jsonify
    from datetime import datetime
    today = datetime.today().strftime('%Y-%m-%d')
    # Try to fetch mandi prices from API, else fallback to demo data
    try:
        url = 'https://data.gov.in/node/328681/datastore/export/json'
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            records = resp.json()
            # Parse and filter for major crops and markets (customize as needed)
            mandi_data = []
            for r in records:
                crop = r.get('commodity') or r.get('Crop') or r.get('crop')
                location = r.get('market') or r.get('Location') or r.get('location')
                price = r.get('modal_price') or r.get('Price') or r.get('price')
                date = r.get('arrival_date') or r.get('Date') or r.get('date')
                if crop and location and price and date:
                    mandi_data.append({
                        'crop': crop,
                        'location': location,
                        'price': price,
                        'date': date
                    })
            if not mandi_data:
                raise Exception('No mandi data parsed')
        else:
            raise Exception('API error')
    except Exception:
        # Fallback static/demo data (same as /api/mandi-prices)
        mandi_data = [
            {"crop": "Wheat", "location": "Delhi", "price": "2,300", "date": today},
            {"crop": "Rice", "location": "Kolkata", "price": "2,800", "date": today},
            {"crop": "Maize", "location": "Pune", "price": "1,900", "date": today},
            {"crop": "Barley", "location": "Jaipur", "price": "1,700", "date": today},
            {"crop": "Mustard", "location": "Kanpur", "price": "5,050", "date": today},
            {"crop": "Cotton", "location": "Nagpur", "price": "6,000", "date": today},
            {"crop": "Soybean", "location": "Indore", "price": "4,300", "date": today},
            {"crop": "Gram", "location": "Bhopal", "price": "4,800", "date": today},
            {"crop": "Sugarcane", "location": "Meerut", "price": "320", "date": today},
            {"crop": "Onion", "location": "Nashik", "price": "1,400", "date": today},
            {"crop": "Tomato", "location": "Bangalore", "price": "1,800", "date": today},
            {"crop": "Apple", "location": "Shimla", "price": "8,000", "date": today},
            {"crop": "Banana", "location": "Trichy", "price": "1,100", "date": today},
            {"crop": "Tea", "location": "Darjeeling", "price": "20,000", "date": today},
            {"crop": "Rubber", "location": "Kottayam", "price": "15,000", "date": today}
        ]
    # Collect crops and locations for filter dropdowns
    crops = sorted(list(set([row['crop'] for row in mandi_data])))
    locations = sorted(list(set([row['location'] for row in mandi_data])))
    crop = request.form.get('crop') if request.method == 'POST' else ''
    location = request.form.get('location') if request.method == 'POST' else ''
    filtered_prices = [row for row in mandi_data if (not crop or row['crop'] == crop) and (not location or row['location'] == location) and row['date'] == today]
    # For chart: prices for last 7 days for selected crop/location (simulate if no API)
    chart_labels = []
    chart_data = []
    if crop and location:
        trend = [row for row in mandi_data if row['crop'] == crop and row['location'] == location]
        trend = sorted(trend, key=lambda x: x['date'])[-7:]
        chart_labels = [row['date'] for row in trend]
        chart_data = [int(row['price'].replace(',', '')) if isinstance(row['price'], str) else row['price'] for row in trend]
    return render_template('prices.html', crops=crops, locations=locations, filtered_prices=filtered_prices, selected_crop=crop, selected_location=location, chart_labels=chart_labels, chart_data=chart_data)


# Simple in-memory storage for demo; in production, use a database
user_queries = []
# Each query dict can have an optional 'reply' field

@app.route('/helpdesk', methods=['GET', 'POST'])
@login_required
def helpdesk():
    global user_queries
    is_admin = current_user.username == 'Hari'
    # Handle reply if admin posts
    # Handle admin delete
    if is_admin and request.method == 'POST' and request.form.get('delete_query'):
        idx = int(request.form.get('delete_query'))
        del user_queries[idx]
        flash('Query deleted.', 'success')
    # Handle admin reply
    elif is_admin and request.method == 'POST' and request.form.get('reply_to'):
        idx = int(request.form.get('reply_to'))
        reply = request.form.get('reply_text', '').strip()
        if reply:
            user_queries[idx]['reply'] = reply
            user_queries[idx]['notified'] = False  # Mark as not notified
            flash('Reply posted.', 'success')
        else:
            flash('Reply cannot be empty.', 'danger')
    # Handle normal query post
    elif request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        subject = request.form.get('subject')
        message = request.form.get('message')
        if not (name and email and subject and message):
            flash('All fields are required.', 'danger')
        else:
            user_queries.append({
                'user': current_user.username,
                'name': name,
                'email': email,
                'subject': subject,
                'message': message
            })
            flash('Your query has been submitted. We will contact you soon!', 'success')
    # Notify users of new replies to their queries
    if not is_admin:
        for q in user_queries:
            if q.get('user') == current_user.username and q.get('reply') and not q.get('notified', False):
                flash('New reply to your query: "{}"'.format(q['subject']), 'info')
                q['notified'] = True
    prev_queries = user_queries
    return render_template('helpdesk.html', prev_queries=prev_queries, is_admin=is_admin)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user:
            # Try both methods without specifying method parameter
            try:
                # First try the hash as is
                if check_password_hash(user.password, password):
                    login_user(user)
                    flash('Logged in successfully!', 'success')
                    return redirect(url_for('dashboard'))
            except ValueError:
                # If first method fails, try to recreate the hash
                try:
                    # Create a new hash with pbkdf2:sha256
                    new_hash = generate_password_hash(password, method='pbkdf2:sha256')
                    if check_password_hash(new_hash, password):
                        # Update the user's password hash
                        user.password = new_hash
                        db.session.commit()
                        login_user(user)
                        flash('Logged in successfully!', 'success')
                        return redirect(url_for('dashboard'))
                except Exception as e:
                    print(f"Error updating password hash: {e}")
            flash('Invalid username or password', 'danger')
        else:
            flash('Invalid username or password', 'danger')
        return render_template('login.html')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
        elif User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
        else:
            hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')
            new_user = User(username=username, email=email, password=hashed_pw)
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# Simple in-memory forum storage
forum_threads = []  # Each thread: {'user', 'title', 'message', 'replies': [{'user', 'message'}]}

@app.route('/forum', methods=['GET', 'POST'])
@login_required
def forum():
    global forum_threads
    is_admin = current_user.username == 'Hari'
    # Handle new thread
    if request.method == 'POST' and request.form.get('new_thread'):
        title = request.form.get('title', '').strip()
        message = request.form.get('message', '').strip()
        if title and message:
            forum_threads.append({'user': current_user.username, 'title': title, 'message': message, 'replies': []})
            flash('Thread posted!', 'success')
        else:
            flash('Title and message required.', 'danger')
    # Handle reply
    elif request.method == 'POST' and request.form.get('reply_to'):
        idx = int(request.form.get('reply_to'))
        reply_msg = request.form.get('reply_message', '').strip()
        if reply_msg:
            forum_threads[idx]['replies'].append({'user': current_user.username, 'message': reply_msg})
            flash('Reply posted!', 'success')
        else:
            flash('Reply cannot be empty.', 'danger')
    # Handle admin delete thread
    elif is_admin and request.method == 'POST' and request.form.get('delete_thread'):
        idx = int(request.form.get('delete_thread'))
        del forum_threads[idx]
        flash('Thread deleted.', 'success')
    # Handle admin delete reply
    elif is_admin and request.method == 'POST' and request.form.get('delete_reply'):
        idx = int(request.form.get('thread_idx'))
        ridx = int(request.form.get('delete_reply'))
        del forum_threads[idx]['replies'][ridx]
        flash('Reply deleted.', 'success')
    return render_template('forum.html', forum_threads=forum_threads, is_admin=is_admin)


@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

from flask import jsonify

@app.route('/api/mandi-prices')
def api_mandi_prices():
    import datetime
    try:
        # Agmarknet API endpoint (demo, no API key required for open data)
        # We'll fetch the latest data for a few crops for today
        today = datetime.datetime.now().strftime('%d-%m-%Y')
        url = f'https://data.gov.in/node/328681/datastore/export/json'
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            records = resp.json()
            # Parse and filter for a few major crops and markets
            crops_of_interest = ["Wheat", "Rice", "Maize", "Cotton", "Mustard", "Soyabean", "Chana", "Sugarcane", "Potato", "Onion", "Tomato"]
            data = []
            for row in records:
                crop = row.get("Commodity")
                market = row.get("Market")
                price = row.get("Modal Price (Rs./Quintal)") or row.get("Modal Price (Rs./Quintal)")
                date = row.get("Arrival Date")
                if crop and crop.title() in [c.title() for c in crops_of_interest]:
                    data.append({
                        "crop": crop.title(),
                        "location": market,
                        "price": price,
                        "date": date
                    })
            # Limit to 40 entries for speed
            return jsonify(data[:40])
    except Exception as e:
        print("Agmarknet fetch failed:", e)
    # Fallback to demo data
    data = [
        {"crop": "Wheat", "location": "Delhi", "price": "2,300", "date": "2025-05-13"},
        {"crop": "Wheat", "location": "Lucknow", "price": "2,250", "date": "2025-05-13"},
        {"crop": "Wheat", "location": "Chandigarh", "price": "2,400", "date": "2025-05-13"},
        {"crop": "Rice", "location": "Kolkata", "price": "2,800", "date": "2025-05-13"},
        {"crop": "Rice", "location": "Patna", "price": "2,650", "date": "2025-05-13"},
        {"crop": "Rice", "location": "Guwahati", "price": "2,700", "date": "2025-05-13"},
        {"crop": "Maize", "location": "Pune", "price": "1,900", "date": "2025-05-13"},
        {"crop": "Maize", "location": "Hyderabad", "price": "2,000", "date": "2025-05-13"},
        {"crop": "Maize", "location": "Bangalore", "price": "1,950", "date": "2025-05-13"},
        {"crop": "Cotton", "location": "Ahmedabad", "price": "6,200", "date": "2025-05-13"},
        {"crop": "Cotton", "location": "Nagpur", "price": "6,000", "date": "2025-05-13"},
        {"crop": "Cotton", "location": "Coimbatore", "price": "6,300", "date": "2025-05-13"},
        {"crop": "Mustard", "location": "Jaipur", "price": "5,100", "date": "2025-05-13"},
        {"crop": "Mustard", "location": "Kanpur", "price": "5,050", "date": "2025-05-13"},
        {"crop": "Mustard", "location": "Hisar", "price": "5,200", "date": "2025-05-13"},
        {"crop": "Soybean", "location": "Indore", "price": "4,300", "date": "2025-05-13"},
        {"crop": "Soybean", "location": "Bhopal", "price": "4,350", "date": "2025-05-13"},
        {"crop": "Soybean", "location": "Nanded", "price": "4,250", "date": "2025-05-13"},
        {"crop": "Chana", "location": "Bhopal", "price": "4,800", "date": "2025-05-13"},
        {"crop": "Chana", "location": "Raipur", "price": "4,700", "date": "2025-05-13"},
        {"crop": "Chana", "location": "Jodhpur", "price": "4,850", "date": "2025-05-13"},
        {"crop": "Sugarcane", "location": "Meerut", "price": "320", "date": "2025-05-13"},
        {"crop": "Sugarcane", "location": "Kolhapur", "price": "315", "date": "2025-05-13"},
        {"crop": "Sugarcane", "location": "Gorakhpur", "price": "325", "date": "2025-05-13"},
        {"crop": "Potato", "location": "Agra", "price": "1,200", "date": "2025-05-13"},
        {"crop": "Onion", "location": "Nashik", "price": "1,400", "date": "2025-05-13"},
        {"crop": "Tomato", "location": "Bangalore", "price": "1,800", "date": "2025-05-13"},
        {"crop": "Apple", "location": "Shimla", "price": "8,000", "date": "2025-05-13"},
        {"crop": "Banana", "location": "Trichy", "price": "1,100", "date": "2025-05-13"},
        {"crop": "Tea", "location": "Darjeeling", "price": "20,000", "date": "2025-05-13"},
        {"crop": "Rubber", "location": "Kottayam", "price": "15,000", "date": "2025-05-13"}
    ]
    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True)
