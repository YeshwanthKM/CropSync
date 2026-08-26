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

import threading

_thread_local = threading.local()

def get_connection():
    if DB_URL:
        import psycopg2
        import psycopg2.extras
        
        conn = getattr(_thread_local, 'conn', None)
        if conn is not None and not conn.closed:
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                return conn, "postgres"
            except Exception:
                try:
                    conn.close()
                except Exception:
                    pass

        url = DB_URL
        if 'sslmode' not in url.lower():
            sep = '&' if '?' in url else '?'
            url = f"{url}{sep}sslmode=require"
        conn = psycopg2.connect(url, cursor_factory=psycopg2.extras.RealDictCursor, connect_timeout=5)
        conn.autocommit = True
        _thread_local.conn = conn
        return conn, "postgres"
    else:
        # Fallback to local SQLite database
        data_dir = '/tmp' if os.environ.get('VERCEL') else '.'
        db_path = os.path.join(data_dir, 'cropsync.db')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn, "sqlite"


def init_db():
    try:
        conn, db_type = get_connection()
    except Exception as e:
        print("[!] Connection error during init_db:", e)
        return
    try:
        cursor = conn.cursor()
        if db_type == "postgres":
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT CHECK (role IN ('farmer', 'buyer', 'admin')) NOT NULL,
                    account_status TEXT CHECK (account_status IN ('pending', 'active', 'suspended')) DEFAULT 'pending' NOT NULL,
                    suspension_reason TEXT,
                    email_verified BOOLEAN DEFAULT FALSE NOT NULL,
                    email_verified_at TIMESTAMP WITH TIME ZONE,
                    phone_verified BOOLEAN DEFAULT FALSE NOT NULL,
                    phone_verified_at TIMESTAMP WITH TIME ZONE,
                    otp_hash TEXT,
                    otp_expires_at TIMESTAMP WITH TIME ZONE,
                    otp_attempts INTEGER DEFAULT 0,
                    otp_last_sent_at TIMESTAMP WITH TIME ZONE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
                );
                ALTER TABLE users DROP CONSTRAINT IF EXISTS users_account_status_check;
                ALTER TABLE users ADD CONSTRAINT users_account_status_check CHECK (account_status IN ('pending', 'active', 'suspended'));
                ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT FALSE;
                ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified_at TIMESTAMP WITH TIME ZONE;
                ALTER TABLE users ADD COLUMN IF NOT EXISTS phone_verified BOOLEAN DEFAULT FALSE;
                ALTER TABLE users ADD COLUMN IF NOT EXISTS phone_verified_at TIMESTAMP WITH TIME ZONE;
                ALTER TABLE users ADD COLUMN IF NOT EXISTS otp_hash TEXT;
                ALTER TABLE users ADD COLUMN IF NOT EXISTS otp_expires_at TIMESTAMP WITH TIME ZONE;
                ALTER TABLE users ADD COLUMN IF NOT EXISTS otp_attempts INTEGER DEFAULT 0;
                ALTER TABLE users ADD COLUMN IF NOT EXISTS otp_last_sent_at TIMESTAMP WITH TIME ZONE;


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
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    admin_id UUID REFERENCES users(id) ON DELETE SET NULL,
                    action TEXT NOT NULL,
                    target_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
                    reason TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
                );
            """)
        else:
            cursor.executescript("""
                CREATE TABLE IF NOT EXISTS users_v2 (
                    id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT CHECK (role IN ('farmer', 'buyer', 'admin')) NOT NULL,
                    account_status TEXT CHECK (account_status IN ('pending', 'active', 'suspended')) DEFAULT 'pending' NOT NULL,
                    suspension_reason TEXT,
                    email_verified INTEGER DEFAULT 0,
                    email_verified_at TEXT,
                    phone_verified INTEGER DEFAULT 0,
                    phone_verified_at TEXT,
                    otp_hash TEXT,
                    otp_expires_at TEXT,
                    otp_attempts INTEGER DEFAULT 0,
                    otp_last_sent_at TEXT,
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
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id TEXT PRIMARY KEY,
                    admin_id TEXT,
                    action TEXT NOT NULL,
                    target_user_id TEXT,
                    reason TEXT,
                    created_at TEXT NOT NULL
                );
            """)
            try:
                cursor.execute("SELECT count(*) FROM users")
                # Migrate existing users to users_v2 if users table exists
                cursor.execute("""
                    INSERT OR IGNORE INTO users_v2 (id, email, password_hash, role, account_status, suspension_reason, created_at, updated_at)
                    SELECT id, email, password_hash, role, account_status, suspension_reason, created_at, updated_at FROM users
                """)
                cursor.execute("DROP TABLE users")
                cursor.execute("ALTER TABLE users_v2 RENAME TO users")
            except Exception:
                try:
                    cursor.execute("ALTER TABLE users_v2 RENAME TO users")
                except Exception:
                    pass
            conn.commit()

    except Exception as e:
        print("[!] Error executing DDL in init_db:", e)
    finally:
        try: conn.close()
        except: pass


def _dict_row(row):
    if row is None:
        return None
    d = dict(row) if not isinstance(row, dict) else row.copy()
    for k, v in list(d.items()):
        if isinstance(v, (datetime, uuid.UUID)):
            d[k] = str(v)
    return d


# --- USER FUNCTIONS ---

def get_user_by_email(email):
    try:
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
    except Exception as e:
        print(f"[!] Error in get_user_by_email({email}):", e)
        return None

def get_user_by_id(user_id):
    try:
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
    except Exception as e:
        print(f"[!] Error in get_user_by_id({user_id}):", e)
        return None

SEED_USERS = [
    {"id": "f1", "name": "Farmer 1", "email": "farmer1@gmail.com", "role": "farmer", "phone": "9876543210", "address": "Village A, State X", "location": "Coimbatore", "account_status": "active", "email_verified": True, "phone_verified": True},
    {"id": "f2", "name": "Farmer 2", "email": "farmer2@gmail.com", "role": "farmer", "phone": "9876543211", "address": "Village B, State Y", "location": "Madurai", "account_status": "active", "email_verified": True, "phone_verified": True},
    {"id": "f3", "name": "Farmer 3", "email": "farmer3@gmail.com", "role": "farmer", "phone": "9876543212", "address": "Village C, State Z", "location": "Salem", "account_status": "active", "email_verified": True, "phone_verified": True},
    {"id": "f4", "name": "Farmer 4", "email": "farmer4@gmail.com", "role": "farmer", "phone": "9876543213", "address": "Village D, State W", "location": "Erode", "account_status": "active", "email_verified": True, "phone_verified": True},
    {"id": "b1", "name": "Buyer 1", "email": "buyer1@gmail.com", "role": "buyer", "phone": "8876543210", "address": "City X, State A", "location": "Chennai", "account_status": "active", "email_verified": True, "phone_verified": True},
    {"id": "b2", "name": "Buyer 2", "email": "buyer2@gmail.com", "role": "buyer", "phone": "8876543211", "address": "City Y, State B", "location": "Bangalore", "account_status": "active", "email_verified": True, "phone_verified": True},
    {"id": "b3", "name": "Buyer 3", "email": "buyer3@gmail.com", "role": "buyer", "phone": "8876543212", "address": "City Z, State C", "location": "Trichy", "account_status": "active", "email_verified": True, "phone_verified": True},
    {"id": "b4", "name": "Buyer 4", "email": "buyer4@gmail.com", "role": "buyer", "phone": "8876543213", "address": "City W, State D", "location": "Nellai", "account_status": "active", "email_verified": True, "phone_verified": True},
]

def create_user(email, password_hash, role, name="User", phone="", address="", location="", organization="", user_id=None, status="pending", email_verified=False, phone_verified=False):
    conn, db_type = get_connection()
    try:
        cursor = conn.cursor()
        uid = str(user_id) if user_id else str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        ph = "%s" if db_type == "postgres" else "?"
        if db_type == "postgres":
            user_sql = """
                INSERT INTO users (id, email, password_hash, role, account_status, email_verified, phone_verified)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (email) DO UPDATE SET 
                    password_hash = EXCLUDED.password_hash,
                    account_status = EXCLUDED.account_status,
                    email_verified = EXCLUDED.email_verified,
                    phone_verified = EXCLUDED.phone_verified
            """
            cursor.execute(user_sql, (uid, email.lower().strip(), password_hash, role, status, email_verified, phone_verified))
            
            if role == 'farmer':
                prof_sql = """
                    INSERT INTO farmer_profiles (user_id, name, phone, address, location)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (user_id) DO UPDATE SET name = EXCLUDED.name, phone = EXCLUDED.phone, location = EXCLUDED.location
                """
                cursor.execute(prof_sql, (uid, name, phone, address, location))
            elif role == 'buyer':
                prof_sql = """
                    INSERT INTO buyer_profiles (user_id, name, phone, organization, address, location)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (user_id) DO UPDATE SET name = EXCLUDED.name, phone = EXCLUDED.phone, organization = EXCLUDED.organization, location = EXCLUDED.location
                """
                cursor.execute(prof_sql, (uid, name, phone, organization, address, location))
        else:
            user_sql = """
                INSERT OR REPLACE INTO users (id, email, password_hash, role, account_status, email_verified, phone_verified, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            cursor.execute(user_sql, (uid, email.lower().strip(), password_hash, role, status, 1 if email_verified else 0, 1 if phone_verified else 0, now, now))
            
            if role == 'farmer':
                prof_sql = """
                    INSERT OR REPLACE INTO farmer_profiles (id, user_id, name, phone, address, location, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """
                cursor.execute(prof_sql, (str(uuid.uuid4()), uid, name, phone, address, location, now, now))
            elif role == 'buyer':
                prof_sql = """
                    INSERT OR REPLACE INTO buyer_profiles (id, user_id, name, phone, organization, address, location, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                cursor.execute(prof_sql, (str(uuid.uuid4()), uid, name, phone, organization, address, location, now, now))
            conn.commit()
        return uid
    except Exception as e:
        print("[!] Error in create_user:", e)
        raise e
    finally:
        conn.close()

def update_email_verified(user_id, verified=True):
    conn, db_type = get_connection()
    try:
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat()
        ph = "%s" if db_type == "postgres" else "?"
        if db_type == "postgres":
            sql = f"""
                UPDATE users
                SET email_verified = {ph}, email_verified_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                WHERE id = {ph}
            """
        else:
            sql = f"""
                UPDATE users
                SET email_verified = {ph}, email_verified_at = {ph}, updated_at = {ph}
                WHERE id = {ph}
            """
        if db_type == "postgres":
            cursor.execute(sql, (verified, str(user_id)))
        else:
            cursor.execute(sql, (1 if verified else 0, now, now, str(user_id)))
            conn.commit()
    finally:
        conn.close()

def set_phone_otp(user_id, otp_hash, expires_at_iso):
    conn, db_type = get_connection()
    try:
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat()
        ph = "%s" if db_type == "postgres" else "?"
        sql = f"""
            UPDATE users
            SET otp_hash = {ph}, otp_expires_at = {ph}, otp_attempts = 0, otp_last_sent_at = {ph}, updated_at = {ph}
            WHERE id = {ph}
        """
        cursor.execute(sql, (otp_hash, expires_at_iso, now, now, str(user_id)))
        if db_type == "sqlite":
            conn.commit()
    finally:
        conn.close()

def increment_otp_attempts(user_id):
    conn, db_type = get_connection()
    try:
        cursor = conn.cursor()
        ph = "%s" if db_type == "postgres" else "?"
        sql = f"UPDATE users SET otp_attempts = COALESCE(otp_attempts, 0) + 1 WHERE id = {ph}"
        cursor.execute(sql, (str(user_id),))
        if db_type == "sqlite":
            conn.commit()
    finally:
        conn.close()

def update_phone_verified(user_id, verified=True):
    conn, db_type = get_connection()
    try:
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat()
        ph = "%s" if db_type == "postgres" else "?"
        if db_type == "postgres":
            sql = f"""
                UPDATE users
                SET phone_verified = {ph}, phone_verified_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                WHERE id = {ph}
            """
            cursor.execute(sql, (verified, str(user_id)))
        else:
            sql = f"""
                UPDATE users
                SET phone_verified = {ph}, phone_verified_at = {ph}, updated_at = {ph}
                WHERE id = {ph}
            """
            cursor.execute(sql, (1 if verified else 0, now, now, str(user_id)))
            conn.commit()
    finally:
        conn.close()

def log_admin_action(admin_id, action, target_user_id, reason=None):
    conn, db_type = get_connection()
    try:
        cursor = conn.cursor()
        ph = "%s" if db_type == "postgres" else "?"
        uid = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        if db_type == "postgres":
            sql = """
                INSERT INTO audit_logs (id, admin_id, action, target_user_id, reason)
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (uid, str(admin_id) if admin_id else None, action, str(target_user_id) if target_user_id else None, reason))
        else:
            sql = """
                INSERT INTO audit_logs (id, admin_id, action, target_user_id, reason, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """
            cursor.execute(sql, (uid, str(admin_id) if admin_id else None, action, str(target_user_id) if target_user_id else None, reason, now))
            conn.commit()
    except Exception as e:
        print("[!] Audit logging error:", e)
    finally:
        conn.close()

