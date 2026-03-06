import os
import json
import secrets
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Data File Paths
USERS_FILE = 'users.json'
CROPS_FILE = 'crops.json'
ORDERS_FILE = 'orders.json'

def load_data(file_path):
    if not os.path.exists(file_path):
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump([], f)
        return []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return []

def save_data(file_path, data):
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# MSP Reference Data
MSP_DATA = {
    'rice': 21.83,
    'wheat': 22.75,
    'maize': 20.90,
    'ragi': 38.46,
    'bajra': 25.00,
    'tur': 70.00,
    'moong': 85.58,
    'urad': 69.50,
    'groundnut': 63.77,
    'sunflower': 67.60,
    'soyabean': 46.00,
    'cotton': 66.20
}

# English and Tamil Translations
TRANSLATIONS = {
    'en': {
        'home': 'Home',
        'login': 'Login',
        'register': 'Register',
        'settings': 'Settings',
        'logout': 'Logout',
        'welcome': 'CropSync connects farmers directly with buyers to ensure fair pricing and transparency.',
        'get_started': 'Get Started',
        'farmer_login': 'Farmer Login',
        'buyer_login': 'Buyer Login',
        'guest_login': 'Guest Login',
        'tagline': 'CropSync',
        'tagline_sub': 'A Transparent Farmer–Buyer Digital Marketplace.',
        'footer': 'Simple. Fair. Professional.',
        'name': 'Full Name',
        'email': 'Email Address',
        'password': 'Password',
        'role': 'Role',
        'farmer': 'Farmer',
        'buyer': 'Buyer',
        'create_account': 'Create Account',
        'already_account': 'Already have an account?',
        'no_account': "Don't have an account?",
        'login_here': 'Login here',
        'register_here': 'Register here',
        'welcome_back': 'Welcome Back',
        'farmer_dashboard': 'Farmer Dashboard',
        'buyer_dashboard': 'Buyer Dashboard',
        'total_earnings': 'Total Earnings',
        'active_listings': 'Active Listings',
        'list_new_crop': 'List New Crop',
        'msp_reference': 'MSP Reference',
        'crop_name': 'Crop Name',
        'quantity': 'Quantity',
        'price_per_kg': 'Price per kg',
        'location': 'Location',
        'add_new_listing': 'Add New Listing',
        'my_crop_listings': 'My Crop Listings',
        'action': 'Action',
        'delete': 'Delete',
        'search_marketplace': 'Search Marketplace',
        'search': 'Search',
        'clear': 'Clear',
        'available_crops': 'Available Crops',
        'price': 'Price',
        'stock': 'Stock',
        'order': 'Order',
        'buy': 'Buy',
        'my_orders': 'My Orders',
        'status': 'Status',
        'profile_settings': 'Profile Settings',
        'update_profile': 'Update Profile',
        'password_info': 'Leave blank to keep current password',
        'save_changes': 'Save Changes',
        'language': 'Language',
        'english': 'English',
        'tamil': 'Tamil',
        'project_overview': 'Project Overview',
        'problem_statement': 'Problem Statement',
        'problem_desc': 'Agriculture supports nearly 45% of India’s workforce, yet many small and marginal farmers struggle to receive fair prices for their crops due to dependence on intermediaries and lack of direct buyer access. Limited transparency in agricultural trade reduces their bargaining power and affects income stability.',
        'our_objective': 'Our Objective',
        'obj_1': 'Provide direct farmer-to-buyer connectivity',
        'obj_2': 'Ensure fair crop pricing using MSP validation',
        'obj_3': 'Increase farmer income and transparency',
        'obj_4': 'Promote digital inclusion in agriculture',
        'our_solution': 'Our Solution – CropSync',
        'sol_desc': 'CropSync is a digital marketplace where farmers can list their crops and buyers can search and purchase directly from them. The platform improves transparency, promotes fair pricing, and helps reduce dependency on middlemen.',
        'sol_f_title': 'Farmer Dashboard',
        'sol_f1': 'List available crops',
        'sol_f2': 'View MSP reference price',
        'sol_f3': 'Manage orders',
        'sol_f4': 'Track earnings',
        'sol_b_title': 'Buyer Dashboard',
        'sol_b1': 'Search crops by name and location',
        'sol_b2': 'Compare farmer price with MSP',
        'sol_b3': 'Place secure orders',
        'fair_pricing': 'Fair Pricing Mechanism',
        'pricing_desc': 'The system integrates MSP (Minimum Support Price) reference values to prevent underpricing, protect farmer income, and promote transparent transactions.',
        'pricing_gov': 'MSP values are based on guidelines issued by the Government of India through the Commission for Agricultural Costs and Prices.',
        'expected_impact': 'Impact Section',
        'impact_desc': 'CropSync helps improve farmer income, reduces dependency on middlemen, and promotes a transparent digital agricultural marketplace.',
        'impact_1': 'Improved farmer income',
        'impact_2': 'Reduced dependency on middlemen',
        'impact_3': 'Transparent digital marketplace',
        'impact_4': 'Direct coordination',
        'tech_used': 'Technology Used',
        'tech_1': 'Python Flask',
        'tech_2': 'JSON Database Storage',
        'tech_3': 'HTML5 & CSS3 Responsive UI',
        'tech_4': 'Gunicorn & Render Deployment',
        'short_about': 'About CropSync',
        'short_desc': 'CropSync is a digital marketplace designed to eliminate middlemen and ensure fair crop pricing. By integrating MSP-based validation, the platform protects farmers from underpayment while providing buyers with transparent and direct access to agricultural produce.',
        'key_features': 'Key Features',
        'feature_msp': 'MSP Price Protection',
        'feature_direct': 'Direct Market Access',
        'feature_secure': 'Secure & Transparent',
        'phone': 'Phone Number',
        'contact_details': 'Contact Details',
        'buyer_name': 'Buyer Name',
        'buyer_contact': 'Buyer Contact',
        'sold_items': 'Sold Items',
        'farmer_contact': 'Farmer Contact',
        'no_phone': 'No phone provided',
        'how_it_works': 'How It Works',
        'how_1': 'Farmers list their crops.',
        'how_2': 'Buyers browse and search for crops.',
        'how_3': 'Buyers connect directly with farmers for transparent trade.',
        'feature_dash': 'Farmer Dashboard – Farmers can list and manage their crop listings.',
        'feature_market': 'Buyer Marketplace – Buyers can browse available crops easily.',
        'feature_price': 'Transparent Pricing – Better visibility of crop prices.',
        'feature_connect': 'Direct Farmer–Buyer Connection – Reduces intermediaries.',
    }
}

