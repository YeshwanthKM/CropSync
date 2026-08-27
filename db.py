import os
import sqlite3
import uuid
from datetime import datetime, timedelta

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
        import psycopg2.extensions
        
        conn = getattr(_thread_local, 'conn', None)
        if conn is not None and not conn.closed:
            try:
                if getattr(conn, 'status', None) == psycopg2.extensions.STATUS_READY:
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
                ALTER TABLE users ADD COLUMN IF NOT EXISTS verification_token TEXT;



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
                    status TEXT DEFAULT 'Pending' CHECK (status IN ('Pending', 'Accepted', 'Rejected', 'Cancelled', 'Completed')) NOT NULL,
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
                CREATE TABLE IF NOT EXISTS government_msp (
                    crop_name TEXT PRIMARY KEY,
                    msp_price_per_kg NUMERIC NOT NULL,
                    msp_price_per_quintal NUMERIC,
                    category TEXT NOT NULL,
                    season TEXT NOT NULL,
                    effective_year INTEGER NOT NULL,
                    source TEXT DEFAULT 'Ministry of Agriculture & Farmers Welfare, Govt of India',
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
                );
                CREATE TABLE IF NOT EXISTS email_notifications (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    order_id UUID REFERENCES orders(id) ON DELETE CASCADE,
                    recipient_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
                    notification_type TEXT NOT NULL CHECK (notification_type IN ('NEW_ORDER', 'ORDER_ACCEPTED', 'ORDER_REJECTED', 'ORDER_COMPLETED')),
                    recipient_email TEXT NOT NULL,
                    status TEXT DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'SENT', 'FAILED')) NOT NULL,
                    error_message TEXT,
                    sent_at TIMESTAMP WITH TIME ZONE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
                );
            """)
            # Schema migrations for Postgres constraints
            try:
                cursor.execute("ALTER TABLE orders DROP CONSTRAINT IF EXISTS orders_status_check;")
                cursor.execute("ALTER TABLE orders ADD CONSTRAINT orders_status_check CHECK (status IN ('Pending', 'Accepted', 'Rejected', 'Cancelled', 'Completed'));")
            except Exception as e:
                print("[!] Warning updating orders_status_check constraint:", e)

            # Drop obsolete table if exists
            try:
                cursor.execute("DROP TABLE IF EXISTS crop_price_history")
            except Exception:
                pass

        else:
            cursor.executescript("""
                CREATE TABLE IF NOT EXISTS users (
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
                    verification_token TEXT,
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
                    status TEXT DEFAULT 'available' CHECK (status IN ('available', 'disabled', 'sold', 'archived')) NOT NULL,
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
                    status TEXT DEFAULT 'Pending' CHECK (status IN ('Pending', 'Accepted', 'Rejected', 'Cancelled', 'Completed')) NOT NULL,
                    payment_status TEXT DEFAULT 'pending' CHECK (payment_status IN ('pending', 'paid', 'failed', 'refunded')) NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id TEXT PRIMARY KEY,
                    admin_id TEXT REFERENCES users(id) ON DELETE SET NULL,
                    action TEXT NOT NULL,
                    target_user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
                    reason TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS government_msp (
                    crop_name TEXT PRIMARY KEY,
                    msp_price_per_kg REAL NOT NULL,
                    msp_price_per_quintal REAL,
                    category TEXT NOT NULL,
                    season TEXT NOT NULL,
                    effective_year INTEGER NOT NULL,
                    source TEXT DEFAULT 'Ministry of Agriculture & Farmers Welfare, Govt of India',
                    status TEXT DEFAULT 'active',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS email_notifications (
                    id TEXT PRIMARY KEY,
                    order_id TEXT REFERENCES orders(id) ON DELETE CASCADE,
                    recipient_user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
                    notification_type TEXT NOT NULL,
                    recipient_email TEXT NOT NULL,
                    status TEXT DEFAULT 'PENDING' NOT NULL,
                    error_message TEXT,
                    sent_at TEXT,
                    created_at TEXT NOT NULL
                );
                DROP TABLE IF EXISTS crop_price_history;
            """)


            try:
                cursor.execute("SELECT count(*) FROM users")
                cursor.execute("""
                    INSERT OR IGNORE INTO users_v2 (id, email, password_hash, role, account_status, suspension_reason, created_at, updated_at)
                    SELECT id, email, password_hash, role, account_status, suspension_reason, created_at, updated_at FROM users
                """)
                cols = ["email_verified INTEGER DEFAULT 0", "email_verified_at TEXT", "phone_verified INTEGER DEFAULT 0", "phone_verified_at TEXT", "otp_hash TEXT", "otp_expires_at TEXT", "otp_attempts INTEGER DEFAULT 0", "otp_last_sent_at TEXT", "verification_token TEXT"]
                for col in cols:
                    try:
                        cursor.execute(f"ALTER TABLE users_v2 ADD COLUMN {col}")
                    except Exception:
                        pass
            except Exception:
                pass

            # Add column migrations for existing tables if needed
            msp_cols = [
                "msp_price_per_quintal REAL",
                "source TEXT DEFAULT 'Ministry of Agriculture & Farmers Welfare, Govt of India'",
                "status TEXT DEFAULT 'active'",
                "updated_at TEXT"
            ]
            for mcol in msp_cols:
                try:
                    cursor.execute(f"ALTER TABLE government_msp ADD COLUMN {mcol}")
                except Exception:
                    pass

            if db_type == "postgres":
                try:
                    cursor.execute("ALTER TABLE orders DROP CONSTRAINT IF EXISTS orders_status_check")
                    cursor.execute("ALTER TABLE orders ADD CONSTRAINT orders_status_check CHECK (status IN ('Pending', 'Accepted', 'Rejected', 'Cancelled', 'Completed'))")
                except Exception:
                    pass
            else:
                try:
                    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='orders'")
                    row = cursor.fetchone()
                    if row and 'Completed' not in row[0]:
                        cursor.execute("PRAGMA foreign_keys=OFF")
                        cursor.execute("CREATE TABLE orders_new AS SELECT * FROM orders")
                        cursor.execute("DROP TABLE orders")
                        cursor.execute("""
                            CREATE TABLE orders (
                                id TEXT PRIMARY KEY,
                                crop_id TEXT REFERENCES crops(id) ON DELETE CASCADE NOT NULL,
                                buyer_id TEXT REFERENCES users(id) ON DELETE CASCADE NOT NULL,
                                farmer_id TEXT REFERENCES users(id) ON DELETE CASCADE NOT NULL,
                                crop_name TEXT NOT NULL,
                                quantity REAL NOT NULL,
                                total_price REAL NOT NULL,
                                status TEXT DEFAULT 'Pending' CHECK (status IN ('Pending', 'Accepted', 'Rejected', 'Cancelled', 'Completed')) NOT NULL,
                                payment_status TEXT DEFAULT 'pending' CHECK (payment_status IN ('pending', 'paid', 'failed', 'refunded')) NOT NULL,
                                created_at TEXT NOT NULL,
                                updated_at TEXT NOT NULL
                            )
                        """)
                        cursor.execute("INSERT INTO orders SELECT * FROM orders_new")
                        cursor.execute("DROP TABLE orders_new")
                        cursor.execute("PRAGMA foreign_keys=ON")
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

def _val(row, default=0):
    if row is None:
        return default
    if isinstance(row, dict):
        return list(row.values())[0] if row else default
    try:
        return row[0]
    except Exception:
        return default



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

def set_verification_token(user_id, token):
    conn, db_type = get_connection()
    try:
        cursor = conn.cursor()
        ph = "%s" if db_type == "postgres" else "?"
        sql = f"UPDATE users SET verification_token = {ph} WHERE id = {ph}"
        cursor.execute(sql, (token, str(user_id)))
        if db_type == "sqlite":
            conn.commit()
    finally:
        conn.close()

def get_user_by_verification_token(token):
    if not token:
        return None
    conn, db_type = get_connection()
    try:
        cursor = conn.cursor()
        ph = "%s" if db_type == "postgres" else "?"
        sql = f"SELECT * FROM users WHERE verification_token = {ph}"
        cursor.execute(sql, (token,))
        row = cursor.fetchone()
        return _dict_row(row)
    finally:
        conn.close()

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
        conn, db_type = get_connection()
        try:
            cursor = conn.cursor()
            ph = "%s" if db_type == "postgres" else "?"
            for u in SEED_USERS:
                try:
                    existing = get_user_by_email(u['email'])
                    if not existing:
                        pwd_hash = generate_password_hash(u.get('password', 'farmer123'), method='pbkdf2:sha256')
                        user_id = create_user(
                            email=u['email'],
                            password_hash=pwd_hash,
                            role=u.get('role', 'farmer'),
                            name=u.get('name', 'User'),
                            phone=u.get('phone', ''),
                            address=u.get('address', ''),
                            location=u.get('location', ''),
                            user_id=u.get('id'),
                            status='active',
                            email_verified=True,
                            phone_verified=True
                        )
                    cursor.execute(f"UPDATE users SET account_status = 'active', email_verified = 1, phone_verified = 1 WHERE LOWER(TRIM(email)) = LOWER(TRIM({ph}))", (u['email'],))
                except Exception:
                    pass
            conn.commit()
        finally:
            conn.close()
    except Exception as e:
        print("[!] Error in ensure_seed_users:", e)


# --- ADMIN MANAGEMENT FUNCTIONS ---

def get_all_farmers(search=None, status_filter=None):
    try:
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
        cursor.execute(sql, (cid, str(farmer_id), crop_name.strip().title(), float(quantity), float(price_per_kg), location.strip().title(), now, now))
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
        conn.commit()
    finally:
        conn.close()

def update_crop_quantity(crop_id, new_quantity):
    conn, db_type = get_connection()
    try:
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat()
        ph = "%s" if db_type == "postgres" else "?"
        status = 'sold' if float(new_quantity) <= 0 else 'available'
        sql = f"UPDATE crops SET quantity = {ph}, status = {ph}, updated_at = {ph} WHERE id = {ph}"
        cursor.execute(sql, (float(new_quantity), status, now, str(crop_id)))
        conn.commit()
    finally:
        conn.close()

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
                SELECT o.*, fp.name as farmer_name, fp.phone as farmer_phone, u.email as farmer_email
                FROM orders o
                JOIN users u ON o.farmer_id = u.id
                LEFT JOIN farmer_profiles fp ON o.farmer_id = fp.user_id
                WHERE o.buyer_id = {ph}
                ORDER BY o.created_at DESC
            """
            cursor.execute(sql, (str(buyer_id),))
            rows = cursor.fetchall()
            orders = [_dict_row(r) for r in rows]
            # Server-Side Privacy Rule: Mask farmer phone and email unless order status is Accepted or Completed
            for o in orders:
                if o.get('status') not in ('Accepted', 'Completed'):
                    o['farmer_phone'] = None
                    o['farmer_email'] = None
            return orders
        finally:
            conn.close()
    except Exception as e:
        print("[!] Error in get_orders_for_buyer:", e)
        return []

# --- PHASE 4 EMAIL NOTIFICATIONS LOG & ORDER COMPLETION SERVICES ---

def log_email_notification(order_id, recipient_user_id, notification_type, recipient_email, status='PENDING', error_message=None):
    conn, db_type = get_connection()
    try:
        cursor = conn.cursor()
        nid = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        ph = "%s" if db_type == "postgres" else "?"
        sent_at = now if status == 'SENT' else None
        sql = f"""
            INSERT INTO email_notifications (id, order_id, recipient_user_id, notification_type, recipient_email, status, error_message, sent_at, created_at)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
        """
        cursor.execute(sql, (
            nid,
            str(order_id) if order_id else None,
            str(recipient_user_id) if recipient_user_id else None,
            notification_type,
            recipient_email,
            status,
            error_message,
            sent_at,
            now
        ))
        conn.commit()
        return nid
    except Exception as e:
        print("[!] Error logging email notification:", e)
        return None
    finally:
        conn.close()

def get_email_notifications_for_order(order_id):
    conn, db_type = get_connection()
    try:
        cursor = conn.cursor()
        ph = "%s" if db_type == "postgres" else "?"
        sql = f"SELECT * FROM email_notifications WHERE order_id = {ph} ORDER BY created_at DESC"
        cursor.execute(sql, (str(order_id),))
        rows = cursor.fetchall()
        return [_dict_row(r) for r in rows]
    except Exception as e:
        print(f"[!] Error in get_email_notifications_for_order({order_id}):", e)
        return []
    finally:
        conn.close()

def get_all_email_notifications_admin():
    conn, db_type = get_connection()
    try:
        cursor = conn.cursor()
        sql = "SELECT * FROM email_notifications ORDER BY created_at DESC"
        cursor.execute(sql)
        rows = cursor.fetchall()
        return [_dict_row(r) for r in rows]
    except Exception as e:
        print("[!] Error in get_all_email_notifications_admin:", e)
        return []
    finally:
        conn.close()

def complete_order_atomic(order_id, user_id, role):
    conn, db_type = get_connection()
    try:
        cursor = conn.cursor()
        ph = "%s" if db_type == "postgres" else "?"
        now = datetime.utcnow().isoformat()
        
        # 1. Fetch order
        sql_o = f"SELECT * FROM orders WHERE id = {ph}"
        cursor.execute(sql_o, (str(order_id),))
        order_row = cursor.fetchone()
        order = _dict_row(order_row)
        if not order:
            return False, "Order not found."

        # Check authorization
        if role == 'farmer' and str(order['farmer_id']) != str(user_id):
            return False, "Unauthorized action."
        elif role == 'buyer' and str(order['buyer_id']) != str(user_id):
            return False, "Unauthorized action."
        elif role not in ('farmer', 'buyer', 'admin'):
            return False, "Unauthorized role."

        # Duplicate Protection
        if order['status'] == 'Completed':
            return False, "Order is already completed."
        elif order['status'] != 'Accepted':
            return False, f"Cannot complete an order with status '{order['status']}'."

        # Update order status to Completed
        sql_u = f"UPDATE orders SET status = 'Completed', updated_at = {ph} WHERE id = {ph}"
        cursor.execute(sql_u, (now, str(order_id)))
        conn.commit()
        return True, "Order successfully marked as Completed."
    except Exception as e:
        print("[!] Error in complete_order_atomic:", e)
        try: conn.rollback()
        except: pass
        return False, f"Server error: {e}"
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
        conn.commit()
    finally:
        conn.close()



def accept_order_atomic(order_id, farmer_id):
    conn, db_type = get_connection()
    try:
        cursor = conn.cursor()
        ph = "%s" if db_type == "postgres" else "?"
        now = datetime.utcnow().isoformat()
        
        # 1. Fetch order
        sql_o = f"SELECT * FROM orders WHERE id = {ph}"
        cursor.execute(sql_o, (str(order_id),))
        order_row = cursor.fetchone()
        order = _dict_row(order_row)
        if not order:
            return False, "Order not found."

        if str(order['farmer_id']) != str(farmer_id):
            return False, "Unauthorized action."

        if order['status'] == 'Accepted':
            return False, "Order is already accepted."
        elif order['status'] != 'Pending':
            return False, f"Order is not pending (current status: {order['status']})."
            
        # 2. Fetch crop listing
        sql_c = f"SELECT * FROM crops WHERE id = {ph}"
        cursor.execute(sql_c, (str(order['crop_id']),))
        crop_row = cursor.fetchone()
        crop = _dict_row(crop_row)
        if not crop:
            return False, "Crop listing no longer exists."

        curr_qty = float(crop['quantity'])
        order_qty = float(order['quantity'])

        if curr_qty < order_qty:
            return False, f"Insufficient stock: Available {curr_qty} kg, requested {order_qty} kg."

        # 3. Update stock and crop status
        new_qty = curr_qty - order_qty

        new_crop_status = 'sold' if new_qty == 0 else crop['status']

        sql_u_crop = f"UPDATE crops SET quantity = {ph}, status = {ph}, updated_at = {ph} WHERE id = {ph}"
        cursor.execute(sql_u_crop, (new_qty, new_crop_status, now, str(crop['id'])))

        # 4. Update order status to Accepted
        sql_u_order = f"UPDATE orders SET status = 'Accepted', updated_at = {ph} WHERE id = {ph}"
        cursor.execute(sql_u_order, (now, str(order_id)))

        conn.commit()
        return True, "Order accepted and stock updated."
    except Exception as e:
        print("[!] Error in accept_order_atomic:", e)
        try: conn.rollback()
        except: pass
        return False, f"Server error: {e}"
    finally:
        conn.close()

# --- PHASE 3 OFFICIAL MSP REFERENCE SERVICES ---

SEED_GOVT_MSP = [
    ("Rice", 21.83, 2183.0, "Cereals", "Kharif", 2025),
    ("Wheat", 22.75, 2275.0, "Cereals", "Rabi", 2025),
    ("Maize", 20.90, 2090.0, "Coarse Cereals", "Kharif", 2025),
    ("Ragi", 38.46, 3846.0, "Coarse Cereals", "Kharif", 2025),
    ("Bajra", 25.00, 2500.0, "Coarse Cereals", "Kharif", 2025),
    ("Tur", 70.00, 7000.0, "Pulses", "Kharif", 2025),
    ("Moong", 85.58, 8558.0, "Pulses", "Kharif", 2025),
    ("Urad", 69.50, 6950.0, "Pulses", "Kharif", 2025),
    ("Groundnut", 63.77, 6377.0, "Oilseeds", "Kharif", 2025),
    ("Sunflower", 67.60, 6760.0, "Oilseeds", "Kharif", 2025),
    ("Soyabean", 46.00, 4600.0, "Oilseeds", "Kharif", 2025),
    ("Cotton", 66.20, 6620.0, "Commercial", "Kharif", 2025)
]

_msp_seeded = False

def seed_government_msp_data(force=False):
    global _msp_seeded
    if _msp_seeded and not force:
        return
    conn, db_type = get_connection()
    try:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT count(*) FROM government_msp")
            count = _val(cursor.fetchone(), 0)
            if count >= 12 and not force:
                _msp_seeded = True
                return
        except Exception:
            pass

        now = datetime.utcnow().isoformat()
        for crop, msp_kg, msp_q, cat, season, yr in SEED_GOVT_MSP:
            if db_type == "postgres":
                sql = """
                    INSERT INTO government_msp (crop_name, msp_price_per_kg, msp_price_per_quintal, category, season, effective_year, source, status, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, 'Ministry of Agriculture & Farmers Welfare, Govt of India', 'active', %s, %s)
                    ON CONFLICT (crop_name) DO UPDATE SET 
                        msp_price_per_kg = EXCLUDED.msp_price_per_kg,
                        msp_price_per_quintal = EXCLUDED.msp_price_per_quintal,
                        category = EXCLUDED.category,
                        season = EXCLUDED.season,
                        effective_year = EXCLUDED.effective_year,
                        updated_at = EXCLUDED.updated_at
                """
                cursor.execute(sql, (crop, msp_kg, msp_q, cat, season, yr, now, now))
            else:
                sql = """
                    INSERT OR REPLACE INTO government_msp (crop_name, msp_price_per_kg, msp_price_per_quintal, category, season, effective_year, source, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, 'Ministry of Agriculture & Farmers Welfare, Govt of India', 'active', ?, ?)
                """
                cursor.execute(sql, (crop, msp_kg, msp_q, cat, season, yr, now, now))
        conn.commit()
        _msp_seeded = True
    except Exception as e:
        print("[!] Error in seed_government_msp_data:", e)
    finally:
        conn.close()


def get_all_msp_references(search=None, season=None, year=None):
    seed_government_msp_data()
    conn, db_type = get_connection()
    try:
        cursor = conn.cursor()
        ph = "%s" if db_type == "postgres" else "?"
        where_clauses = []
        params = []
        if search:
            where_clauses.append(f"LOWER(crop_name) LIKE LOWER({ph})")
            params.append(f"%{search.strip()}%")
        if season and season != 'All':
            where_clauses.append(f"season = {ph}")
            params.append(season)
        if year and str(year) != 'All':
            where_clauses.append(f"effective_year = {ph}")
            params.append(int(year))
        
        where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
        sql = f"SELECT * FROM government_msp{where_sql} ORDER BY crop_name ASC"
        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall()
        return [_dict_row(r) for r in rows]
    except Exception as e:
        print("[!] Error in get_all_msp_references:", e)
        return []
    finally:
        conn.close()

def get_msp_by_crop(crop_name):
    if not crop_name: return None
    seed_government_msp_data()
    conn, db_type = get_connection()
    try:
        cursor = conn.cursor()
        ph = "%s" if db_type == "postgres" else "?"
        c_clean = crop_name.strip()
        sql = f"""
            SELECT * FROM government_msp 
            WHERE LOWER(crop_name) = LOWER({ph}) 
               OR LOWER({ph}) LIKE '%' || LOWER(crop_name) || '%' 
               OR LOWER(crop_name) LIKE '%' || LOWER({ph}) || '%'
            LIMIT 1
        """
        cursor.execute(sql, (c_clean, c_clean, c_clean))
        row = cursor.fetchone()
        return _dict_row(row)
    except Exception as e:
        print(f"[!] Error in get_msp_by_crop({crop_name}):", e)
        return None
    finally:
        conn.close()

def save_msp_reference(crop_name, msp_price_per_kg, category='Cereals', season='Kharif', effective_year=2025, source='Ministry of Agriculture & Farmers Welfare, Govt of India', status='active'):
    conn, db_type = get_connection()
    try:
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat()
        ph = "%s" if db_type == "postgres" else "?"
        msp_kg = float(msp_price_per_kg)
        msp_q = msp_kg * 100.0
        c_name = crop_name.strip().title()
        if db_type == "postgres":
            sql = f"""
                INSERT INTO government_msp (crop_name, msp_price_per_kg, msp_price_per_quintal, category, season, effective_year, source, status, created_at, updated_at)
                VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
                ON CONFLICT (crop_name) DO UPDATE SET 
                    msp_price_per_kg = EXCLUDED.msp_price_per_kg,
                    msp_price_per_quintal = EXCLUDED.msp_price_per_quintal,
                    category = EXCLUDED.category,
                    season = EXCLUDED.season,
                    effective_year = EXCLUDED.effective_year,
                    source = EXCLUDED.source,
                    status = EXCLUDED.status,
                    updated_at = EXCLUDED.updated_at
            """
            cursor.execute(sql, (c_name, msp_kg, msp_q, category, season, int(effective_year), source, status, now, now))
        else:
            sql = f"""
                INSERT OR REPLACE INTO government_msp (crop_name, msp_price_per_kg, msp_price_per_quintal, category, season, effective_year, source, status, created_at, updated_at)
                VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
            """
            cursor.execute(sql, (c_name, msp_kg, msp_q, category, season, int(effective_year), source, status, now, now))
        conn.commit()
        return True
    except Exception as e:
        print("[!] Error in save_msp_reference:", e)
        return False
    finally:
        conn.close()

def toggle_msp_status(crop_name, new_status):
    conn, db_type = get_connection()
    try:
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat()
        ph = "%s" if db_type == "postgres" else "?"
        sql = f"UPDATE government_msp SET status = {ph}, updated_at = {ph} WHERE LOWER(crop_name) = LOWER({ph})"
        cursor.execute(sql, (new_status, now, crop_name.strip()))
        conn.commit()
        return True
    except Exception as e:
        print("[!] Error in toggle_msp_status:", e)
        return False
    finally:
        conn.close()

# --- ADMIN LISTINGS MANAGEMENT SERVICES ---

def get_all_listings_admin():
    seed_government_msp_data()
    conn, db_type = get_connection()
    try:
        cursor = conn.cursor()
        
        # Batch fetch all MSP active benchmark values in a single query
        cursor.execute("SELECT crop_name, msp_price_per_kg FROM government_msp")
        msp_rows = cursor.fetchall()
        msp_map = {}
        for r in msp_rows:
            rd = _dict_row(r)
            if rd and rd.get('crop_name'):
                msp_map[rd['crop_name'].strip().lower()] = float(rd['msp_price_per_kg'])

        sql = """
            SELECT c.*, fp.name AS farmer_name, u.email AS farmer_email
            FROM crops c
            JOIN users u ON c.farmer_id = u.id
            LEFT JOIN farmer_profiles fp ON u.id = fp.user_id
            ORDER BY c.created_at DESC
        """
        cursor.execute(sql)
        rows = cursor.fetchall()
        listings = [_dict_row(r) for r in rows]
        for l in listings:
            c_name = l['crop_name'].strip().lower() if l.get('crop_name') else ''
            msp_val = msp_map.get(c_name)
            if msp_val is None:
                # Substring matching fallback
                msp_val = next((v for k, v in msp_map.items() if k in c_name or c_name in k), None)
            l['msp_reference'] = msp_val
        return listings
    except Exception as e:
        print("[!] Error in get_all_listings_admin:", e)
        return []
    finally:
        conn.close()


def get_listing_by_id_admin(crop_id):
    conn, db_type = get_connection()
    try:
        cursor = conn.cursor()
        ph = "%s" if db_type == "postgres" else "?"
        sql = f"""
            SELECT c.*, fp.name AS farmer_name, fp.phone AS farmer_phone, u.email AS farmer_email
            FROM crops c
            JOIN users u ON c.farmer_id = u.id
            LEFT JOIN farmer_profiles fp ON u.id = fp.user_id
            WHERE c.id = {ph}
        """
        cursor.execute(sql, (str(crop_id),))
        row = cursor.fetchone()
        listing = _dict_row(row)
        if listing:
            msp_info = get_msp_by_crop(listing['crop_name'])
            listing['msp_reference'] = msp_info['msp_price_per_kg'] if msp_info else None
        return listing
    except Exception as e:
        print(f"[!] Error in get_listing_by_id_admin({crop_id}):", e)
        return None
    finally:
        conn.close()

def update_listing_status_admin(crop_id, status, admin_id=None):
    conn, db_type = get_connection()
    try:
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat()
        ph = "%s" if db_type == "postgres" else "?"
        sql = f"UPDATE crops SET status = {ph}, updated_at = {ph} WHERE id = {ph}"
        cursor.execute(sql, (status, now, str(crop_id)))
        conn.commit()
        if admin_id:
            log_admin_action(admin_id, f"Admin updated listing status to {status}", reason=f"Listing {crop_id}")
        return True
    except Exception as e:
        print(f"[!] Error in update_listing_status_admin({crop_id}):", e)
        return False
    finally:
        conn.close()

# --- ADMIN ORDERS MANAGEMENT SERVICES ---

def get_all_orders_admin(status_filter=None):
    conn, db_type = get_connection()
    try:
        cursor = conn.cursor()
        ph = "%s" if db_type == "postgres" else "?"
        where_sql = f" WHERE o.status = {ph}" if status_filter and status_filter != 'All' else ""
        params = (status_filter,) if status_filter and status_filter != 'All' else ()
        
        sql = f"""
            SELECT o.*, 
                   fp.name AS farmer_name, fp.phone AS farmer_phone, u_f.email AS farmer_email,
                   bp.name AS buyer_name, bp.phone AS buyer_phone, u_b.email AS buyer_email,
                   c.price_per_kg AS unit_price
            FROM orders o
            JOIN users u_f ON o.farmer_id = u_f.id
            LEFT JOIN farmer_profiles fp ON u_f.id = fp.user_id
            JOIN users u_b ON o.buyer_id = u_b.id
            LEFT JOIN buyer_profiles bp ON u_b.id = bp.user_id
            LEFT JOIN crops c ON o.crop_id = c.id
            {where_sql}
            ORDER BY o.created_at DESC
        """
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        orders = [_dict_row(r) for r in rows]
        for o in orders:
            if not o.get('unit_price') and float(o.get('quantity', 0)) > 0:
                o['unit_price'] = round(float(o['total_price']) / float(o['quantity']), 2)
        return orders
    except Exception as e:
        print("[!] Error in get_all_orders_admin:", e)
        return []
    finally:
        conn.close()

def get_order_by_id_admin(order_id):
    conn, db_type = get_connection()
    try:
        cursor = conn.cursor()
        ph = "%s" if db_type == "postgres" else "?"
        sql = f"""
            SELECT o.*, 
                   fp.name AS farmer_name, fp.phone AS farmer_phone, u_f.email AS farmer_email,
                   bp.name AS buyer_name, bp.phone AS buyer_phone, u_b.email AS buyer_email,
                   c.price_per_kg AS unit_price
            FROM orders o
            JOIN users u_f ON o.farmer_id = u_f.id
            LEFT JOIN farmer_profiles fp ON u_f.id = fp.user_id
            JOIN users u_b ON o.buyer_id = u_b.id
            LEFT JOIN buyer_profiles bp ON u_b.id = bp.user_id
            LEFT JOIN crops c ON o.crop_id = c.id
            WHERE o.id = {ph}
        """
        cursor.execute(sql, (str(order_id),))
        row = cursor.fetchone()
        order = _dict_row(row)
        if order and not order.get('unit_price') and float(order.get('quantity', 0)) > 0:
            order['unit_price'] = round(float(order['total_price']) / float(order['quantity']), 2)
        return order
    except Exception as e:
        print(f"[!] Error in get_order_by_id_admin({order_id}):", e)
        return None
    finally:
        conn.close()

# --- ADMIN DASHBOARD STATS & AUDIT LOGGING ---

def get_admin_dashboard_stats():
    conn, db_type = get_connection()
    try:
        cursor = conn.cursor()
        
        cursor.execute("SELECT count(*) AS count FROM users WHERE role = 'farmer'")
        total_farmers = int(_val(cursor.fetchone(), 0))

        cursor.execute("SELECT count(*) AS count FROM users WHERE role = 'buyer'")
        total_buyers = int(_val(cursor.fetchone(), 0))

        cursor.execute("SELECT count(*) AS count FROM crops WHERE status = 'available'")
        active_listings = int(_val(cursor.fetchone(), 0))

        cursor.execute("SELECT COALESCE(SUM(quantity), 0) AS total_qty FROM crops WHERE status = 'available'")
        total_listed_qty = float(_val(cursor.fetchone(), 0.0))

        cursor.execute("SELECT count(*) AS count FROM orders WHERE status = 'Pending'")
        pending_orders = int(_val(cursor.fetchone(), 0))

        cursor.execute("SELECT count(*) AS count FROM orders WHERE status = 'Accepted'")
        accepted_orders = int(_val(cursor.fetchone(), 0))

        cursor.execute("SELECT count(*) AS count FROM orders WHERE status = 'Completed'")
        completed_orders = int(_val(cursor.fetchone(), 0))

        return {
            'total_farmers': total_farmers,
            'total_buyers': total_buyers,
            'active_listings': active_listings,
            'total_listed_qty': total_listed_qty,
            'pending_orders': pending_orders,
            'accepted_orders': accepted_orders,
            'completed_orders': completed_orders
        }
    except Exception as e:
        print("[!] Error in get_admin_dashboard_stats:", e)
        return {
            'total_farmers': 0, 'total_buyers': 0, 'active_listings': 0,
            'total_listed_qty': 0.0, 'pending_orders': 0, 'accepted_orders': 0, 'completed_orders': 0
        }
    finally:
        conn.close()


def log_admin_action(admin_id, action, target_user_id=None, reason=None):
    conn, db_type = get_connection()
    try:
        cursor = conn.cursor()
        aid = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        ph = "%s" if db_type == "postgres" else "?"
        sql = f"""
            INSERT INTO audit_logs (id, admin_id, action, target_user_id, reason, created_at)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})
        """
        cursor.execute(sql, (aid, str(admin_id) if admin_id else None, action, str(target_user_id) if target_user_id else None, reason, now))
        conn.commit()
    except Exception as e:
        print("[!] Error logging admin action:", e)
    finally:
        conn.close()


def reset_database():
    conn, db_type = get_connection()
    tables = ["email_notifications", "orders", "crops", "farmer_profiles", "buyer_profiles", "verification_tokens", "audit_logs", "users"]
    try:
        cursor = conn.cursor()
        for t in tables:
            try:
                if db_type == "postgres":
                    cursor.execute(f"TRUNCATE TABLE {t} CASCADE;")
                else:
                    cursor.execute(f"DELETE FROM {t};")
            except Exception:
                pass
        conn.commit()
    except Exception as e:
        print("[!] Error clearing database tables:", e)
    finally:
        conn.close()

    init_db()
    ensure_seed_users()