def get_audit_logs(limit=50):
    try:
        conn, db_type = get_connection()
        try:
            cursor = conn.cursor()
            ph = "%s" if db_type == "postgres" else "?"
            sql = f"""
                SELECT a.*, u.email as admin_email
                FROM audit_logs a
                LEFT JOIN users u ON a.admin_id = u.id
                ORDER BY a.created_at DESC
                LIMIT {ph}
            """
            cursor.execute(sql, (limit,))
            rows = cursor.fetchall()
            return [_dict_row(r) for r in rows]
        finally:
            conn.close()
    except Exception as e:
        print("[!] Error in get_audit_logs:", e)
        return []


def delete_user(user_id):
    conn, db_type = get_connection()
    try:
        cursor = conn.cursor()
        ph = "%s" if db_type == "postgres" else "?"
        cursor.execute(f"DELETE FROM farmer_profiles WHERE user_id = {ph}", (str(user_id),))
        cursor.execute(f"DELETE FROM buyer_profiles WHERE user_id = {ph}", (str(user_id),))
        cursor.execute(f"DELETE FROM crops WHERE farmer_id = {ph}", (str(user_id),))
        cursor.execute(f"DELETE FROM orders WHERE buyer_id = {ph} OR farmer_id = {ph}", (str(user_id), str(user_id)))
        cursor.execute(f"DELETE FROM users WHERE id = {ph}", (str(user_id),))
        if db_type == "sqlite":
            conn.commit()
    finally:
        conn.close()

