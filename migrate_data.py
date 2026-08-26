import os
import json
from werkzeug.security import generate_password_hash
import db

DATA_DIR = '/tmp' if os.environ.get('VERCEL') else '.'
USERS_FILE = os.path.join(DATA_DIR, 'users.json')
CROPS_FILE = os.path.join(DATA_DIR, 'crops.json')
ORDERS_FILE = os.path.join(DATA_DIR, 'orders.json')

SEED_USERS = [
    {"id": "f1", "name": "Farmer 1", "email": "farmer1@gmail.com", "password": "farmer123", "role": "farmer", "phone": "9876543210", "address": "Village A, State X", "location": "Coimbatore"},
    {"id": "f2", "name": "Farmer 2", "email": "farmer2@gmail.com", "password": "farmer123", "role": "farmer", "phone": "9876543211", "address": "Village B, State Y", "location": "Madurai"},
    {"id": "f3", "name": "Farmer 3", "email": "farmer3@gmail.com", "password": "farmer123", "role": "farmer", "phone": "9876543212", "address": "Village C, State Z", "location": "Salem"},
    {"id": "f4", "name": "Farmer 4", "email": "farmer4@gmail.com", "password": "farmer123", "role": "farmer", "phone": "9876543213", "address": "Village D, State W", "location": "Erode"},
    {"id": "b1", "name": "Buyer 1", "email": "buyer1@gmail.com", "password": "buyer123", "role": "buyer", "phone": "8876543210", "address": "City X, State A", "location": "Chennai"},
    {"id": "b2", "name": "Buyer 2", "email": "buyer2@gmail.com", "password": "buyer123", "role": "buyer", "phone": "8876543211", "address": "City Y, State B", "location": "Bangalore"},
    {"id": "b3", "name": "Buyer 3", "email": "buyer3@gmail.com", "password": "buyer123", "role": "buyer", "phone": "8876543212", "address": "City Z, State C", "location": "Trichy"},
    {"id": "b4", "name": "Buyer 4", "email": "buyer4@gmail.com", "password": "buyer123", "role": "buyer", "phone": "8876543213", "address": "City W, State D", "location": "Nellai"},
]

def load_json(file_path):
    # Try given path, then fallback to current working directory or absolute file location
    paths_to_try = [
        file_path,
        os.path.basename(file_path),
        os.path.join(os.path.dirname(__file__), os.path.basename(file_path))
    ]
    for p in paths_to_try:
        if os.path.exists(p):
            try:
                with open(p, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if data:
                        return data
            except Exception:
                pass
    return []

def run_migration():
    print("=== Starting CropSync Phase 1 Data Migration ===")
    try:
        db.init_db()
    except Exception as e:
        print("[!] DB init warning:", e)
    
    # 1. Migrate Users & Profiles
    users = load_json(USERS_FILE)
    if not users:
        users = SEED_USERS
        
    migrated_users = 0
    for u in users:
        existing = db.get_user_by_email(u['email'])
        if not existing:
            pwd_hash = generate_password_hash(u.get('password', 'farmer123'), method='pbkdf2:sha256')
            db.create_user(
                email=u['email'],
                password_hash=pwd_hash,
                role=u.get('role', 'farmer'),
                name=u.get('name', 'User'),
                phone=u.get('phone', ''),
                address=u.get('address', ''),
                location=u.get('location', ''),
                user_id=u.get('id')
            )
            migrated_users += 1
    print(f"[+] Migrated {migrated_users} users and profiles into database.")

    # 2. Migrate Crops
    crops = load_json(CROPS_FILE)
    migrated_crops = 0
    for c in crops:
        existing = db.get_crop_by_id(c['id'])
        if not existing:
            db.create_crop(
                farmer_id=c['farmer_id'],
                crop_name=c['crop_name'],
                quantity=c['quantity'],
                price_per_kg=c['price_per_kg'],
                location=c.get('location', 'Unknown'),
                crop_id=c.get('id')
            )
            migrated_crops += 1
    print(f"[+] Migrated {migrated_crops} crops into database.")

    # 3. Migrate Orders
    orders = load_json(ORDERS_FILE)
    migrated_orders = 0
    for o in orders:
        db.create_order(
            buyer_id=o['buyer_id'],
            farmer_id=o['farmer_id'],
            crop_id=o['crop_id'],
            crop_name=o.get('crop_name', 'Crop'),
            quantity=o['quantity'],
            total_price=o['total_price'],
            order_id=o.get('id')
        )
        migrated_orders += 1
    print(f"[+] Migrated {migrated_orders} orders into database.")

    # 4. Seed Initial Admin Account
    admin_email = os.environ.get('ADMIN_EMAIL', 'admin@cropsync.com').lower().strip()
    admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
    
    existing_admin = db.get_user_by_email(admin_email)
    if not existing_admin:
        admin_hash = generate_password_hash(admin_password, method='pbkdf2:sha256')
        db.create_user(
            email=admin_email,
            password_hash=admin_hash,
            role='admin',
            name='System Administrator'
        )
        print(f"[+] Created initial Admin account: {admin_email}")
    else:
        print(f"[*] Admin account ({admin_email}) already exists.")

    print("=== Data Migration Completed Successfully ===")

if __name__ == '__main__':
    run_migration()
