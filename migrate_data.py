import os
import json
from werkzeug.security import generate_password_hash
import db

DATA_DIR = '/tmp' if os.environ.get('VERCEL') else '.'
USERS_FILE = os.path.join(DATA_DIR, 'users.json')
CROPS_FILE = os.path.join(DATA_DIR, 'crops.json')
ORDERS_FILE = os.path.join(DATA_DIR, 'orders.json')

def load_json(file_path):
    if not os.path.exists(file_path):
        return []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return []

def run_migration():
    print("=== Starting CropSync Phase 1 Data Migration ===")
    db.init_db()
    
    # 1. Migrate Users & Profiles from users.json
    users = load_json(USERS_FILE)
    if not users and os.path.exists('users.json'):
        users = load_json('users.json')
        
    migrated_users = 0
    for u in users:
        existing = db.get_user_by_email(u['email'])
        if not existing:
            # Hash password securely
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

    # 2. Migrate Crops from crops.json
    crops = load_json(CROPS_FILE)
    if not crops and os.path.exists('crops.json'):
        crops = load_json('crops.json')
        
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

    # 3. Migrate Orders from orders.json
    orders = load_json(ORDERS_FILE)
    if not orders and os.path.exists('orders.json'):
        orders = load_json('orders.json')
        
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
    admin_email = os.environ.get('ADMIN_EMAIL', 'admin@cropsync.com').lower()
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
