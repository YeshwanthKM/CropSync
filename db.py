import os
import sqlite3
import uuid
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables safely from local workspace .env if present
env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_path):
    load_dotenv(dotenv_path=env_path)

# Check for PostgreSQL connection URL across all common environment variable names
DB_URL = (
    os.environ.get('DATABASE_URL') or
    os.environ.get('SUPABASE_DB_URL') or
    os.environ.get('POSTGRES_URL') or
    os.environ.get('POSTGRES_PRISMA_URL') or
    os.environ.get('SUPABASE_DATABASE_URL')
)


def get_connection():
    if DB_URL:
        import psycopg2
        import psycopg2.extras
        url = DB_URL
        if 'sslmode' not in url.lower():
            sep = '&' if '?' in url else '?'
            url = f"{url}{sep}sslmode=require"
        conn = psycopg2.connect(url, cursor_factory=psycopg2.extras.RealDictCursor)
        conn.autocommit = True
        return conn, "postgres"
    else:
        # Fallback to local SQLite database
        data_dir = '/tmp' if os.environ.get('VERCEL') else '.'
        db_path = os.path.join(data_dir, 'cropsync.db')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn, "sqlite"


def init_db():
    conn, db_type = get_connection()
    try:
        cursor = conn.cursor()
        if db_type == "postgres":
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT CHECK (role IN ('farmer', 'buyer', 'admin')) NOT NULL,
                    account_status TEXT CHECK (account_status IN ('active', 'suspended')) DEFAULT 'active' NOT NULL,
                    suspension_reason TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
                );
                CREATE TABLE IF NOT EXISTS farmer_profiles (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID REFERENCES users(id) ON DELETE CASCADE UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    phone TEXT,
                    address TEXT,
                    location TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
                );
                CREATE TABLE IF NOT EXISTS buyer_profiles (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID REFERENCES users(id) ON DELETE CASCADE UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    phone TEXT,
                    organization TEXT,
                    address TEXT,
                    location TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
                );
                CREATE TABLE IF NOT EXISTS crops (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    farmer_id UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,
                    crop_name TEXT NOT NULL,
                    quantity NUMERIC NOT NULL,
                    price_per_kg NUMERIC NOT NULL,
                    location TEXT NOT NULL,
                    status TEXT DEFAULT 'available' CHECK (status IN ('available', 'sold', 'archived')) NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
                );
                CREATE TABLE IF NOT EXISTS orders (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    crop_id UUID REFERENCES crops(id) ON DELETE CASCADE NOT NULL,
                    buyer_id UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,
                    farmer_id UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,
                    crop_name TEXT NOT NULL,
                    quantity NUMERIC NOT NULL,
                    total_price NUMERIC NOT NULL,
                    status TEXT DEFAULT 'Pending' CHECK (status IN ('Pending', 'Accepted', 'Rejected', 'Cancelled')) NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
                );
            """)
        else:
            # SQLite DDL
            cursor.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT CHECK (role IN ('farmer', 'buyer', 'admin')) NOT NULL,
                    account_status TEXT CHECK (account_status IN ('active', 'suspended')) DEFAULT 'active' NOT NULL,
                    suspension_reason TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS farmer_profiles (
                    id TEXT PRIMARY KEY,
                    user_id TEXT REFERENCES users(id) ON DELETE CASCADE UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    phone TEXT,
                    address TEXT,
                    location TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS buyer_profiles (
                    id TEXT PRIMARY KEY,
                    user_id TEXT REFERENCES users(id) ON DELETE CASCADE UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    phone TEXT,
                    organization TEXT,
                    address TEXT,
                    location TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS crops (
                    id TEXT PRIMARY KEY,
                    farmer_id TEXT REFERENCES users(id) ON DELETE CASCADE NOT NULL,
                    crop_name TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    price_per_kg REAL NOT NULL,
                    location TEXT NOT NULL,
                    status TEXT DEFAULT 'available' CHECK (status IN ('available', 'sold', 'archived')) NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS orders (
                    id TEXT PRIMARY KEY,
                    crop_id TEXT REFERENCES crops(id) ON DELETE CASCADE NOT NULL,
                    buyer_id TEXT REFERENCES users(id) ON DELETE CASCADE NOT NULL,
                    farmer_id TEXT REFERENCES users(id) ON DELETE CASCADE NOT NULL,
                    crop_name TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    total_price REAL NOT NULL,
                    status TEXT DEFAULT 'Pending' CHECK (status IN ('Pending', 'Accepted', 'Rejected', 'Cancelled')) NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
            """)
            conn.commit()
    finally:
        conn.close()

