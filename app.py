import os
import json
import secrets
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify


from werkzeug.security import generate_password_hash, check_password_hash

import db
import migrate_data
from otp_service import OTPService
import services.email_service as email_service



app = Flask(__name__)
app.secret_key = 'cropsync-demo-secret-key-stable'

# Auto-initialize database & run migration on startup
try:
    db.init_db()
    migrate_data.run_migration()
except Exception as _e:
    print("[!] Database initialization warning:", _e)

# MSP Reference Data (Case-Insensitive Dictionary)
class CaseInsensitiveMSPData(dict):
    def get(self, key, default=None):
        if not key or not isinstance(key, str):
            return super().get(key, default)
        k_lower = key.strip().lower()
        for k, v in self.items():
            if k.lower() == k_lower:
                return v
        return default

    def __getitem__(self, key):
        val = self.get(key)
        if val is not None:
            return val
        return super().__getitem__(key)

MSP_DATA = CaseInsensitiveMSPData({
    'Rice': 21.83,
    'Wheat': 22.75,
    'Maize': 20.90,
    'Ragi': 38.46,
    'Bajra': 25.00,
    'Tur': 70.00,
    'Moong': 85.58,
    'Urad': 69.50,
    'Groundnut': 63.77,
    'Sunflower': 67.60,
    'Soyabean': 46.00,
    'Cotton': 66.20
})


CROP_TRANSLATIONS_TA = {
    'rice': 'அரிசி', 'wheat': 'கோதுமை', 'maize': 'சோளம்', 'ragi': 'கேழ்வரகு',
    'bajra': 'கம்பு', 'tur': 'துவரம் பருப்பு', 'moong': 'பாசிப் பருப்பு',
    'urad': 'உளுந்தம் பருப்பு', 'groundnut': 'நிலக்கடலை', 'sunflower': 'சூரியகாந்தி',
    'soyabean': 'சோயாபீன்ஸ்', 'cotton': 'பருத்தி', 'sugarcane': 'கரும்பு',
    'tomato': 'தக்காளி', 'potato': 'உருளைக்கிழங்கு', 'onion': 'வெங்காயம்',
    'chilli': 'மிளகாய்', 'turmeric': 'மஞ்சள்', 'banana': 'வாழைப்பழம்',
    'coconut': 'தேங்காய்', 'mustard': 'கடுகு', 'jute': 'சணல்', 'pulses': 'பருப்பு வகைகள்'
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
        'phone': 'Phone Number',
        'address': 'Address',
        'contact_details': 'Contact Details',
        'buyer_name': 'Buyer Name',
        'buyer_contact': 'Buyer Contact',
        'sold_items': 'Sold Items',
        'farmer_contact': 'Farmer Contact',
        'no_phone': 'No phone provided',
        'recent_activity': 'Recent Activity',
        'select_section_help': 'Select a section from the sidebar to manage your crops, view sales, or check market prices.',
        'select_crop_placeholder': 'Select crop...',
        'govt_msp_reference': 'Govt MSP Reference',
        'diff_vs_msp': 'Difference vs MSP',
        'enter_price': 'Enter price',
        'note_price_below_msp': '⚠️ Note: Your price is listed below the official Government MSP benchmark.',
        'auto_location_note': 'Auto-detected from your profile',
        'contact_revealed_on_acceptance': 'Contact revealed upon acceptance',
        'confirm_payment_received': '✓ Confirm Payment Received',
        'mark_completed': 'Mark Completed',
        'waiting_for_farmer': 'Waiting for farmer',
        'no_listings_yet': 'No active listings.',
        'no_orders_found': 'No orders found.',
        'marketplace_overview': 'Marketplace Overview'
    },
    'ta': {
        'home': 'முகப்பு',
        'login': 'உள்நுழை',
        'register': 'பதிவு செய்',
        'settings': 'அமைப்புகள்',
        'logout': 'வெளியேறு',
        'marketplace': 'சந்தை',
        'home_welcome': 'க்ராப்சின்க் (CropSync) என்பது விவசாயிகளையும் வாங்குபவர்களையும் நேரடியாக இணைக்கும் ஒரு வெளிப்படையான டிஜிட்டல் சந்தையாகும். எங்கள் தளம் அரசின் குறைந்தபட்ச ஆதரவு விலையை (MSP) ஒருங்கிணைத்து நியாயமான விலையை உறுதி செய்கிறது.',
        'welcome': 'பயிர்களுக்கு நியாயமான விலை கிடைக்க க்ராப்சின்க் விவசாயிகளையும் வாங்குபவர்களையும் நேரடியாக இணைக்கிறது.',
        'tagline': 'க்ராப்சின்க்',
        'tagline_sub': 'வெளிப்படையான விவசாயி-வாங்குபவர் டிஜிட்டல் சந்தை.',
        'farmer_dashboard': 'விவசாயி டாஷ்போர்டு',
        'total_earnings': 'மொத்த வருமானம்',
        'active_listings': 'செயலில் உள்ள பட்டியல்கள்',
        'list_new_crop': 'புதிய பயிர் பட்டியலிடு',
        'msp_reference': 'குறைந்தபட்ச ஆதரவு விலை (MSP)',
        'crop_name': 'பயிர் பெயர்',
        'quantity': 'அளவு',
        'price_per_kg': 'கிலோ விலை (₹)',
        'location': 'இடம்',
        'add_new_listing': 'புதிய பட்டியலைச் சேர்',
        'my_crop_listings': 'எனது பயிர் பட்டியல்கள்',
        'action': 'செயல்',
        'delete': 'நீக்கு',
        'my_orders': 'எனது ஆர்டர்கள்',
        'sold_items': 'ஆர்டர்கள் & விற்பனை',
        'status': 'நிலை',
        'profile_settings': 'சுயவிவர அமைப்புகள்',
        'update_profile': 'சுயவிவரத்தைப் புதுப்பி',
        'name': 'முழு பெயர்',
        'email': 'மின்னஞ்சல் முகவரி',
        'phone': 'தொலைபேசி எண்',
        'address': 'முகவரி',
        'role': 'பங்கு',
        'farmer': 'விவசாயி',
        'recent_activity': 'சமீபத்திய நடவடிக்கைகள்',
        'select_section_help': 'உங்கள் பயிர்களை நிர்வகிக்க, விற்பனையைப் பார்க்க அல்லது சந்தை விலைகளைச் சரிபார்க்க பக்கவாட்டு மெனுவிலிருந்து ஒரு பகுதியைத் தேர்ந்தெடுக்கவும்.',
        'select_crop_placeholder': 'பயிரைத் தேர்ந்தெடுக்கவும்...',
        'govt_msp_reference': 'அரசு MSP குறிப்பு',
        'diff_vs_msp': 'MSP உடன் ஒப்பீடு',
        'enter_price': 'விலையை உள்ளிடவும்',
        'note_price_below_msp': '⚠️ குறிப்பு: நீங்கள் குறிப்பிட்ட விலை அரசின் குறைந்தபட்ச ஆதரவு விலையை (MSP) விடக் குறைவாக உள்ளது.',
        'auto_location_note': 'உங்கள் சுயவிவரத்திலிருந்து தானாக கண்டறியப்பட்டது',
        'contact_revealed_on_acceptance': 'ஏற்றுக்கொண்ட பிறகு தொடர்பு விவரம் காண்பிக்கப்படும்',
        'confirm_payment_received': '✓ பணத்தைப் பெற்றதை உறுதிசெய்',
        'mark_completed': 'முடிந்ததாகக் குறி',
        'waiting_for_farmer': 'விவசாயிக்காக காத்திருக்கிறது',
        'no_listings_yet': 'நீங்கள் இன்னும் எந்த பயிரையும் பட்டியலிடவில்லை.',
        'no_orders_found': 'ஆர்டர்கள் எதுவும் கிடைக்கவில்லை.',
        'marketplace_overview': 'சந்தை மேலோட்டம்'
    }
}

