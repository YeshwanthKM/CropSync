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
        'welcome': 'Welcome to Smart AgriTrade, connecting farmers and buyers directly with MSP protection.',
        'get_started': 'Get Started',
        'farmer_login': 'Farmer Login',
        'buyer_login': 'Buyer Login',
        'guest_login': 'Guest Login',
        'tagline': 'Smart AgriTrade',
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
        'problem_desc': 'Small and marginal farmers often depend on middlemen due to lack of direct market access and price transparency, which leads to underpayment and reduced profits. There is a need for a simple, accessible digital platform that connects farmers directly with buyers while ensuring fair pricing protection.',
        'our_objective': 'Our Objective',
        'obj_1': 'Provide direct farmer-to-buyer connectivity',
        'obj_2': 'Ensure fair crop pricing using MSP validation',
        'obj_3': 'Increase farmer income and transparency',
        'obj_4': 'Promote digital inclusion in agriculture',
        'our_solution': 'Proposed Solution',
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
        'expected_impact': 'Expected Impact',
        'impact_1': 'Increased farmer profitability',
        'impact_2': 'Reduced dependency on intermediaries',
        'impact_3': 'Transparent agricultural trade',
        'impact_4': 'Support for SDG 1 (No Poverty) and SDG 2 (Zero Hunger)',
        'tech_used': 'Technology Used',
        'tech_1': 'Python Flask',
        'tech_2': 'JSON Database Storage',
        'tech_3': 'HTML5 & CSS3 Responsive UI',
        'tech_4': 'Gunicorn & Render Deployment',
        'short_about': 'About Smart AgriTrade',
        'short_desc': 'Smart AgriTrade is a digital marketplace designed to eliminate middlemen and ensure fair crop pricing. By integrating MSP-based validation, the platform protects farmers from underpayment while providing buyers with transparent and direct access to agricultural produce.',
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
    },
    'ta': {
        'home': 'முகப்பு',
        'login': 'உள்நுழை',
        'register': 'பதிவு செய்',
        'settings': 'அமைப்புகள்',
        'logout': 'வெளியேறு',
        'welcome': 'ஸ்மார்ட் அக்ரிட்ரேடுக்கு வரவேற்கிறோம், விவசாயிகள் மற்றும் வாங்குபவர்களை நேரடியாக MSP பாதுகாப்புடன் இணைக்கிறோம்.',
        'get_started': 'தொடங்கவும்',
        'farmer_login': 'விவசாயி உள்நுழைவு',
        'buyer_login': 'வாங்குபவர் உள்நுழைவு',
        'guest_login': 'விருந்தினர் உள்நுழைவு',
        'tagline': 'ஸ்மார்ட் அக்ரிட்ரேட்',
        'tagline_sub': 'விவசாயி-வாங்குபவர் இடையேயான ஒரு வெளிப்படையான டிஜிட்டல் சந்தை.',
        'footer': 'எளிமையானது. நியாயமானது. தொழில்முறை.',
        'name': 'முழு பெயர்',
        'email': 'மின்னஞ்சல் முகவரி',
        'password': 'கடவுச்சொல்',
        'role': 'பங்கு',
        'farmer': 'விவசாயி',
        'buyer': 'வாங்குபவர்',
        'create_account': 'கணக்கை உருவாக்கு',
        'already_account': 'ஏற்கனவே கணக்கு உள்ளதா?',
        'no_account': 'கணக்கு இல்லையா?',
        'login_here': 'இங்கே உள்நுழையவும்',
        'register_here': 'இங்கே பதிவு செய்யவும்',
        'welcome_back': 'மீண்டும் வருக',
        'farmer_dashboard': 'விவசாயி டாஷ்போர்டு',
        'buyer_dashboard': 'வாங்குபவர் டாஷ்போர்டு',
        'total_earnings': 'மொத்த வருவாய்',
        'active_listings': 'செயலில் உள்ள பட்டியல்கள்',
        'list_new_crop': 'புதிய பயிர் பட்டியல்',
        'msp_reference': 'MSP குறிப்பு',
        'crop_name': 'பயிரின் பெயர்',
        'quantity': 'அளவு',
        'price_per_kg': 'ஒரு கிலோ விலை',
        'location': 'இடம்',
        'add_new_listing': 'புதிய பட்டியலைச் சேர்க்கவும்',
        'my_crop_listings': 'எனது பயிர் பட்டியல்கள்',
        'action': 'நடவடிக்கை',
        'delete': 'நீக்கு',
        'search_marketplace': 'சந்தையைத் தேடு',
        'search': 'தேடு',
        'clear': 'அழி',
        'available_crops': 'கிடைக்கும் பயிர்கள்',
        'price': 'விலை',
        'stock': 'இருப்பு',
        'order': 'ஆர்டர்',
        'buy': 'வாங்கு',
        'my_orders': 'எனது ஆர்டர்கள்',
        'status': 'நிலை',
        'profile_settings': 'சுயவிவர அமைப்புகள்',
        'update_profile': 'சுயவிவரத்தைப் புதுப்பி',
        'password_info': 'தற்போதைய கடவுச்சொல்லை வைத்திருக்க காலியாக விடவும்',
        'save_changes': 'மாற்றங்களைச் சேமி',
        'language': 'மொழி',
        'english': 'ஆங்கிலம்',
        'tamil': 'தமிழ்',
        'project_overview': 'திட்ட மேலோட்டம்',
        'problem_statement': 'சிக்கல் அறிக்கை',
        'problem_desc': 'சிறு மற்றும் குறு விவசாயிகள் நேரடி சந்தை அணுகல் மற்றும் விலை வெளிப்படைத்தன்மை இல்லாததால் பெரும்பாலும் இடைத்தரகர்களை நம்பியிருக்கிறார்கள், இது குறைந்த ஊதியம் மற்றும் குறைந்த லாபத்திற்கு வழிவகுக்கிறது. விவசாயிகளை நேரடியாக வாங்குபவர்களுடன் இணைக்கும் எளிய, அணுகக்கூடிய டிஜிட்டல் தளம் தேவை.',
        'our_objective': 'எங்கள் நோக்கம்',
        'obj_1': 'நேரடி விவசாயி-வாங்குபவர் இணைப்பை வழங்குதல்',
        'obj_2': 'MSP சரிபார்ப்பைப் பயன்படுத்தி நியாயமான பயிர் விலையை உறுதி செய்தல்',
        'obj_3': 'விவசாயிகளின் வருமானம் மற்றும் வெளிப்படைத்தன்மையை அதிகரித்தல்',
        'obj_4': 'விவசாயத்தில் டிஜிட்டல் உள்ளடக்கத்தை ஊக்குவித்தல்',
        'our_solution': 'முன்மொழியப்பட்ட தீர்வு',
        'sol_f_title': 'விவசாயி டாஷ்போர்டு',
        'sol_f1': 'கிடைக்கும் பயிர்களை பட்டியலிடுங்கள்',
        'sol_f2': 'MSP குறிப்பு விலையைப் பார்க்கவும்',
        'sol_f3': 'ஆர்டர்களை நிர்வகிக்கவும்',
        'sol_f4': 'வருவாயைக் கண்காணிக்கவும்',
        'sol_b_title': 'வாங்குபவர் டாஷ்போர்டு',
        'sol_b1': 'பயிர்களை பெயர் மற்றும் இருப்பிடத்தின் அடிப்படையில் தேடுங்கள்',
        'sol_b2': 'விவசாயி விலையை MSP உடன் ஒப்பிட்டுப் பாருங்கள்',
        'sol_b3': 'பாதுகாப்பான ஆர்டர்களை வழங்கவும்',
        'fair_pricing': 'நியாயமான விலை வழிமுறை',
        'pricing_desc': 'குறைந்த விலையிடுவதைத் தடுக்கவும், விவசாயிகளின் வருமானத்தைப் பாதுகாக்கவும் மற்றும் வெளிப்படையான பரிவர்த்தனைகளை ஊக்குவிக்கிறது.',
        'pricing_gov': 'MSP மதிப்புகள் இந்திய அரசாங்கத்தின் வேளாண் செலவுகள் மற்றும் விலைகளுக்கான ஆணையம் வழங்கிய வழிகாட்டுதல்களின் அடிப்படையில் அமைந்துள்ளன.',
        'expected_impact': 'எதிர்பார்க்கப்படும் தாக்கம்',
        'impact_1': 'விவசாயிகளின் லாபம் அதிகரிப்பு',
        'impact_2': 'இடைத்தரகர்கள் மீதான சார்பு குறைப்பு',
        'impact_3': 'வெளிப்படையான விவசாய வர்த்தகம்',
        'impact_4': 'வறுமையின்மை (SDG 1) மற்றும் பசியின்மை (SDG 2) ஆகியவற்றிற்கான ஆதரவு',
        'tech_used': 'பயன்படுத்தப்பட்ட தொழில்நுட்பம்',
        'tech_1': 'பைதான் பிளாஸ்க் (Python Flask)',
        'tech_2': 'JSON தரவுத்தள சேமிப்பு',
        'tech_3': 'HTML5 & CSS3 பதிலளிக்கும் UI',
        'tech_4': 'Gunicorn & Render வரிசைப்படுத்தல்',
        'short_about': 'ஸ்மார்ட் அக்ரிட்ரேட் பற்றி',
        'short_desc': 'ஸ்மார்ட் அக்ரிட்ரேட் என்பது இடைத்தரகர்களைத் தவிர்க்கவும் நியாயமான பயிர் விலையை உறுதி செய்யவும் வடிவமைக்கப்பட்ட ஒரு டிஜிட்டல் சந்தையாகும். MSP அடிப்படையிலான சரிபார்ப்பை ஒருங்கிணைப்பதன் மூலம், விவசாயிகளை குறைந்த விலையில் இருந்து பாதுகாக்கிறது.',
        'key_features': 'முக்கிய அம்சங்கள்',
        'feature_msp': 'MSP விலை பாதுகாப்பு',
        'feature_direct': 'நேரடி சந்தை அணுகல்',
        'feature_secure': 'பாதுகாப்பான & வெளிப்படையான',
        'phone': 'தொலைபேசி எண்',
        'contact_details': 'தொடர்பு விவரங்கள்',
        'buyer_name': 'வாங்குபவர் பெயர்',
        'buyer_contact': 'வாங்குபவர் தொடர்பு',
        'sold_items': 'விற்கப்பட்ட பொருட்கள்',
        'farmer_contact': 'விவசாயி தொடர்பு',
        'no_phone': 'தொலைபேசி எண் வழங்கப்படவில்லை',
    }
}

@app.context_processor
def inject_translations():
    def get_text(key):
        lang = session.get('lang', 'en')
        return TRANSLATIONS.get(lang, TRANSLATIONS['en']).get(key, key)
    return dict(get_text=get_text)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/set_language/<lang>')
def set_language(lang):
    if lang in ['en', 'ta']:
        session['lang'] = lang
    return redirect(request.referrer or url_for('home'))

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
            o_copy['farmer_name'] = farmer_map.get(o['farmer_id'], 'Farmer')
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