def _dict_row(row):
    if row is None:
        return None
    if isinstance(row, dict):
        return row
    return dict(row)

# --- USER FUNCTIONS ---

def get_user_by_email(email):
    conn, db_type = get_connection()
    try:
        cursor = conn.cursor()
        query = """
            SELECT u.*, 
                   COALESCE(fp.name, bp.name, 'Admin') as name,
                   COALESCE(fp.phone, bp.phone) as phone,
                   COALESCE(fp.address, bp.address) as address,
                   COALESCE(fp.location, bp.location) as location,
                   bp.organization
            FROM users u
            LEFT JOIN farmer_profiles fp ON u.id = fp.user_id
            LEFT JOIN buyer_profiles bp ON u.id = bp.user_id
            WHERE LOWER(u.email) = LOWER(%s)
        """ if db_type == "postgres" else """
            SELECT u.*, 
                   COALESCE(fp.name, bp.name, 'Admin') as name,
                   COALESCE(fp.phone, bp.phone) as phone,
                   COALESCE(fp.address, bp.address) as address,
                   COALESCE(fp.location, bp.location) as location,
                   bp.organization
            FROM users u
            LEFT JOIN farmer_profiles fp ON u.id = fp.user_id
            LEFT JOIN buyer_profiles bp ON u.id = bp.user_id
            WHERE LOWER(u.email) = LOWER(?)
        """
        cursor.execute(query, (email,))
        row = cursor.fetchone()
        return _dict_row(row)
    finally:
        conn.close()

def get_user_by_id(user_id):
    conn, db_type = get_connection()
    try:
        cursor = conn.cursor()
        query = """
            SELECT u.*, 
                   COALESCE(fp.name, bp.name, 'Admin') as name,
                   COALESCE(fp.phone, bp.phone) as phone,
                   COALESCE(fp.address, bp.address) as address,
                   COALESCE(fp.location, bp.location) as location,
                   bp.organization
            FROM users u
            LEFT JOIN farmer_profiles fp ON u.id = fp.user_id
            LEFT JOIN buyer_profiles bp ON u.id = bp.user_id
            WHERE u.id = %s
        """ if db_type == "postgres" else """
            SELECT u.*, 
                   COALESCE(fp.name, bp.name, 'Admin') as name,
                   COALESCE(fp.phone, bp.phone) as phone,
                   COALESCE(fp.address, bp.address) as address,
                   COALESCE(fp.location, bp.location) as location,
                   bp.organization
            FROM users u
            LEFT JOIN farmer_profiles fp ON u.id = fp.user_id
            LEFT JOIN buyer_profiles bp ON u.id = bp.user_id
            WHERE u.id = ?
        """
        cursor.execute(query, (str(user_id),))
        row = cursor.fetchone()
        return _dict_row(row)
    finally:
        conn.close()

