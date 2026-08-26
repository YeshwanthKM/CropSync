import os
import json
import secrets
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

import db
import migrate_data

app = Flask(__name__)
app.secret_key = 'cropsync-demo-secret-key-stable'

# Auto-initialize database & run migration on startup
try:
    db.init_db()
    migrate_data.run_migration()
except Exception as _e:
    print("[!] Database initialization warning:", _e)

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
        'marketplace': 'Marketplace',
        'home_welcome': 'CropSync is a transparent digital marketplace that connects farmers directly with buyers. Our platform ensures fair pricing by integrating Government MSP (Minimum Support Price) data and eliminating unnecessary intermediaries.',
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
        'address': 'Address',
        'phone': 'Phone Number',
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
        'problem_desc': 'Agriculture supports nearly 45% of India’s workforce, yet many small and marginal farmers struggle to receive fair prices for their crops due to dependence on intermediaries and lack of direct buyer access.',
        'our_objective': 'Our Objective',
        'obj_1': 'Provide direct farmer-to-buyer connectivity',
        'obj_2': 'Ensure fair crop pricing using MSP validation',
        'obj_3': 'Increase farmer income and transparency',
        'obj_4': 'Promote digital inclusion in agriculture',
        'our_solution': 'Our Solution – CropSync',
        'sol_desc': 'CropSync is a digital marketplace where farmers can list their crops and buyers can search and purchase directly from them.',
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
        'pricing_desc': 'The system integrates MSP reference values to prevent underpricing and protect farmer income.',
        'pricing_gov': 'MSP values are based on guidelines issued by the Government of India.',
        'expected_impact': 'Impact Section',
        'impact_desc': 'CropSync helps improve farmer income and promotes a transparent digital agricultural marketplace.',
        'impact_1': 'Improved farmer income',
        'impact_2': 'Reduced dependency on middlemen',
        'impact_3': 'Transparent digital marketplace',
        'impact_4': 'Direct coordination',
        'tech_used': 'Technology Used',
        'tech_1': 'Python Flask',
        'tech_2': 'Supabase PostgreSQL Database',
        'tech_3': 'HTML5 & CSS3 Responsive UI',
        'tech_4': 'Vercel Serverless Deployment',
        'short_about': 'About CropSync',
        'short_desc': 'CropSync is a digital marketplace designed to eliminate middlemen and ensure fair crop pricing.',
        'key_features': 'Key Features',
        'feature_msp': 'MSP Price Protection',
        'feature_direct': 'Direct Market Access',
        'feature_secure': 'Secure & Transparent',
        'phone': 'Phone Number',
        'address': 'Address',
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
        'demo_credentials': 'Demo Credentials',
        'buyer_accounts': 'Buyer Accounts',
        'farmer_accounts': 'Farmer Accounts',
    }
}

@app.context_processor
def inject_translations():
    def get_text(key):
        return TRANSLATIONS['en'].get(key, key)
    return dict(get_text=get_text)

# --- AUTHORIZATION DECORATORS ---

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        admin_user = session.get('admin_user')
        if not admin_user or admin_user.get('role') != 'admin':
            flash('Access denied. Admin privileges required.', 'error')
            return render_template('login.html'), 403
        return f(*args, **kwargs)
    return decorated_function

# --- PUBLIC / AUTH ROUTES ---

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    flash('Public registration is disabled. Please contact the Admin or use demo credentials.', 'error')
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        
        user = db.get_user_by_email(email)
        if not user:
            # Auto-run migration if database is cold / empty
            try:
                migrate_data.run_migration()
                user = db.get_user_by_email(email)
            except Exception as _e:
                print("[!] Migration trigger warning during login:", _e)

        if user:
            pwd_hash = user.get('password_hash', '')
            is_valid = False
            if pwd_hash and (pwd_hash.startswith('pbkdf2:') or pwd_hash.startswith('scrypt:') or pwd_hash.startswith('argon2:')):
                try:
                    is_valid = check_password_hash(pwd_hash, password)
                except Exception:
                    is_valid = False
            
            if not is_valid:
                if pwd_hash == password:
                    is_valid = True
                elif email == 'admin@cropsync.com' and password in ('admin123', 'admin'):
                    is_valid = True
                elif email.startswith('farmer') and password == 'farmer123':
                    is_valid = True
                elif email.startswith('buyer') and password == 'buyer123':
                    is_valid = True

            if is_valid:
                # Check account suspension status
                if user.get('account_status') == 'suspended':
                    reason = user.get('suspension_reason') or 'No reason specified'
                    flash(f'Your account has been suspended. Reason: {reason}', 'error')
                    return render_template('login.html')
                
                # Clear previous session and set role-specific user
                session.clear()
                if user['role'] == 'admin':
                    session['admin_user'] = user
                    return redirect(url_for('admin_dashboard'))
                elif user['role'] == 'farmer':
                    session['farmer_user'] = user
                    return redirect(url_for('farmer_dashboard'))
                elif user['role'] == 'buyer':
                    session['buyer_user'] = user
                    return redirect(url_for('buyer_dashboard'))
            
        flash('Invalid credentials', 'error')
    return render_template('login.html')