@app.context_processor
def inject_translations():
    farmer_lang = session.get('farmer_lang', 'en') if session.get('farmer_user') else 'en'

    def get_text(key, default=None):
        if farmer_lang == 'ta' and 'ta' in TRANSLATIONS and key in TRANSLATIONS['ta']:
            return TRANSLATIONS['ta'][key]
        return TRANSLATIONS['en'].get(key, default if default is not None else key)

    def crop_display(crop_name):
        if not crop_name:
            return ''
        key = str(crop_name).strip()
        lower_key = key.lower()
        ta_val = CROP_TRANSLATIONS_TA.get(lower_key) or CROP_TRANSLATIONS_TA.get(key)
        if farmer_lang == 'ta' and ta_val:
            return f"{key.capitalize()} ({ta_val})"
        return key.capitalize()

    return dict(get_text=get_text, crop_display=crop_display, farmer_lang=farmer_lang)

@app.route('/toggle_farmer_language')
def toggle_farmer_language():
    current_lang = session.get('farmer_lang', 'en')
    new_lang = 'ta' if current_lang == 'en' else 'en'
    session['farmer_lang'] = new_lang
    referrer = request.referrer or url_for('farmer_dashboard')
    return redirect(referrer)

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


def logistics_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        logistics_user = session.get('logistics_user')
        if not logistics_user or logistics_user.get('role') != 'logistics':
            flash('Access denied. Logistics Partner privileges required.', 'error')
            return render_template('login.html'), 403
        return f(*args, **kwargs)
    return decorated_function



from auth_service import SupabaseAuthService, EmailService

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])