def create_user(email, password_hash, role, name="User", phone="", address="", location="", organization="", user_id=None, status="active"):
    conn, db_type = get_connection()
    try:
        cursor = conn.cursor()
        uid = str(user_id) if user_id else str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        ph = "%s" if db_type == "postgres" else "?"
        user_sql = f"""
            INSERT INTO users (id, email, password_hash, role, account_status, created_at, updated_at)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
        """
        cursor.execute(user_sql, (uid, email.lower(), password_hash, role, status, now, now))
        
        prof_id = str(uuid.uuid4())
        if role == 'farmer':
            prof_sql = f"""
                INSERT INTO farmer_profiles (id, user_id, name, phone, address, location, created_at, updated_at)
                VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
            """
            cursor.execute(prof_sql, (prof_id, uid, name, phone, address, location, now, now))
        elif role == 'buyer':
            prof_sql = f"""
                INSERT INTO buyer_profiles (id, user_id, name, phone, organization, address, location, created_at, updated_at)
                VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
            """
            cursor.execute(prof_sql, (prof_id, uid, name, phone, organization, address, location, now, now))

        if db_type == "sqlite":
            conn.commit()
        return uid
    finally:
        conn.close()

def update_user_status(user_id, status, reason=None):
    conn, db_type = get_connection()
    try:
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat()
        ph = "%s" if db_type == "postgres" else "?"
        sql = f"""
            UPDATE users
            SET account_status = {ph}, suspension_reason = {ph}, updated_at = {ph}
            WHERE id = {ph}
        """
        cursor.execute(sql, (status, reason, now, str(user_id)))
        if db_type == "sqlite":
            conn.commit()
    finally:
        conn.close()

def update_user_profile(user_id, name, phone="", address="", location="", organization=""):
    conn, db_type = get_connection()
    try:
        cursor = conn.cursor()
        user = get_user_by_id(user_id)
        if not user:
            return
        now = datetime.utcnow().isoformat()
        ph = "%s" if db_type == "postgres" else "?"
        if user['role'] == 'farmer':
            sql = f"""
                UPDATE farmer_profiles
                SET name = {ph}, phone = {ph}, address = {ph}, location = {ph}, updated_at = {ph}
                WHERE user_id = {ph}
            """
            cursor.execute(sql, (name, phone, address, location, now, str(user_id)))
        elif user['role'] == 'buyer':
            sql = f"""
                UPDATE buyer_profiles
                SET name = {ph}, phone = {ph}, organization = {ph}, address = {ph}, location = {ph}, updated_at = {ph}
                WHERE user_id = {ph}
            """
            cursor.execute(sql, (name, phone, organization, address, location, now, str(user_id)))
        if db_type == "sqlite":
            conn.commit()
    finally:
        conn.close()

# --- ADMIN MANAGEMENT FUNCTIONS ---

def get_all_farmers(search=None):
    conn, db_type = get_connection()
    try:
        cursor = conn.cursor()
        ph = "%s" if db_type == "postgres" else "?"
        if search:
            s_param = f"%{search.lower()}%"
            sql = f"""
                SELECT u.id, u.email, u.account_status, u.suspension_reason, u.created_at,
                       fp.name, fp.phone, fp.address, fp.location
                FROM users u
                JOIN farmer_profiles fp ON u.id = fp.user_id
                WHERE u.role = 'farmer'
                  AND (LOWER(fp.name) LIKE {ph} OR LOWER(u.email) LIKE {ph} OR LOWER(fp.location) LIKE {ph})
                ORDER BY u.created_at DESC
            """
            cursor.execute(sql, (s_param, s_param, s_param))
        else:
            sql = """
                SELECT u.id, u.email, u.account_status, u.suspension_reason, u.created_at,
                       fp.name, fp.phone, fp.address, fp.location
                FROM users u
                JOIN farmer_profiles fp ON u.id = fp.user_id
                WHERE u.role = 'farmer'
                ORDER BY u.created_at DESC
            """
            cursor.execute(sql)
        rows = cursor.fetchall()
        return [_dict_row(r) for r in rows]
    finally:
        conn.close()