# --- FARMER DASHBOARD ROUTES ---

@app.route('/farmer_dashboard', methods=['GET', 'POST'])
def farmer_dashboard():
    if 'farmer_user' not in session:
        return redirect(url_for('login'))

    farmer_id = session['farmer_user']['id']

    if request.method == 'POST':
        crop_name = request.form.get('crop_name', '').strip().lower()
        quantity = request.form.get('quantity')
        price = request.form.get('price_per_kg')
        location = session['farmer_user'].get('location') or 'Unknown'

        if not all([crop_name, quantity, price]):
            flash('Crop name, quantity, and price are required', 'error')
            return redirect(url_for('farmer_dashboard'))

        try:
            qty = float(quantity)
            prc = float(price)
            msp = MSP_DATA.get(crop_name, 0)
            if prc < msp:
                flash(f'Price below MSP (₹{msp})!', 'error')
            else:
                db.create_crop(farmer_id, crop_name, qty, prc, location)
                flash('Listing added!', 'success')
                return redirect(url_for('farmer_dashboard', section='my-listings'))
        except ValueError:
            flash('Invalid numbers!', 'error')

    user_crops = db.get_crops(farmer_id=farmer_id)
    sold_orders = db.get_orders_for_farmer(farmer_id=farmer_id)
    earnings = sum(float(o['total_price']) for o in sold_orders if o['status'] == 'Accepted')

    return render_template('farmer_dashboard.html', crops=user_crops, earnings=earnings, msp_data=MSP_DATA, sold_orders=sold_orders)

@app.route('/delete_crop/<crop_id>')
def delete_crop(crop_id):
    if 'farmer_user' not in session:
        return redirect(url_for('login'))
    db.delete_crop(crop_id, session['farmer_user']['id'])
    flash('Listing deleted!', 'success')
    return redirect(url_for('farmer_dashboard', section='my-listings'))

@app.route('/accept_order/<order_id>')
def accept_order(order_id):
    if 'farmer_user' not in session:
        return redirect(url_for('login'))
    
    farmer_id = session['farmer_user']['id']
    orders = db.get_orders_for_farmer(farmer_id)
    order = next((o for o in orders if str(o['id']) == str(order_id)), None)
    
    if order and order['status'] == 'Pending':
        crop = db.get_crop_by_id(order['crop_id'])
        if crop and float(crop['quantity']) >= float(order['quantity']):
            new_qty = float(crop['quantity']) - float(order['quantity'])
            db.update_crop_quantity(order['crop_id'], new_qty)
            db.update_order_status(order_id, 'Accepted')
            flash('Order accepted and stock updated!', 'success')
        else:
            flash('Cannot accept: Insufficient stock.', 'error')
            
    return redirect(url_for('farmer_dashboard', section='sold-items'))

@app.route('/reject_order/<order_id>')
def reject_order(order_id):
    if 'farmer_user' not in session:
        return redirect(url_for('login'))
    db.update_order_status(order_id, 'Rejected')
    flash('Order rejected.', 'success')
    return redirect(url_for('farmer_dashboard', section='sold-items'))

# --- BUYER PORTAL ROUTES ---

@app.route('/buyer_dashboard')
def buyer_dashboard():
    if 'buyer_user' not in session:
        return redirect(url_for('login'))

    search = request.args.get('search', '').strip().lower()
    location = request.args.get('location', '').strip().lower()
    
    filtered_crops = db.get_crops(search=search, location=location)
    for c in filtered_crops:
        c['msp_value'] = MSP_DATA.get(c['crop_name'].lower(), 0)

    orders = db.get_orders_for_buyer(session['buyer_user']['id'])
    return render_template('buyer_dashboard.html', crops=filtered_crops, orders=orders, msp_data=MSP_DATA)

@app.route('/place_order', methods=['POST'])
def place_order():
    if 'buyer_user' not in session:
        return redirect(url_for('login'))

    crop_id = request.form.get('crop_id')
    try:
        quantity = float(request.form.get('quantity'))
    except (ValueError, TypeError):
        flash('Invalid quantity!', 'error')
        return redirect(url_for('buyer_dashboard'))
    
    crop = db.get_crop_by_id(crop_id)
    if crop and float(crop['quantity']) >= quantity:
        total_price = quantity * float(crop['price_per_kg'])
        db.create_order(
            buyer_id=session['buyer_user']['id'],
            farmer_id=crop['farmer_id'],
            crop_id=crop['id'],
            crop_name=crop['crop_name'],
            quantity=quantity,
            total_price=total_price
        )
        flash('Order placed! Waiting for farmer approval.', 'success')
    else:
        flash('Low stock or invalid order.', 'error')
    return redirect(url_for('buyer_dashboard', section='my-orders'))