def update_user_status(user_id, status, reason=None):
    if status == 'suspended':
        delete_user(user_id)
        return

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

def ensure_seed_users():
    try:
        from werkzeug.security import generate_password_hash
        for u in SEED_USERS:
            try:
                existing = get_user_by_email(u['email'])
                if not existing:
                    pwd_hash = generate_password_hash(u.get('password', 'farmer123'), method='pbkdf2:sha256')
                    create_user(
                        email=u['email'],
                        password_hash=pwd_hash,
                        role=u.get('role', 'farmer'),
                        name=u.get('name', 'User'),
                        phone=u.get('phone', ''),
                        address=u.get('address', ''),
                        location=u.get('location', ''),
                        user_id=u.get('id')
                    )
            except Exception:
                pass
    except Exception as e:
        print("[!] Error in ensure_seed_users:", e)

# --- ADMIN MANAGEMENT FUNCTIONS ---

def get_all_farmers(search=None, status_filter=None):
    try:
        ensure_seed_users()
        conn, db_type = get_connection()
        try:
            cursor = conn.cursor()
            ph = "%s" if db_type == "postgres" else "?"
            where_clauses = ["u.role = 'farmer'"]
            params = []
            
            if search:
                s_param = f"%{search.lower()}%"
                where_clauses.append(f"(LOWER(COALESCE(fp.name, '')) LIKE {ph} OR LOWER(u.email) LIKE {ph} OR LOWER(COALESCE(fp.location, '')) LIKE {ph})")
                params.extend([s_param, s_param, s_param])
                
            if status_filter == 'verified':
                where_clauses.append("u.account_status = 'active'")
            elif status_filter == 'pending':
                where_clauses.append("u.account_status = 'pending'")
            elif status_filter == 'suspended':
                where_clauses.append("u.account_status = 'suspended'")

            where_sql = " AND ".join(where_clauses)
            sql = f"""
                SELECT u.id, u.email, u.account_status, u.suspension_reason, u.created_at,
                       COALESCE(u.email_verified, FALSE) as email_verified,
                       COALESCE(u.phone_verified, FALSE) as phone_verified,
                       COALESCE(fp.name, 'Farmer') as name, 
                       COALESCE(fp.phone, 'N/A') as phone, 
                       COALESCE(fp.address, 'N/A') as address, 
                       COALESCE(fp.location, 'N/A') as location
                FROM users u
                LEFT JOIN farmer_profiles fp ON u.id = fp.user_id
                WHERE {where_sql}
                ORDER BY u.created_at DESC
            """
            cursor.execute(sql, tuple(params))
            rows = cursor.fetchall()
            res = [_dict_row(r) for r in rows]
            if not res and not search and not status_filter:
                res = [u for u in SEED_USERS if u['role'] == 'farmer']
            return res
        finally:
            conn.close()
    except Exception as e:
        print("[!] Error in get_all_farmers:", e)
        return [u for u in SEED_USERS if u['role'] == 'farmer']