def get_all_buyers(search=None):
    conn, db_type = get_connection()
    try:
        cursor = conn.cursor()
        ph = "%s" if db_type == "postgres" else "?"
        if search:
            s_param = f"%{search.lower()}%"
            sql = f"""
                SELECT u.id, u.email, u.account_status, u.suspension_reason, u.created_at,
                       bp.name, bp.phone, bp.organization, bp.address, bp.location
                FROM users u
                JOIN buyer_profiles bp ON u.id = bp.user_id
                WHERE u.role = 'buyer'
                  AND (LOWER(bp.name) LIKE {ph} OR LOWER(u.email) LIKE {ph} OR LOWER(bp.location) LIKE {ph})
                ORDER BY u.created_at DESC
            """
            cursor.execute(sql, (s_param, s_param, s_param))
        else:
            sql = """
                SELECT u.id, u.email, u.account_status, u.suspension_reason, u.created_at,
                       bp.name, bp.phone, bp.organization, bp.address, bp.location
                FROM users u
                JOIN buyer_profiles bp ON u.id = bp.user_id
                WHERE u.role = 'buyer'
                ORDER BY u.created_at DESC
            """
            cursor.execute(sql)
        rows = cursor.fetchall()
        return [_dict_row(r) for r in rows]
    finally:
        conn.close()

def get_admin_stats():
    conn, db_type = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM users WHERE role = 'farmer'")
        farmers_count = cursor.fetchone()
        
        cursor.execute("SELECT COUNT(*) as count FROM users WHERE role = 'buyer'")
        buyers_count = cursor.fetchone()
        
        cursor.execute("SELECT COUNT(*) as count FROM crops WHERE status = 'available'")
        listings_count = cursor.fetchone()
        
        cursor.execute("SELECT COUNT(*) as count FROM orders WHERE status = 'Pending'")
        orders_count = cursor.fetchone()
        
        cursor.execute("SELECT COUNT(*) as count FROM users WHERE account_status = 'suspended'")
        suspended_count = cursor.fetchone()

        def _c(val):
            if val is None: return 0
            if isinstance(val, dict): return val['count']
            try: return val[0]
            except: return 0

        return {
            'total_farmers': _c(farmers_count),
            'total_buyers': _c(buyers_count),
            'active_listings': _c(listings_count),
            'active_orders': _c(orders_count),
            'suspended_accounts': _c(suspended_count)
        }
    finally:
        conn.close()

# --- CROPS FUNCTIONS ---

def get_crops(farmer_id=None, search=None, location=None):
    conn, db_type = get_connection()
    try:
        cursor = conn.cursor()
        ph = "%s" if db_type == "postgres" else "?"
        query = """
            SELECT c.*, fp.name as farmer_name, fp.phone as farmer_phone
            FROM crops c
            JOIN farmer_profiles fp ON c.farmer_id = fp.user_id
            WHERE c.status = 'available'
        """
        params = []
        if farmer_id:
            query = """
                SELECT c.*, fp.name as farmer_name, fp.phone as farmer_phone
                FROM crops c
                JOIN farmer_profiles fp ON c.farmer_id = fp.user_id
                WHERE c.farmer_id = """ + ph + """ AND c.status = 'available'
            """
            params.append(str(farmer_id))
        else:
            if search:
                query += f" AND LOWER(c.crop_name) LIKE {ph}"
                params.append(f"%{search.lower()}%")
            if location:
                query += f" AND LOWER(c.location) LIKE {ph}"
                params.append(f"%{location.lower()}%")
                
        query += " ORDER BY c.created_at DESC"
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        return [_dict_row(r) for r in rows]
    finally:
        conn.close()

def get_crop_by_id(crop_id):
    conn, db_type = get_connection()
    try:
        cursor = conn.cursor()
        ph = "%s" if db_type == "postgres" else "?"
        sql = f"SELECT * FROM crops WHERE id = {ph}"
        cursor.execute(sql, (str(crop_id),))
        row = cursor.fetchone()
        return _dict_row(row)
    finally:
        conn.close()