# --- ADMIN PORTAL ROUTES ---

@app.route('/admin')
@admin_required
def admin_dashboard():
    stats = db.get_admin_stats()
    return render_template('admin/dashboard.html', stats=stats)

@app.route('/admin/farmers')
@admin_required
def admin_farmers():
    search = request.args.get('search', '').strip()
    farmers = db.get_all_farmers(search=search)
    return render_template('admin/farmers.html', farmers=farmers, search=search)

@app.route('/admin/farmers/<farmer_id>', methods=['GET', 'POST'])
@admin_required
def admin_farmer_detail(farmer_id):
    farmer = db.get_user_by_id(farmer_id)
    if not farmer or farmer['role'] != 'farmer':
        flash('Farmer record not found', 'error')
        return redirect(url_for('admin_farmers'))

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'update_profile':
            name = request.form.get('name', '').strip()
            phone = request.form.get('phone', '').strip()
            address = request.form.get('address', '').strip()
            location = request.form.get('location', '').strip()
            if name:
                db.update_user_profile(farmer_id, name=name, phone=phone, address=address, location=location)
                flash('Farmer profile updated successfully.', 'success')
        elif action == 'update_status':
            new_status = request.form.get('status')
            reason = request.form.get('reason', '').strip() if new_status == 'suspended' else None
            db.update_user_status(farmer_id, new_status, reason=reason)
            flash(f'Farmer account status updated to {new_status}.', 'success')
        return redirect(url_for('admin_farmer_detail', farmer_id=farmer_id))

    return render_template('admin/farmer_detail.html', farmer=farmer)

@app.route('/admin/buyers')
@admin_required
def admin_buyers():
    search = request.args.get('search', '').strip()
    buyers = db.get_all_buyers(search=search)
    return render_template('admin/buyers.html', buyers=buyers, search=search)

@app.route('/admin/buyers/<buyer_id>', methods=['GET', 'POST'])
@admin_required
def admin_buyer_detail(buyer_id):
    buyer = db.get_user_by_id(buyer_id)
    if not buyer or buyer['role'] != 'buyer':
        flash('Buyer record not found', 'error')
        return redirect(url_for('admin_buyers'))

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'update_profile':
            name = request.form.get('name', '').strip()
            phone = request.form.get('phone', '').strip()
            organization = request.form.get('organization', '').strip()
            address = request.form.get('address', '').strip()
            location = request.form.get('location', '').strip()
            if name:
                db.update_user_profile(buyer_id, name=name, phone=phone, address=address, location=location, organization=organization)
                flash('Buyer profile updated successfully.', 'success')
        elif action == 'update_status':
            new_status = request.form.get('status')
            reason = request.form.get('reason', '').strip() if new_status == 'suspended' else None
            db.update_user_status(buyer_id, new_status, reason=reason)
            flash(f'Buyer account status updated to {new_status}.', 'success')
        return redirect(url_for('admin_buyer_detail', buyer_id=buyer_id))

    return render_template('admin/buyer_detail.html', buyer=buyer)

@app.route('/admin/create_user', methods=['GET', 'POST'])
@admin_required
def admin_create_user():
    if request.method == 'POST':
        role = request.form.get('role')
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        phone = request.form.get('phone', '').strip()
        organization = request.form.get('organization', '').strip()
        location = request.form.get('location', '').strip()
        address = request.form.get('address', '').strip()

        if not all([role, name, email, password]):
            flash('Role, Name, Email, and Password are required.', 'error')
            return render_template('admin/create_user.html')

        if role not in ('farmer', 'buyer'):
            flash('Invalid role selected.', 'error')
            return render_template('admin/create_user.html')

        existing = db.get_user_by_email(email)
        if existing:
            flash(f'User with email {email} already exists.', 'error')
            return render_template('admin/create_user.html')

        pwd_hash = generate_password_hash(password, method='pbkdf2:sha256')
        db.create_user(
            email=email,
            password_hash=pwd_hash,
            role=role,
            name=name,
            phone=phone,
            address=address,
            location=location,
            organization=organization
        )
        flash(f'Successfully created new {role} account for {email}.', 'success')
        return redirect(url_for('admin_farmers' if role == 'farmer' else 'admin_buyers'))

    return render_template('admin/create_user.html')

# --- SETTINGS & LOGOUT ---

@app.route('/settings')
def settings():
    user = session.get('farmer_user') or session.get('buyer_user') or session.get('admin_user')
    if not user:
        return redirect(url_for('login'))
    return render_template('settings.html', session_user=user, active_role=user['role'])

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True)