@app.context_processor
def inject_translations():
    def get_text(key):
        return TRANSLATIONS['en'].get(key, key)
    return dict(get_text=get_text)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')
        phone = request.form.get('phone')

        if not all([name, email, password, role, phone]):
            flash('All fields are required', 'error')
            return redirect(url_for('register'))

        users = load_data(USERS_FILE)
        if any(u['email'] == email for u in users):
            flash('Email already registered', 'error')
            return redirect(url_for('register'))

        new_user = {
            'id': secrets.token_hex(8),
            'name': name,
            'email': email,
            'password': password,
            'role': role,
            'phone': phone
        }
        users.append(new_user)
        save_data(USERS_FILE, users)
        flash('Registration successful!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        users = load_data(USERS_FILE)
        user = next((u for u in users if u['email'] == email and u['password'] == password), None)
        if user:
            session['user'] = user
            return redirect(url_for('farmer_dashboard' if user['role'] == 'farmer' else 'buyer_dashboard'))
        flash('Invalid credentials', 'error')
    return render_template('login.html')

@app.route('/farmer_dashboard', methods=['GET', 'POST'])
def farmer_dashboard():
    if 'user' not in session or session['user']['role'] != 'farmer':
        return redirect(url_for('login'))

    crops = load_data(CROPS_FILE)
    if request.method == 'POST':
        crop_name = request.form.get('crop_name', '').lower()
        quantity = request.form.get('quantity')
        price = request.form.get('price_per_kg')
        location = request.form.get('location')

        if not all([crop_name, quantity, price, location]):
            flash('All fields are required', 'error')
            return redirect(url_for('farmer_dashboard'))

        try:
            qty = float(quantity)
            prc = float(price)
            msp = MSP_DATA.get(crop_name, 0)
            if prc < msp:
                flash(f'Price below MSP (₹{msp})!', 'error')
            else:
                new_crop = {
                    'id': secrets.token_hex(8),
                    'farmer_id': session['user']['id'],
                    'crop_name': crop_name,
                    'quantity': qty,
                    'price_per_kg': prc,
                    'location': location
                }
                crops.append(new_crop)
                save_data(CROPS_FILE, crops)
                flash('Listing added!', 'success')
        except ValueError:
            flash('Invalid numbers!', 'error')

    user_crops = [c for c in crops if c['farmer_id'] == session['user']['id']]
    orders = load_data(ORDERS_FILE)
    users = load_data(USERS_FILE)
    buyer_map = {u['id']: {'name': u['name'], 'phone': u.get('phone', 'N/A')} for u in users}
    
    sold_orders = []
    for o in orders:
        if o['farmer_id'] == session['user']['id']:
            o_copy = o.copy()
            buyer_info = buyer_map.get(o['buyer_id'], {'name': 'Unknown', 'phone': 'N/A'})
            o_copy['buyer_name'] = buyer_info['name']
            o_copy['buyer_phone'] = buyer_info['phone']
            sold_orders.append(o_copy)

    earnings = sum(o['total_price'] for o in sold_orders)
    
    return render_template('farmer_dashboard.html', crops=user_crops, earnings=earnings, msp_data=MSP_DATA, sold_orders=sold_orders)

@app.route('/delete_crop/<crop_id>')
def delete_crop(crop_id):
    if 'user' not in session or session['user']['role'] != 'farmer':
        return redirect(url_for('login'))
    crops = load_data(CROPS_FILE)
    crops = [c for c in crops if not (c['id'] == crop_id and c['farmer_id'] == session['user']['id'])]
    save_data(CROPS_FILE, crops)
    flash('Listing deleted', 'success')
    return redirect(url_for('farmer_dashboard'))

@app.route('/buyer_dashboard')
def buyer_dashboard():
    if 'user' not in session or session['user']['role'] != 'buyer':
        return redirect(url_for('login'))

    crops = load_data(CROPS_FILE)
    users = load_data(USERS_FILE)
    
    search = request.args.get('search', '').lower()
    location = request.args.get('location', '').lower()

    filtered_crops = []
    farmer_map = {u['id']: {'name': u['name'], 'phone': u.get('phone', 'N/A')} for u in users}

    for c in crops:
        if search and search not in c['crop_name'].lower(): continue
        if location and location not in c['location'].lower(): continue
        c_copy = c.copy()
        farmer_info = farmer_map.get(c['farmer_id'], {'name': 'Farmer', 'phone': 'N/A'})
        c_copy['farmer_name'] = farmer_info['name']
        c_copy['farmer_phone'] = farmer_info['phone']
        c_copy['msp_value'] = MSP_DATA.get(c['crop_name'].lower(), 0)
        filtered_crops.append(c_copy)

    orders = load_data(ORDERS_FILE)
    user_orders = []
    for o in orders:
        if o['buyer_id'] == session['user']['id']:
            o_copy = o.copy()
            farmer_info = farmer_map.get(o['farmer_id'], {'name': 'Farmer', 'phone': 'N/A'})
            o_copy['farmer_name'] = farmer_info['name']
            o_copy['farmer_phone'] = farmer_info['phone']
            user_orders.append(o_copy)

    return render_template('buyer_dashboard.html', crops=filtered_crops, orders=user_orders)

@app.route('/place_order', methods=['POST'])
def place_order():
    if 'user' not in session or session['user']['role'] != 'buyer':
        return redirect(url_for('login'))

    crop_id = request.form.get('crop_id')
    qty_buy = request.form.get('quantity')
    
    crops = load_data(CROPS_FILE)
    crop = next((c for c in crops if c['id'] == crop_id), None)
    
    if crop and qty_buy:
        try:
            q = float(qty_buy)
            if q <= crop['quantity']:
                orders = load_data(ORDERS_FILE)
                new_order = {
                    'id': secrets.token_hex(8),
                    'buyer_id': session['user']['id'],
                    'farmer_id': crop['farmer_id'],
                    'crop_id': crop['id'],
                    'crop_name': crop['crop_name'],
                    'quantity': q,
                    'total_price': q * crop['price_per_kg'],
                    'status': 'completed'
                }
                orders.append(new_order)
                save_data(ORDERS_FILE, orders)
                
                crop['quantity'] -= q
                if crop['quantity'] <= 0:
                    crops = [c for c in crops if c['id'] != crop_id]
                save_data(CROPS_FILE, crops)
                flash('Order placed!', 'success')
            else:
                flash('Not enough stock!', 'error')
        except ValueError:
            flash('Invalid quantity!', 'error')
            
    return redirect(url_for('buyer_dashboard'))

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'user' not in session: return redirect(url_for('login'))
    if request.method == 'POST':
        users = load_data(USERS_FILE)
        for u in users:
            if u['id'] == session['user']['id']:
                u['name'] = request.form.get('name')
                pw = request.form.get('password')
                if pw: u['password'] = pw
                session['user'] = u
                save_data(USERS_FILE, users)
                flash('Profile updated!', 'success')
                break
    return render_template('settings.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True)