def create_crop(farmer_id, crop_name, quantity, price_per_kg, location, crop_id=None):
    conn, db_type = get_connection()
    try:
        cursor = conn.cursor()
        cid = str(crop_id) if crop_id else str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        ph = "%s" if db_type == "postgres" else "?"
        sql = f"""
            INSERT INTO crops (id, farmer_id, crop_name, quantity, price_per_kg, location, status, created_at, updated_at)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, 'available', {ph}, {ph})
        """
        cursor.execute(sql, (cid, str(farmer_id), crop_name.lower(), float(quantity), float(price_per_kg), location, now, now))
        if db_type == "sqlite":
            conn.commit()
        return cid
    finally:
        conn.close()

def delete_crop(crop_id, farmer_id):
    conn, db_type = get_connection()
    try:
        cursor = conn.cursor()
        ph = "%s" if db_type == "postgres" else "?"
        sql = f"DELETE FROM crops WHERE id = {ph} AND farmer_id = {ph}"
        cursor.execute(sql, (str(crop_id), str(farmer_id)))
        if db_type == "sqlite":
            conn.commit()
    finally:
        conn.close()

def update_crop_quantity(crop_id, new_quantity):
    conn, db_type = get_connection()
    try:
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat()
        ph = "%s" if db_type == "postgres" else "?"
        status = 'sold' if new_quantity <= 0 else 'available'
        sql = f"UPDATE crops SET quantity = {ph}, status = {ph}, updated_at = {ph} WHERE id = {ph}"
        cursor.execute(sql, (float(new_quantity), status, now, str(crop_id)))
        if db_type == "sqlite":
            conn.commit()
    finally:
        conn.close()

# --- ORDERS FUNCTIONS ---

def get_orders_for_farmer(farmer_id):
    conn, db_type = get_connection()
    try:
        cursor = conn.cursor()
        ph = "%s" if db_type == "postgres" else "?"
        sql = f"""
            SELECT o.*, bp.name as buyer_name, bp.phone as buyer_phone
            FROM orders o
            JOIN buyer_profiles bp ON o.buyer_id = bp.user_id
            WHERE o.farmer_id = {ph}
            ORDER BY o.created_at DESC
        """
        cursor.execute(sql, (str(farmer_id),))
        rows = cursor.fetchall()
        return [_dict_row(r) for r in rows]
    finally:
        conn.close()

def get_orders_for_buyer(buyer_id):
    conn, db_type = get_connection()
    try:
        cursor = conn.cursor()
        ph = "%s" if db_type == "postgres" else "?"
        sql = f"""
            SELECT o.*, fp.name as farmer_name, fp.phone as farmer_phone
            FROM orders o
            JOIN farmer_profiles fp ON o.farmer_id = fp.user_id
            WHERE o.buyer_id = {ph}
            ORDER BY o.created_at DESC
        """
        cursor.execute(sql, (str(buyer_id),))
        rows = cursor.fetchall()
        return [_dict_row(r) for r in rows]
    finally:
        conn.close()

def create_order(buyer_id, farmer_id, crop_id, crop_name, quantity, total_price, order_id=None):
    conn, db_type = get_connection()
    try:
        cursor = conn.cursor()
        oid = str(order_id) if order_id else str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        ph = "%s" if db_type == "postgres" else "?"
        sql = f"""
            INSERT INTO orders (id, crop_id, buyer_id, farmer_id, crop_name, quantity, total_price, status, created_at, updated_at)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, 'Pending', {ph}, {ph})
        """
        cursor.execute(sql, (oid, str(crop_id), str(buyer_id), str(farmer_id), crop_name, float(quantity), float(total_price), now, now))
        if db_type == "sqlite":
            conn.commit()
        return oid
    finally:
        conn.close()

def update_order_status(order_id, status):
    conn, db_type = get_connection()
    try:
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat()
        ph = "%s" if db_type == "postgres" else "?"
        sql = f"UPDATE orders SET status = {ph}, updated_at = {ph} WHERE id = {ph}"
        cursor.execute(sql, (status, now, str(order_id)))
        if db_type == "sqlite":
            conn.commit()
    finally:
        conn.close()