def register():
    if request.method == 'POST':
        role = request.form.get('role', 'farmer').lower()
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        location = request.form.get('location', '').strip()
        address = request.form.get('address', '').strip()
        organization = request.form.get('organization', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Server-side Role Protection: Never allow admin registration via form
        if role not in ('farmer', 'buyer'):
            flash('Invalid registration role.', 'error')
            return render_template('register.html')

        if not all([name, email, phone, password, confirm_password]):
            flash('All required fields must be filled.', 'error')
            return render_template('register.html')

        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('register.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
            return render_template('register.html')

        # Check existing email
        existing_user = db.get_user_by_email(email)
        if existing_user:
            flash(f'An account with email {email} already exists.', 'error')
            return render_template('register.html')

        try:
            pwd_hash = generate_password_hash(password, method='pbkdf2:sha256')
            user_id = db.create_user(
                email=email,
                password_hash=pwd_hash,
                role=role,
                name=name,
                phone=phone,
                location=location,
                address=address,
                organization=organization,
                status='pending',
                email_verified=False,
                phone_verified=True
            )

            # Generate and assign verification token
            v_token = secrets.token_urlsafe(32)
            db.set_verification_token(user_id, v_token)
            
            # Dispatch direct verification email
            email_sent, email_err = EmailService.send_verification_email(email, v_token)

            session['pending_user_id'] = user_id
            session['pending_email'] = email
            if email_err and not email_sent:
                session['auth_err'] = str(email_err)
            else:
                session.pop('auth_err', None)

            flash('Account created! Please check your email to activate your account.', 'success')
            return redirect(url_for('verify_email_pending'))

        except Exception as e:
            print("[!] Registration error:", e)
            flash(f'Error creating account: {str(e)}', 'error')
            return render_template('register.html')

    return render_template('register.html')


@app.route('/verify-email-pending')
def verify_email_pending():
    email = session.get('pending_email') or session.get('pending_user', {}).get('email')
    if not email:
        return redirect(url_for('login'))
    auth_err = session.get('auth_err')
    return render_template('verify_email_pending.html', email=email, auth_err=auth_err)


@app.route('/confirm-email')
def confirm_email():
    token = request.args.get('token', '').strip()
    email = request.args.get('email', '').strip().lower() or session.get('pending_email')
    user_id = session.get('pending_user_id')

    if token:
        u = db.get_user_by_verification_token(token)
        if u: user_id = u['id']

    if not user_id and email:
        u = db.get_user_by_email(email)
        if u: user_id = u['id']

    # Fallback for cross-device or new browser link clicks
    if not user_id:
        try:
            conn, db_type = db.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id, email, role FROM users WHERE account_status = 'pending' ORDER BY created_at DESC LIMIT 1")
            row = cursor.fetchone()
            if row:
                u = db._dict_row(row)
                user_id = u['id']
        except Exception as e:
            print("[!] Confirm email fallback lookup error:", e)

    if user_id:
        db.update_email_verified(user_id, True)
        db.update_user_status(user_id, 'active')
        updated_user = db.get_user_by_id(user_id)
        session.clear()
        if updated_user['role'] == 'farmer':
            session['farmer_user'] = updated_user
            flash('Email verified successfully! Welcome to CropSync Farmer Dashboard.', 'success')
            return redirect(url_for('farmer_dashboard'))
        else:
            session['buyer_user'] = updated_user
            flash('Email verified successfully! Welcome to CropSync Buyer Portal.', 'success')
            return redirect(url_for('buyer_dashboard'))
    else:
        flash('Email verified! Please log in to access your account.', 'success')
        return redirect(url_for('login'))





@app.route('/resend-email-verification', methods=['POST'])
def resend_email_verification():
    email = session.get('pending_email')
    flash(f'A new verification link has been sent to {email}.', 'success')
    return redirect(url_for('verify_email_pending'))

@app.route('/verify-phone', methods=['GET', 'POST'])
def verify_phone():
    user_id = session.get('pending_user_id')
    user = None
    if user_id:
        user = db.get_user_by_id(user_id)
    elif session.get('pending_email'):
        user = db.get_user_by_email(session['pending_email'])
        if user: user_id = user['id']

    if not user:
        flash('Session expired. Please log in.', 'error')
        return redirect(url_for('login'))

    dev_otp = None
    if not os.environ.get('SMS_PROVIDER_API_KEY'):
        dev_otp = session.get('last_otp')

    if request.method == 'POST':
        submitted_otp = request.form.get('otp', '').strip()
        stored_hash = user.get('otp_hash')
        expires_at = user.get('otp_expires_at')

        # Check expiration
        if expires_at:
            try:
                exp_dt = datetime.fromisoformat(str(expires_at).replace('Z', ''))
                if datetime.utcnow() > exp_dt:
                    flash('OTP code has expired. Please request a new OTP.', 'error')
                    return render_template('verify_phone.html', user=user, phone=user.get('phone'), dev_otp=dev_otp)
            except Exception:
                pass

        if OTPService.verify_otp_hash(stored_hash, submitted_otp):
            db.update_phone_verified(user_id, True)
            db.update_user_status(user_id, 'active')
            
            # Clear pending session and log user into dashboard session
            updated_user = db.get_user_by_id(user_id)
            session.clear()
            if updated_user['role'] == 'farmer':
                session['farmer_user'] = updated_user
                flash('Phone verified! Welcome to CropSync Farmer Dashboard.', 'success')
                return redirect(url_for('farmer_dashboard'))
            else:
                session['buyer_user'] = updated_user
                flash('Phone verified! Welcome to CropSync Buyer Portal.', 'success')
                return redirect(url_for('buyer_dashboard'))
        else:
            db.increment_otp_attempts(user_id)
            flash('Invalid OTP code. Please try again.', 'error')

    return render_template('verify_phone.html', user=user, phone=user.get('phone'), dev_otp=dev_otp)

@app.route('/resend-phone-otp', methods=['POST'])
def resend_phone_otp():
    user_id = session.get('pending_user_id')
    user = db.get_user_by_id(user_id) if user_id else None
    if user:
        otp_code = OTPService.generate_otp()
        otp_hash = OTPService.hash_otp(otp_code)
        expires_at = (datetime.utcnow() + timedelta(minutes=5)).isoformat()
        db.set_phone_otp(user_id, otp_hash, expires_at)
        session['last_otp'] = otp_code
        OTPService.send_sms(user.get('phone'), otp_code)
        flash('A fresh OTP code has been generated.', 'success')
    return redirect(url_for('verify_phone'))


@app.route('/verification-status')
def verification_status():
    user_id = session.get('pending_user_id')
    user = db.get_user_by_id(user_id) if user_id else None
    if not user:
        user = session.get('farmer_user') or session.get('buyer_user') or session.get('admin_user')
    if not user:
        return redirect(url_for('login'))
    return render_template('verification_status.html', user=user)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        if request.args.get('logout'):
            session.clear()

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()

        # Map short username aliases to system accounts
        if email in ('logistics', 'logistics1') or 'logistics' in email:
            email = 'logistics@cropsync.com'
        elif email in ('admin', 'admin1'):
            email = 'admin@cropsync.com'
        
        # 1. Fetch user from DB
        user = None
        try:
            user = db.get_user_by_email(email)
        except Exception as _e:
            print("[!] DB Error during login:", _e)

        # 2. Fallback demo user object if DB user lookup returns None
        if not user:
            if email == 'admin@cropsync.com' and password in ('admin123', 'admin'):
                user = {'id': 'admin1', 'email': 'admin@cropsync.com', 'role': 'admin', 'name': 'System Administrator', 'account_status': 'active', 'email_verified': True, 'phone_verified': True}
            elif email == 'logistics@cropsync.com' and password in ('logistics123', 'logistics'):
                user = {'id': 'logistics1', 'email': 'logistics@cropsync.com', 'role': 'logistics', 'name': 'CropSync Logistics', 'account_status': 'active', 'email_verified': True, 'phone_verified': True}

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
                elif (email == 'logistics@cropsync.com' or user.get('role') == 'logistics') and password in ('logistics123', 'logistics'):
                    is_valid = True

            if is_valid:
                if user.get('account_status') == 'suspended':
                    reason = user.get('suspension_reason') or 'No reason specified'
                    flash(f'Your account has been suspended. Reason: {reason}', 'error')
                    return render_template('login.html')

                if user.get('account_status') == 'pending':
                    session['pending_user_id'] = user['id']
                    session['pending_email'] = user['email']
                    flash('Your account is pending verification. Please complete verification.', 'error')
                    return redirect(url_for('verification_status'))
                
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
                elif user['role'] == 'logistics':
                    session['logistics_user'] = user
                    return redirect(url_for('logistics_dashboard'))
            
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

    farmer_user = db.get_user_by_id(farmer_id) or session['farmer_user']
    session['farmer_user'] = farmer_user

    user_crops = db.get_crops(farmer_id=farmer_id)
    sold_orders = db.get_orders_for_farmer(farmer_id=farmer_id)
    earnings = round(sum(float(o['total_price']) for o in sold_orders if o['status'] in ('Accepted', 'Completed')), 2)

    return render_template('farmer_dashboard.html', crops=user_crops, earnings=earnings, msp_data=MSP_DATA, sold_orders=sold_orders, farmer_user=farmer_user)

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
    success, msg = db.accept_order_atomic(order_id, farmer_id)
    
    if success:
        flash('Order accepted and stock updated!', 'success')
        # Dispatch notification email to buyer
        try:
            orders = db.get_orders_for_farmer(farmer_id)
            order = next((o for o in orders if str(o['id']) == str(order_id)), None)
            if order:
                buyer = db.get_user_by_id(order['buyer_id'])
                farmer = db.get_user_by_id(farmer_id)
                if buyer and farmer:
                    email_service.send_order_accepted_email(order, buyer, farmer)
        except Exception as e:
            print("[!] Error dispatching order accepted email:", e)
    else:
        flash(f'Cannot accept order: {msg}', 'error')
            
    return redirect(url_for('farmer_dashboard', section='sold-items'))

@app.route('/reject_order/<order_id>')
def reject_order(order_id):
    if 'farmer_user' not in session:
        return redirect(url_for('login'))
    
    farmer_id = session['farmer_user']['id']
    orders = db.get_orders_for_farmer(farmer_id)
    order = next((o for o in orders if str(o['id']) == str(order_id)), None)
    
    if not order:
        flash('Order not found or unauthorized.', 'error')
        return redirect(url_for('farmer_dashboard', section='sold-items'))

    # Duplicate Action Protection
    if order['status'] != 'Pending':
        flash(f'Order is already {order["status"]}.', 'error')
        return redirect(url_for('farmer_dashboard', section='sold-items'))

    db.update_order_status(order_id, 'Rejected')
    flash('Order rejected.', 'success')

    # Dispatch rejection email to buyer
    try:
        buyer = db.get_user_by_id(order['buyer_id'])
        if buyer:
            email_service.send_order_rejected_email(order, buyer)
    except Exception as e:
        print("[!] Error dispatching order rejected email:", e)

    return redirect(url_for('farmer_dashboard', section='sold-items'))

@app.route('/buyer/confirm_received/<order_id>')
def buyer_confirm_order_received(order_id):
    user = session.get('buyer_user')
    if not user:
        flash('Unauthorized access.', 'error')
        return redirect(url_for('buyer_dashboard'))

    buyer_id = user['id']
    success, msg, updated_order = db.buyer_confirm_order_received_atomic(order_id, buyer_id)
    if success:
        flash('Order receipt confirmed! Waiting for farmer payment confirmation.', 'success')
    else:
        flash(msg, 'error')

    return redirect(url_for('buyer_dashboard', section='my-orders'))

@app.route('/complete_order/<order_id>')
def complete_order(order_id):
    user = session.get('farmer_user') or session.get('buyer_user') or session.get('admin_user')
    if not user:
        return redirect(url_for('login'))

    user_id = user['id']
    role = user['role']
    
    if role == 'buyer':
        return redirect(url_for('buyer_confirm_order_received', order_id=order_id))

    success, msg = db.complete_order_atomic(order_id, user_id, role)

    if success:
        flash('Order marked as Completed!', 'success')
        try:
            order = db.get_order_by_id_admin(order_id)
            if order:
                buyer = db.get_user_by_id(order['buyer_id'])
                farmer = db.get_user_by_id(order['farmer_id'])
                if buyer:
                    email_service.send_order_completed_email(order, buyer, 'buyer')
                if farmer:
                    email_service.send_order_completed_email(order, farmer, 'farmer')
        except Exception as e:
            print("[!] Error dispatching order completed email:", e)
    else:
        flash(f'Error completing order: {msg}', 'error')

    if role == 'farmer':
        return redirect(url_for('farmer_dashboard', section='sold-items'))
    else:
        return redirect(url_for('admin_orders'))

@app.route('/farmer/confirm_payment/<order_id>')
def confirm_farmer_payment_received(order_id):
    user = session.get('farmer_user')
    if not user:
        flash('Unauthorized access.', 'error')
        return redirect(url_for('farmer_dashboard'))

    farmer_id = user['id']
    success, msg, updated_order = db.farmer_confirm_payment_received_atomic(order_id, farmer_id)
    if success:
        flash('Payout payment receipt confirmed! Order marked as Completed.', 'success')
        try:
            if updated_order:
                email_service.dispatch_logistics_milestone_emails(updated_order, 'SETTLED')
        except Exception as e:
            print("[!] Error dispatching settlement confirmation email:", e)
    else:
        flash(msg, 'error')

    return redirect(url_for('farmer_dashboard', section='sold-items'))

# --- BUYER PORTAL ROUTES ---

@app.route('/buyer_dashboard', methods=['GET', 'POST'])
def buyer_dashboard():
    if 'buyer_user' not in session:
        return redirect(url_for('login'))

    search = request.args.get('search', '').strip().lower()
    location = request.args.get('location', '').strip().lower()
    
    filtered_crops = db.get_crops(search=search, location=location)
    for c in filtered_crops:
        msp_val = None
        msp_record = db.get_msp_by_crop(c['crop_name'])
        if msp_record:
            msp_val = float(msp_record['msp_price_per_kg'])
        else:
            fallback = MSP_DATA.get(c['crop_name'])
            if fallback:
                msp_val = float(fallback)

        if msp_val is not None:
            c['msp_value'] = msp_val
            farmer_price = float(c['price_per_kg'])
            diff_pct = round(((farmer_price - msp_val) / msp_val) * 100, 1)
            c['msp_diff_pct'] = diff_pct
            c['msp_diff_text'] = f"+{diff_pct}% above MSP" if diff_pct >= 0 else f"{diff_pct}% below MSP"
        else:
            c['msp_value'] = None
            c['msp_diff_pct'] = None
            c['msp_diff_text'] = 'N/A'

    orders = db.get_orders_for_buyer(session['buyer_user']['id'])
    for o in orders:
        c_name = o.get('crop_name', '')
        msp_val = None
        msp_record = db.get_msp_by_crop(c_name)
        if msp_record:
            msp_val = float(msp_record['msp_price_per_kg'])
        else:
            fallback = MSP_DATA.get(c_name)
            if fallback:
                msp_val = float(fallback)

        if msp_val is not None:
            o['msp_value'] = msp_val
            qty = float(o.get('quantity', 1) or 1)
            unit_price = float(o.get('total_price', 0)) / qty if qty > 0 else 0
            diff_pct = round(((unit_price - msp_val) / msp_val) * 100, 1)
            o['msp_diff_pct'] = diff_pct
            o['msp_diff_text'] = f"+{diff_pct}% above MSP" if diff_pct >= 0 else f"{diff_pct}% below MSP"
        else:
            o['msp_value'] = None
            o['msp_diff_pct'] = None
            o['msp_diff_text'] = 'N/A'

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
    
    fulfillment_method = request.form.get('fulfillment_method', 'Direct Collection')
    if fulfillment_method not in ('Direct Collection', 'Logistics Partner'):
        fulfillment_method = 'Direct Collection'

    crop = db.get_crop_by_id(crop_id)
    if crop and float(crop['quantity']) >= quantity:
        total_price = round(quantity * float(crop['price_per_kg']), 2)
        
        if fulfillment_method == 'Logistics Partner':
            logistics_fee = 50.0
            cod_amount = round(total_price + logistics_fee, 2)
            farmer_settlement_amount = total_price
        else:
            logistics_fee = 0.0
            cod_amount = 0.0
            farmer_settlement_amount = total_price

        buyer_user = session.get('buyer_user', {})
        buyer_db = db.get_user_by_id(buyer_user.get('id')) if buyer_user.get('id') else {}
        farmer_user = db.get_user_by_id(crop['farmer_id']) or {}

        pickup_address = farmer_user.get('address') or farmer_user.get('location') or crop.get('location', '') or 'Farm Address'
        delivery_address = (
            request.form.get('delivery_address', '').strip() or 
            buyer_db.get('address') or 
            buyer_db.get('location') or 
            buyer_user.get('address') or 
            buyer_user.get('location') or 
            'Delivery Address'
        )

        try:
            order_id = db.create_order(
                buyer_id=buyer_user['id'],
                farmer_id=crop['farmer_id'],
                crop_id=crop['id'],
                crop_name=crop['crop_name'],
                quantity=quantity,
                total_price=total_price,
                fulfillment_method=fulfillment_method,
                logistics_fee=logistics_fee,
                cod_amount=cod_amount,
                farmer_settlement_amount=farmer_settlement_amount,
                pickup_address=pickup_address,
                delivery_address=delivery_address
            )
            flash('Order placed! Waiting for farmer approval.', 'success')

            # Dispatch email notification to farmer
            try:
                farmer = db.get_user_by_id(crop['farmer_id'])
                buyer = db.get_user_by_id(buyer_user['id'])
                order = {
                    'id': order_id,
                    'crop_name': crop['crop_name'],
                    'quantity': quantity,
                    'unit_price': crop['price_per_kg'],
                    'total_price': total_price,
                    'location': crop.get('location'),
                    'fulfillment_method': fulfillment_method
                }
                if farmer:
                    email_service.send_new_order_email(order, farmer, buyer)
            except Exception as e:
                print("[!] Error dispatching new order email:", e)
        except Exception as e:
            print("[!] Error creating order:", e)
            flash(f'Failed to place order: {str(e)}', 'error')
    else:
        flash('Low stock or invalid order.', 'error')
    return redirect(url_for('buyer_dashboard', section='my-orders'))


# --- ADMIN PORTAL ROUTES ---

@app.route('/admin', methods=['GET', 'POST'])
@admin_required
def admin_dashboard():
    stats = db.get_admin_dashboard_stats()
    return render_template('admin/dashboard.html', stats=stats, active_page='dashboard')

@app.route('/admin/farmers', methods=['GET', 'POST'])
@admin_required
def admin_farmers():
    search = request.args.get('search', '').strip()
    status_filter = request.args.get('status', 'all').strip()
    farmers = db.get_all_farmers(search=search, status_filter=status_filter)
    return render_template('admin/farmers.html', farmers=farmers, search=search, status_filter=status_filter, active_page='farmers')

@app.route('/admin/farmers/<farmer_id>', methods=['GET', 'POST'])
@admin_required
def admin_farmer_detail(farmer_id):
    farmer = db.get_user_by_id(farmer_id)
    if not farmer or farmer['role'] != 'farmer':
        flash('Farmer record not found', 'error')
        return redirect(url_for('admin_farmers'))

    if request.method == 'POST':
        admin_id = session.get('admin_user', {}).get('id')
        action = request.form.get('action')
        if action == 'update_profile':
            name = request.form.get('name', '').strip()
            phone = request.form.get('phone', '').strip()
            address = request.form.get('address', '').strip()
            location = request.form.get('location', '').strip()
            if name:
                db.update_user_profile(farmer_id, name=name, phone=phone, address=address, location=location)
                db.log_admin_action(admin_id, 'UPDATE_FARMER_PROFILE', farmer_id, 'Admin updated farmer profile')
                flash('Farmer profile updated successfully.', 'success')
        elif action == 'update_status':
            new_status = request.form.get('status')
            reason = request.form.get('reason', '').strip() if new_status == 'suspended' else None
            if new_status == 'suspended':
                email = farmer['email']
                if email.lower() in db.PERMANENT_DEMO_EMAILS:
                    flash(f'Permanent demo account ({email}) is protected and cannot be deleted or suspended.', 'error')
                    return redirect(url_for('admin_farmers'))
                SupabaseAuthService.delete_user_by_email(email)
                db.log_admin_action(admin_id, 'SUSPEND_AND_PURGE_USER', farmer_id, reason or 'Account suspended and purged by admin')
                db.delete_user(farmer_id)
        elif action == 'toggle_verification':
            is_verified = request.form.get('is_verified') == 'true'
            success, msg = db.set_farmer_verification_admin(farmer_id, is_verified, admin_id=admin_id)
            if success:
                status_str = "Verified" if is_verified else "Unverified"
                flash(f'Farmer verification updated to {status_str}.', 'success')
            else:
                flash(msg, 'error')
        return redirect(url_for('admin_farmer_detail', farmer_id=farmer_id))

    return render_template('admin/farmer_detail.html', farmer=farmer, active_page='farmers')

@app.route('/admin/farmers/toggle_verify/<farmer_id>', methods=['GET', 'POST'])
@admin_required
def admin_toggle_verify_farmer(farmer_id):
    farmer = db.get_user_by_id(farmer_id)
    if not farmer or farmer['role'] != 'farmer':
        flash('Farmer record not found', 'error')
        return redirect(url_for('admin_farmers'))
        
    admin_id = session.get('admin_user', {}).get('id')
    current_verified = bool(farmer.get('is_verified'))
    new_verified = not current_verified
    
    success, msg = db.set_farmer_verification_admin(farmer_id, new_verified, admin_id=admin_id)
    if success:
        status_str = "Verified" if new_verified else "Unverified"
        flash(f'Farmer {farmer.get("name", "account")} is now marked as {status_str}.', 'success')
    else:
        flash(msg, 'error')
        
    referrer = request.referrer
    if referrer and 'farmer_detail' in referrer:
        return redirect(url_for('admin_farmer_detail', farmer_id=farmer_id))
    return redirect(url_for('admin_farmers'))

@app.route('/admin/buyers', methods=['GET', 'POST'])
@admin_required
def admin_buyers():
    search = request.args.get('search', '').strip()
    status_filter = request.args.get('status', 'all').strip()
    buyers = db.get_all_buyers(search=search, status_filter=status_filter)
    return render_template('admin/buyers.html', buyers=buyers, search=search, status_filter=status_filter, active_page='buyers')

@app.route('/admin/buyers/<buyer_id>', methods=['GET', 'POST'])
@admin_required
def admin_buyer_detail(buyer_id):
    buyer = db.get_user_by_id(buyer_id)
    if not buyer or buyer['role'] != 'buyer':
        flash('Buyer record not found', 'error')
        return redirect(url_for('admin_buyers'))

    if request.method == 'POST':
        admin_id = session.get('admin_user', {}).get('id')
        action = request.form.get('action')
        if action == 'update_profile':
            name = request.form.get('name', '').strip()
            phone = request.form.get('phone', '').strip()
            organization = request.form.get('organization', '').strip()
            address = request.form.get('address', '').strip()
            location = request.form.get('location', '').strip()
            if name:
                db.update_user_profile(buyer_id, name=name, phone=phone, address=address, location=location, organization=organization)
                db.log_admin_action(admin_id, 'UPDATE_BUYER_PROFILE', buyer_id, 'Admin updated buyer profile')
                flash('Buyer profile updated successfully.', 'success')
        elif action == 'update_status':
            new_status = request.form.get('status')
            reason = request.form.get('reason', '').strip() if new_status == 'suspended' else None
            if new_status == 'suspended':
                email = buyer['email']
                if email.lower() in db.PERMANENT_DEMO_EMAILS:
                    flash(f'Permanent demo account ({email}) is protected and cannot be deleted or suspended.', 'error')
                    return redirect(url_for('admin_buyers'))
                SupabaseAuthService.delete_user_by_email(email)
                db.log_admin_action(admin_id, 'SUSPEND_AND_PURGE_USER', buyer_id, reason or 'Account suspended and purged by admin')
                db.delete_user(buyer_id)
                flash(f'Account for {email} has been completely removed. The email is now available for new registrations.', 'success')
                return redirect(url_for('admin_buyers'))
            else:
                db.update_user_status(buyer_id, new_status, reason=reason)
                db.log_admin_action(admin_id, f'UPDATE_STATUS_{new_status.upper()}', buyer_id, reason)
                flash(f'Buyer account status updated to {new_status}.', 'success')
        return redirect(url_for('admin_buyer_detail', buyer_id=buyer_id))

    return render_template('admin/buyer_detail.html', buyer=buyer, active_page='buyers')

@app.route('/admin/listings', methods=['GET', 'POST'])
@admin_required
def admin_listings():
    listings = db.get_all_listings_admin()
    return render_template('admin/listings.html', listings=listings, active_page='listings')

@app.route('/admin/listings/status/<crop_id>/<status>')
@admin_required
def admin_listing_status(crop_id, status):
    if status not in ('available', 'disabled', 'archived'):
        flash('Invalid status.', 'error')
        return redirect(url_for('admin_listings'))
    admin_id = session.get('admin_user', {}).get('id')
    db.update_listing_status_admin(crop_id, status, admin_id=admin_id)
    flash(f'Listing status updated to {status}.', 'success')
    return redirect(url_for('admin_listings'))

@app.route('/admin/orders', methods=['GET', 'POST'])
@admin_required
def admin_orders():
    status_filter = request.args.get('status', 'All').strip()
    orders = db.get_all_orders_admin(status_filter=status_filter)
    all_notifs = db.get_all_email_notifications_admin()
    
    notif_map = {}
    for n in all_notifs:
        oid = str(n.get('order_id'))
        if oid not in notif_map:
            notif_map[oid] = []
        notif_map[oid].append(n)
        
    for o in orders:
        o['email_logs'] = notif_map.get(str(o['id']), [])

    return render_template('admin/orders.html', orders=orders, status_filter=status_filter, active_page='orders')


@app.route('/admin/msp', methods=['GET', 'POST'])
@admin_required
def admin_msp():
    search = request.args.get('search', '').strip()
    season = request.args.get('season', 'All').strip()
    year = request.args.get('year', 'All').strip()
    msp_records = db.get_all_msp_references(search=search, season=season, year=year)
    return render_template('admin/msp.html', msp_records=msp_records, search=search, season=season, year=year, active_page='msp')


@app.route('/admin/msp/save', methods=['POST'])
@admin_required
def admin_msp_save():
    crop_name = request.form.get('crop_name', '').strip()
    price_per_kg = request.form.get('msp_price_per_kg', '').strip()
    category = request.form.get('category', 'Cereals').strip()
    season = request.form.get('season', 'Kharif').strip()
    effective_year = request.form.get('effective_year', '2025').strip()
    source = request.form.get('source', 'Ministry of Agriculture & Farmers Welfare, Govt of India').strip()

    if not crop_name or not price_per_kg:
        flash('Crop name and MSP price are required.', 'error')
        return redirect(url_for('admin_msp'))

    try:
        db.save_msp_reference(
            crop_name=crop_name,
            msp_price_per_kg=float(price_per_kg),
            category=category,
            season=season,
            effective_year=int(effective_year),
            source=source
        )
        admin_id = session.get('admin_user', {}).get('id')
        db.log_admin_action(admin_id, f"Admin updated MSP for {crop_name} to ₹{price_per_kg}/kg")
        flash(f'MSP reference for {crop_name} saved successfully.', 'success')
    except Exception as e:
        flash(f'Error saving MSP reference: {e}', 'error')

    return redirect(url_for('admin_msp'))

@app.route('/admin/msp/toggle/<crop_name>')
@admin_required
def admin_msp_toggle(crop_name):
    record = db.get_msp_by_crop(crop_name)
    if not record:
        flash('MSP reference not found.', 'error')
        return redirect(url_for('admin_msp'))
    new_status = 'inactive' if record.get('status') == 'active' else 'active'
    db.toggle_msp_status(crop_name, new_status)
    admin_id = session.get('admin_user', {}).get('id')
    db.log_admin_action(admin_id, f"Admin toggled MSP status for {crop_name} to {new_status}")
    flash(f'MSP status for {crop_name} set to {new_status}.', 'success')
    return redirect(url_for('admin_msp'))

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
            return render_template('admin/create_user.html', active_page='create_user')

        if role not in ('farmer', 'buyer', 'logistics'):
            flash('Invalid role selected.', 'error')
            return render_template('admin/create_user.html', active_page='create_user')

        existing = db.get_user_by_email(email)
        if existing:
            flash(f'User with email {email} already exists.', 'error')
            return render_template('admin/create_user.html', active_page='create_user')

        try:
            pwd_hash = generate_password_hash(password, method='pbkdf2:sha256')
            db.create_user(
                email=email,
                password_hash=pwd_hash,
                role=role,
                name=name,
                phone=phone,
                address=address,
                location=location,
                organization=organization,
                status='active',
                email_verified=True,
                phone_verified=True
            )

            flash(f'Successfully created new {role} account for {email}.', 'success')
            if role == 'farmer':
                return redirect(url_for('admin_farmers'))
            elif role == 'buyer':
                return redirect(url_for('admin_buyers'))
            else:
                return redirect(url_for('admin_logistics'))
        except Exception as e:
            print("[!] Error creating user:", e)
            flash(f'Error creating user: {str(e)}', 'error')
            return render_template('admin/create_user.html', active_page='create_user')

    return render_template('admin/create_user.html', active_page='create_user')


@app.route('/admin/logistics')
@admin_required
def admin_logistics():
    logistics_users = db.get_all_logistics_users()
    orders = db.get_logistics_orders()
    stats = db.get_logistics_dashboard_stats()
    return render_template(
        'admin/logistics.html',
        logistics_users=logistics_users,
        orders=orders,
        stats=stats,
        active_page='logistics'
    )


@app.route('/admin/logistics/toggle_status/<user_id>', methods=['GET', 'POST'])
@admin_required
def admin_toggle_user_status(user_id):
    user = db.get_user_by_id(user_id)
    if not user:
        flash('Logistics account not found.', 'error')
        return redirect(url_for('admin_logistics'))
    
    if user.get('email', '').strip().lower() in db.PERMANENT_DEMO_EMAILS:
        flash(f"Permanent demo account ({user['email']}) is protected and cannot be suspended.", 'error')
        return redirect(url_for('admin_logistics'))

    new_status = 'suspended' if user.get('account_status') == 'active' else 'active'
    db.update_user_status(user_id, new_status)
    admin_id = session.get('admin_user', {}).get('id')
    db.log_admin_action(admin_id, f"TOGGLE_LOGISTICS_STATUS_{new_status.upper()}", user_id, f"Admin updated status to {new_status}")
    flash(f"Logistics status for {user['email']} updated to {new_status}.", 'success')
    return redirect(url_for('admin_logistics'))


@app.route('/admin/reset_database', methods=['GET', 'POST'])
@admin_required
def admin_reset_database():
    if request.method == 'POST':
        db.reset_database()
        session.clear()
        flash('Database successfully reset and re-seeded with clean demo data!', 'success')
        return redirect(url_for('login'))
    return render_template('admin/reset_database.html', active_page='reset_db')


# --- LOGISTICS PORTAL ROUTES ---

@app.route('/logistics/dashboard')
@logistics_required
def logistics_dashboard():
    status_filter = request.args.get('status', 'ALL')
    search = request.args.get('search', '').strip()
    logistics_user = session.get('logistics_user', {})
    
    stats = db.get_logistics_dashboard_stats(logistics_user.get('id'))
    orders = db.get_logistics_orders(logistics_user.get('id'), status_filter=status_filter, search=search)
    
    return render_template(
        'logistics/dashboard.html',
        stats=stats,
        orders=orders,
        status_filter=status_filter,
        search=search,
        user=logistics_user
    )


@app.route('/logistics/order/<order_id>')
@logistics_required
def logistics_order_detail(order_id):
    order = db.get_logistics_order_by_id(order_id)
    if not order:
        flash('Order not found.', 'error')
        return redirect(url_for('logistics_dashboard'))
    
    history = db.get_order_status_history(order_id)
    current_status = order.get('logistics_status') or 'NONE'
    valid_transitions = db.VALID_LOGISTICS_TRANSITIONS.get(current_status, [])
    
    return render_template(
        'logistics/order_detail.html',
        order=order,
        history=history,
        audit_history=history,
        valid_transitions=valid_transitions,
        user=session.get('logistics_user', {})
    )


@app.route('/logistics/order/<order_id>/update_status', methods=['POST'], endpoint='update_logistics_order_status')
@app.route('/logistics/order/<order_id>/update_status_alt', methods=['POST'], endpoint='update_logistics_status')
@logistics_required
def update_logistics_order_status(order_id):
    next_status = request.form.get('next_status')
    notes = request.form.get('notes', '').strip()
    logistics_user = session.get('logistics_user', {})
    
    if not next_status:
        flash('Invalid status target.', 'error')
        return redirect(url_for('logistics_order_detail', order_id=order_id))
    
    success, msg, updated_order = db.update_logistics_order_status_atomic(
        order_id=order_id,
        next_status=next_status,
        updated_by_user_id=logistics_user.get('id'),
        updated_by_role='logistics',
        notes=notes
    )
    
    if success:
        flash(f'Status updated to {next_status} successfully!', 'success')
        # Non-blocking email milestone notification
        try:
            email_service.dispatch_logistics_milestone_emails(updated_order, next_status)
        except Exception as e:
            print(f"[!] Error triggering milestone emails for order {order_id}:", e)
    else:
        flash(msg, 'error')
        
    return redirect(url_for('logistics_order_detail', order_id=order_id))


# --- SETTINGS & LOGOUT ---


@app.route('/settings', methods=['GET', 'POST'])
def settings():
    user = session.get('farmer_user') or session.get('buyer_user') or session.get('admin_user') or session.get('logistics_user')
    if not user:
        return redirect(url_for('login'))
    
    fresh_user = db.get_user_by_id(user['id']) or user
    if user['role'] == 'farmer':
        session['farmer_user'] = fresh_user
    elif user['role'] == 'buyer':
        session['buyer_user'] = fresh_user
        
    return render_template('settings.html', session_user=fresh_user, active_role=user['role'])

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True)