def get_all_buyers(search=None, status_filter=None):
    try:
        ensure_seed_users()
        conn, db_type = get_connection()
        try:
            cursor = conn.cursor()
            ph = "%s" if db_type == "postgres" else "?"
            where_clauses = ["u.role = 'buyer'"]
            params = []
            
            if search:
                s_param = f"%{search.lower()}%"
                where_clauses.append(f"(LOWER(COALESCE(bp.name, '')) LIKE {ph} OR LOWER(u.email) LIKE {ph} OR LOWER(COALESCE(bp.location, '')) LIKE {ph})")
                params.extend([s_param, s_param, s_param])

            if status_filter == 'verified':
                where_clauses.append("u.account_status = 'active'")
            elif status_filter == 'pending':
                where_clauses.append("u.account_status = 'pending'")
            elif status_filter == 'suspended':
                where_clauses.append("u.account_status = 'suspended'")

            where_sql = " AND ".join(where_clauses)
            sql = f"""
                SELECT u.id, u.email, u.account_status, u.suspension_reason, u.created_at,
                       COALESCE(u.email_verified, FALSE) as email_verified,
                       COALESCE(u.phone_verified, FALSE) as phone_verified,
                       COALESCE(bp.name, 'Buyer') as name, 
                       COALESCE(bp.phone, 'N/A') as phone, 
                       COALESCE(bp.organization, 'N/A') as organization,
                       COALESCE(bp.address, 'N/A') as address, 
                       COALESCE(bp.location, 'N/A') as location
                FROM users u
                LEFT JOIN buyer_profiles bp ON u.id = bp.user_id
                WHERE {where_sql}
                ORDER BY u.created_at DESC
            """
            cursor.execute(sql, tuple(params))
            rows = cursor.fetchall()
            res = [_dict_row(r) for r in rows]
            if not res and not search and not status_filter:
                res = [u for u in SEED_USERS if u['role'] == 'buyer']
            return res
        finally:
            conn.close()
    except Exception as e:
        print("[!] Error in get_all_buyers:", e)
        return [u for u in SEED_USERS if u['role'] == 'buyer']


def get_admin_stats():
    try:
        ensure_seed_users()
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

            fc = _c(farmers_count)
            bc = _c(buyers_count)
            
            return {
                'total_farmers': fc,
                'total_buyers': bc,
                'active_listings': _c(listings_count),
                'active_orders': _c(orders_count),
                'suspended_accounts': _c(suspended_count)
            }
        finally:
            conn.close()
    except Exception as e:
        print("[!] Error in get_admin_stats:", e)
        return {'total_farmers': 4, 'total_buyers': 4, 'active_listings': 0, 'active_orders': 0, 'suspended_accounts': 0}



# --- CROPS FUNCTIONS ---

def get_crops(farmer_id=None, search=None, location=None):
    try:
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
    except Exception as e:
        print("[!] Error in get_crops:", e)
        return []

def get_crop_by_id(crop_id):
    try:
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
    except Exception as e:
        print(f"[!] Error in get_crop_by_id({crop_id}):", e)
        return None

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
    try:
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
    except Exception as e:
        print("[!] Error in get_orders_for_farmer:", e)
        return []

def get_orders_for_buyer(buyer_id):
    try:
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
    except Exception as e:
        print("[!] Error in get_orders_for_buyer:", e)
        return []

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
