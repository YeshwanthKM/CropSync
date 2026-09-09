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
        if conn is not None:
            try:
                if not conn.closed and conn.status == psycopg2.extensions.STATUS_READY:
                    return conn, "postgres"
            except Exception:
                try: conn.close()
                except Exception: pass
                _thread_local.conn = None

        url = DB_URL
        if 'sslmode' not in url.lower():
            sep = '&' if '?' in url else '?'
            url = f"{url}{sep}sslmode=require"
        conn = psycopg2.connect(url, cursor_factory=psycopg2.extras.RealDictCursor, connect_timeout=5)
        conn.autocommit = True
        _thread_local.conn = conn
        return conn, "postgres"
    else:
        # Fallback to local SQLite database with thread-local connection reuse
        conn = getattr(_thread_local, 'sqlite_conn', None)
        if conn is not None:
            try:
                conn.execute("SELECT 1")
                return conn, "sqlite"
            except Exception:
                try: conn.close()
                except Exception: pass
                _thread_local.sqlite_conn = None

        data_dir = '/tmp' if os.environ.get('VERCEL') else '.'
        db_path = os.path.join(data_dir, 'cropsync.db')
        conn = sqlite3.connect(db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        _thread_local.sqlite_conn = conn
        return conn, "sqlite"


def release_connection(conn, cursor=None):
    if cursor:
        try:
            cursor.close()
        except Exception:
            pass



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
                    role TEXT CHECK (role IN ('farmer', 'buyer', 'admin', 'logistics')) NOT NULL,
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



                
                CREATE TABLE IF NOT EXISTS logistics_profiles (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID REFERENCES users(id) ON DELETE CASCADE UNIQUE NOT NULL,
                    company_name TEXT NOT NULL,
                    phone TEXT,
                    service_area TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
                );
                CREATE TABLE IF NOT EXISTS order_status_history (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    order_id UUID REFERENCES orders(id) ON DELETE CASCADE NOT NULL,
                    previous_status TEXT,
                    new_status TEXT NOT NULL,
                    updated_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
                    updated_by_role TEXT,
                    notes TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
                );
                ALTER TABLE users DROP CONSTRAINT IF EXISTS users_role_check;
                ALTER TABLE users ADD CONSTRAINT users_role_check CHECK (role IN ('farmer', 'buyer', 'admin', 'logistics'));

                CREATE TABLE IF NOT EXISTS farmer_profiles (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID REFERENCES users(id) ON DELETE CASCADE UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    phone TEXT,
                    address TEXT,
                    location TEXT,
                    is_verified BOOLEAN DEFAULT FALSE NOT NULL,
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
                CREATE TABLE IF NOT EXISTS logistics_profiles (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID REFERENCES users(id) ON DELETE CASCADE UNIQUE NOT NULL,
                    company_name TEXT NOT NULL,
                    phone TEXT,
                    service_area TEXT,
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
                    payment_status TEXT DEFAULT 'pending' CHECK (payment_status IN ('pending', 'paid', 'failed', 'refunded')) NOT NULL,
                    fulfillment_method TEXT DEFAULT 'Direct Collection',
                    logistics_partner_id UUID REFERENCES users(id) ON DELETE SET NULL,
                    logistics_partner_name TEXT DEFAULT 'CropSync Logistics',
                    logistics_status TEXT DEFAULT 'NONE',
                    logistics_fee NUMERIC DEFAULT 0.0,
                    cod_amount NUMERIC DEFAULT 0.0,
                    farmer_settlement_amount NUMERIC DEFAULT 0.0,
                    settlement_status TEXT DEFAULT 'UNSETTLED',
                    pickup_address TEXT,
                    delivery_address TEXT,
                    pickup_scheduled_at TIMESTAMP WITH TIME ZONE,
                    picked_up_at TIMESTAMP WITH TIME ZONE,
                    delivered_at TIMESTAMP WITH TIME ZONE,
                    payment_collected_at TIMESTAMP WITH TIME ZONE,
                    settlement_at TIMESTAMP WITH TIME ZONE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
                );
                CREATE TABLE IF NOT EXISTS order_status_history (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    order_id UUID REFERENCES orders(id) ON DELETE CASCADE NOT NULL,
                    previous_status TEXT,
                    new_status TEXT NOT NULL,
                    updated_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
                    updated_by_role TEXT,
                    notes TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
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

            # PostgreSQL order column migrations for existing deployments
            pg_order_cols = [
                "fulfillment_method TEXT DEFAULT 'Direct Collection'",
                "logistics_partner_id UUID",
                "logistics_partner_name TEXT DEFAULT 'CropSync Logistics'",
                "logistics_status TEXT DEFAULT 'NONE'",
                "logistics_fee NUMERIC DEFAULT 0.0",
                "cod_amount NUMERIC DEFAULT 0.0",
                "farmer_settlement_amount NUMERIC DEFAULT 0.0",
                "settlement_status TEXT DEFAULT 'UNSETTLED'",
                "pickup_address TEXT",
                "delivery_address TEXT",
                "pickup_scheduled_at TIMESTAMP WITH TIME ZONE",
                "picked_up_at TIMESTAMP WITH TIME ZONE",
                "delivered_at TIMESTAMP WITH TIME ZONE",
                "payment_collected_at TIMESTAMP WITH TIME ZONE",
                "settlement_at TIMESTAMP WITH TIME ZONE",
                "payment_status TEXT DEFAULT 'pending'",
                "buyer_confirmed_receipt BOOLEAN DEFAULT FALSE"
            ]
            for col in pg_order_cols:
                try:
                    cursor.execute(f"ALTER TABLE orders ADD COLUMN IF NOT EXISTS {col};")
                except Exception as e:
                    print(f"[!] Warning adding postgres column {col}:", e)

            try:
                cursor.execute("ALTER TABLE farmer_profiles ADD COLUMN IF NOT EXISTS is_verified BOOLEAN DEFAULT FALSE;")
            except Exception as e:
                print("[!] Warning adding is_verified column to postgres farmer_profiles:", e)

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
                    role TEXT CHECK (role IN ('farmer', 'buyer', 'admin', 'logistics')) NOT NULL,
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

                
                CREATE TABLE IF NOT EXISTS logistics_profiles (
                    id TEXT PRIMARY KEY,
                    user_id TEXT REFERENCES users(id) ON DELETE CASCADE UNIQUE NOT NULL,
                    company_name TEXT NOT NULL,
                    phone TEXT,
                    service_area TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS order_status_history (
                    id TEXT PRIMARY KEY,
                    order_id TEXT REFERENCES orders(id) ON DELETE CASCADE NOT NULL,
                    previous_status TEXT,
                    new_status TEXT NOT NULL,
                    updated_by_id TEXT REFERENCES users(id) ON DELETE SET NULL,
                    updated_by_role TEXT,
                    notes TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS farmer_profiles (
                    id TEXT PRIMARY KEY,
                    user_id TEXT REFERENCES users(id) ON DELETE CASCADE UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    phone TEXT,
                    address TEXT,
                    location TEXT,
                    is_verified INTEGER DEFAULT 0,
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

            try:
                cursor.execute("ALTER TABLE farmer_profiles ADD COLUMN is_verified INTEGER DEFAULT 0")
            except Exception:
                pass

            try:
                cursor.execute("ALTER TABLE orders ADD COLUMN buyer_confirmed_receipt INTEGER DEFAULT 0")
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

            
            
            # SQLite users table role CHECK constraint migration
            if db_type != "postgres":
                try:
                    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='users'")
                    row = cursor.fetchone()
                    if row and "'logistics'" not in row[0]:
                        cursor.execute("PRAGMA foreign_keys=OFF")
                        cursor.execute("CREATE TABLE users_old AS SELECT * FROM users")
                        cursor.execute("DROP TABLE users")
                        cursor.execute("""
                            CREATE TABLE users (
                                id TEXT PRIMARY KEY,
                                email TEXT UNIQUE NOT NULL,
                                password_hash TEXT NOT NULL,
                                role TEXT CHECK (role IN ('farmer', 'buyer', 'admin', 'logistics')) NOT NULL,
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
                        """)
                        cursor.execute("INSERT INTO users SELECT * FROM users_old")
                        cursor.execute("DROP TABLE users_old")
                        cursor.execute("PRAGMA foreign_keys=ON")
                except Exception as e:
                    print("[!] SQLite users table migration warning:", e)

            # Order Logistics Column Migrations
            order_cols = [
                "fulfillment_method TEXT DEFAULT 'Direct Collection'",
                "logistics_partner_id TEXT",
                "logistics_partner_name TEXT",
                "logistics_status TEXT DEFAULT 'NONE'",
                "logistics_fee REAL DEFAULT 0.0" if db_type != "postgres" else "logistics_fee NUMERIC DEFAULT 0.0",
                "cod_amount REAL DEFAULT 0.0" if db_type != "postgres" else "cod_amount NUMERIC DEFAULT 0.0",
                "farmer_settlement_amount REAL DEFAULT 0.0" if db_type != "postgres" else "farmer_settlement_amount NUMERIC DEFAULT 0.0",
                "settlement_status TEXT DEFAULT 'UNSETTLED'",
                "pickup_address TEXT",
                "delivery_address TEXT",
                "pickup_scheduled_at TEXT" if db_type != "postgres" else "pickup_scheduled_at TIMESTAMP WITH TIME ZONE",
                "picked_up_at TEXT" if db_type != "postgres" else "picked_up_at TIMESTAMP WITH TIME ZONE",
                "delivered_at TEXT" if db_type != "postgres" else "delivered_at TIMESTAMP WITH TIME ZONE",
                "payment_collected_at TEXT" if db_type != "postgres" else "payment_collected_at TIMESTAMP WITH TIME ZONE",
                "settlement_at TEXT" if db_type != "postgres" else "settlement_at TIMESTAMP WITH TIME ZONE"
            ]
            for col in order_cols:
                try:
                    cursor.execute(f"ALTER TABLE orders ADD COLUMN {col}")
                except Exception:
                    pass

            # Create performance indexes across both Postgres and SQLite
            perf_indexes = [
                "CREATE INDEX IF NOT EXISTS idx_orders_farmer_id ON orders(farmer_id);",
                "CREATE INDEX IF NOT EXISTS idx_orders_buyer_id ON orders(buyer_id);",
                "CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);",
                "CREATE INDEX IF NOT EXISTS idx_orders_logistics_status ON orders(logistics_status);",
                "CREATE INDEX IF NOT EXISTS idx_crops_farmer_id ON crops(farmer_id);",
                "CREATE INDEX IF NOT EXISTS idx_crops_status ON crops(status);",
                "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);"
            ]
            for p_idx in perf_indexes:
                try:
                    cursor.execute(p_idx)
                except Exception:
                    pass

            conn.commit()


    except Exception as e:
        print("[!] Error executing DDL in init_db:", e)
    finally:
        release_connection(conn, cursor)



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
    if isinstance(row, (int, float)):
        return row
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
                       COALESCE(fp.name, bp.name, lp.company_name, 'Admin') as name,
                       COALESCE(fp.phone, bp.phone, lp.phone) as phone,
                       COALESCE(fp.address, bp.address, lp.service_area) as address,
                       COALESCE(fp.location, bp.location, lp.service_area) as location,
                       COALESCE(fp.is_verified, FALSE) as is_verified,
                       bp.organization
                FROM users u
                LEFT JOIN farmer_profiles fp ON u.id = fp.user_id
                LEFT JOIN buyer_profiles bp ON u.id = bp.user_id
                LEFT JOIN logistics_profiles lp ON u.id = lp.user_id
                WHERE LOWER(u.email) = LOWER(%s)
            """ if db_type == "postgres" else """
                SELECT u.*, 
                       COALESCE(fp.name, bp.name, lp.company_name, 'Admin') as name,
                       COALESCE(fp.phone, bp.phone, lp.phone) as phone,
                       COALESCE(fp.address, bp.address, lp.service_area) as address,
                       COALESCE(fp.location, bp.location, lp.service_area) as location,
                       COALESCE(fp.is_verified, FALSE) as is_verified,
                       bp.organization
                FROM users u
                LEFT JOIN farmer_profiles fp ON u.id = fp.user_id
                LEFT JOIN buyer_profiles bp ON u.id = bp.user_id
                LEFT JOIN logistics_profiles lp ON u.id = lp.user_id
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
                       COALESCE(fp.name, bp.name, lp.company_name, 'Admin') as name,
                       COALESCE(fp.phone, bp.phone, lp.phone) as phone,
                       COALESCE(fp.address, bp.address, lp.service_area) as address,
                       COALESCE(fp.location, bp.location, lp.service_area) as location,
                       COALESCE(fp.is_verified, FALSE) as is_verified,
                       bp.organization
                FROM users u
                LEFT JOIN farmer_profiles fp ON u.id = fp.user_id
                LEFT JOIN buyer_profiles bp ON u.id = bp.user_id
                LEFT JOIN logistics_profiles lp ON u.id = lp.user_id
                WHERE u.id = %s
            """ if db_type == "postgres" else """
                SELECT u.*, 
                       COALESCE(fp.name, bp.name, lp.company_name, 'Admin') as name,
                       COALESCE(fp.phone, bp.phone, lp.phone) as phone,
                       COALESCE(fp.address, bp.address, lp.service_area) as address,
                       COALESCE(fp.location, bp.location, lp.service_area) as location,
                       COALESCE(fp.is_verified, FALSE) as is_verified,
                       bp.organization
                FROM users u
                LEFT JOIN farmer_profiles fp ON u.id = fp.user_id
                LEFT JOIN buyer_profiles bp ON u.id = bp.user_id
                LEFT JOIN logistics_profiles lp ON u.id = lp.user_id
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

SEED_USERS = []

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
            elif role == 'logistics':
                prof_sql = """
                    INSERT INTO logistics_profiles (user_id, company_name, phone, service_area)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (user_id) DO UPDATE SET company_name = EXCLUDED.company_name, phone = EXCLUDED.phone, service_area = EXCLUDED.service_area
                """
                cursor.execute(prof_sql, (uid, name, phone, address or location or "Pan-India"))
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
            elif role == 'logistics':
                prof_sql = """
                    INSERT OR REPLACE INTO logistics_profiles (id, user_id, company_name, phone, service_area, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """
                cursor.execute(prof_sql, (str(uuid.uuid4()), uid, name, phone, address or location or "Pan-India", now, now))

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

PERMANENT_DEMO_EMAILS = {
    'admin@cropsync.com',
    'logistics@cropsync.com',
}

def delete_user(user_id):
    user = get_user_by_id(user_id)
    if user and user.get('email', '').strip().lower() in PERMANENT_DEMO_EMAILS:
        print(f"[!] Protection: Permanent demo account {user.get('email')} cannot be deleted.")
        return False

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
        return True
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
    ensure_seed_logistics_user()

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
                where_clauses.append("(fp.is_verified = TRUE OR fp.is_verified = 1)")
            elif status_filter == 'unverified':
                where_clauses.append("(fp.is_verified IS NULL OR fp.is_verified = FALSE OR fp.is_verified = 0)")
            elif status_filter == 'pending':
                where_clauses.append("u.account_status = 'pending'")
            elif status_filter == 'suspended':
                where_clauses.append("u.account_status = 'suspended'")

            where_sql = " AND ".join(where_clauses)
            sql = f"""
                SELECT u.id, u.email, u.account_status, u.suspension_reason, u.created_at,
                       COALESCE(u.email_verified, FALSE) as email_verified,
                       COALESCE(u.phone_verified, FALSE) as phone_verified,
                       COALESCE(fp.is_verified, FALSE) as is_verified,
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

def set_farmer_verification_admin(farmer_id, is_verified, admin_id=None):
    try:
        conn, db_type = get_connection()
        try:
            cursor = conn.cursor()
            ph = "%s" if db_type == "postgres" else "?"
            now = datetime.utcnow().isoformat()
            
            val = True if is_verified in (True, 1, 'true', '1') else False
            val_db = 1 if (db_type == "sqlite" and val) else (0 if db_type == "sqlite" else val)
            
            sql_chk = f"SELECT user_id FROM farmer_profiles WHERE user_id = {ph}"
            cursor.execute(sql_chk, (str(farmer_id),))
            row = cursor.fetchone()
            
            if row:
                sql_upd = f"UPDATE farmer_profiles SET is_verified = {ph}, updated_at = {ph} WHERE user_id = {ph}"
                cursor.execute(sql_upd, (val_db, now, str(farmer_id)))
            else:
                fid = str(uuid.uuid4())
                sql_ins = f"INSERT INTO farmer_profiles (id, user_id, name, is_verified, created_at, updated_at) VALUES ({ph}, {ph}, 'Farmer', {ph}, {ph}, {ph})"
                cursor.execute(sql_ins, (fid, str(farmer_id), val_db, now, now))
                
            conn.commit()
            if admin_id:
                action_name = "VERIFY_FARMER" if val else "UNVERIFY_FARMER"
                log_admin_action(admin_id, action_name, farmer_id, f"Set farmer verification status to {val}")
            return True, "Farmer verification status updated."
        finally:
            conn.close()
    except Exception as e:
        print("[!] Error in set_farmer_verification_admin:", e)
        return False, f"Server error: {e}"

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
                LEFT JOIN logistics_profiles lp ON u.id = lp.user_id
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
            join_sql = "JOIN users u ON c.farmer_id::text = u.id::text LEFT JOIN farmer_profiles fp ON u.id::text = fp.user_id::text" if db_type == "postgres" else "JOIN users u ON c.farmer_id = u.id LEFT JOIN farmer_profiles fp ON u.id = fp.user_id"
            
            query = f"""
                SELECT c.*, COALESCE(fp.name, u.email, 'Farmer') as farmer_name, COALESCE(fp.phone, 'N/A') as farmer_phone, COALESCE(fp.is_verified, FALSE) as is_verified
                FROM crops c
                {join_sql}
                WHERE c.status = 'available'
            """
            params = []
            if farmer_id:
                farmer_where = "c.farmer_id::text = %s" if db_type == "postgres" else "c.farmer_id = ?"
                query = f"""
                    SELECT c.*, COALESCE(fp.name, u.email, 'Farmer') as farmer_name, COALESCE(fp.phone, 'N/A') as farmer_phone, COALESCE(fp.is_verified, FALSE) as is_verified
                    FROM crops c
                    {join_sql}
                    WHERE {farmer_where} AND c.status = 'available'
                """
                params.append(str(farmer_id).strip())
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
        cursor = None
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
            release_connection(conn, cursor)
    except Exception as e:
        print("[!] Error in get_orders_for_farmer:", e)
        return []

def get_orders_for_buyer(buyer_id):
    try:
        conn, db_type = get_connection()
        cursor = None
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
            release_connection(conn, cursor)
    except Exception as e:
        print("[!] Error in get_orders_for_buyer:", e)
        return []

# --- PHASE 4 EMAIL NOTIFICATIONS LOG & ORDER COMPLETION SERVICES ---

def log_email_notification(order_id, recipient_user_id, notification_type, recipient_email, status='PENDING', error_message=None):
    conn, db_type = get_connection()
    cursor = None
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
        release_connection(conn, cursor)

def get_email_notifications_for_order(order_id):
    conn, db_type = get_connection()
    cursor = None
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
        release_connection(conn, cursor)

def get_all_email_notifications_admin():
    conn, db_type = get_connection()
    cursor = None
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
        release_connection(conn, cursor)


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
        release_connection(conn, cursor)

def create_order(buyer_id, farmer_id, crop_id, crop_name, quantity, total_price, order_id=None, fulfillment_method='Direct Collection', logistics_fee=0.0, cod_amount=0.0, farmer_settlement_amount=0.0, pickup_address="", delivery_address="", logistics_partner_name="CropSync Logistics"):
    conn, db_type = get_connection()
    cursor = None
    try:
        cursor = conn.cursor()
        oid = str(order_id) if order_id else str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        ph = "%s" if db_type == "postgres" else "?"
        log_status = 'LOGISTICS_REQUESTED' if fulfillment_method == 'Logistics Partner' else 'NONE'
        sql = f"""
            INSERT INTO orders (id, crop_id, buyer_id, farmer_id, crop_name, quantity, total_price, status, fulfillment_method, logistics_partner_name, logistics_status, logistics_fee, cod_amount, farmer_settlement_amount, payment_status, settlement_status, pickup_address, delivery_address, created_at, updated_at)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, 'Pending', {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, 'pending', 'UNSETTLED', {ph}, {ph}, {ph}, {ph})
        """
        cursor.execute(sql, (oid, str(crop_id), str(buyer_id), str(farmer_id), crop_name, float(quantity), float(total_price), fulfillment_method, logistics_partner_name, log_status, float(logistics_fee), float(cod_amount), float(farmer_settlement_amount), pickup_address, delivery_address, now, now))
        conn.commit()
        return oid
    finally:
        release_connection(conn, cursor)

def update_order_status(order_id, status):
    conn, db_type = get_connection()
    cursor = None
    try:
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat()
        ph = "%s" if db_type == "postgres" else "?"
        sql = f"UPDATE orders SET status = {ph}, updated_at = {ph} WHERE id = {ph}"
        cursor.execute(sql, (status, now, str(order_id)))
        conn.commit()
    finally:
        release_connection(conn, cursor)




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
        log_status = 'LOGISTICS_REQUESTED' if (order.get('fulfillment_method') == 'Logistics Partner' or order.get('logistics_status') == 'LOGISTICS_REQUESTED') else (order.get('logistics_status') or 'NONE')
        sql_u_order = f"UPDATE orders SET status = 'Accepted', logistics_status = {ph}, updated_at = {ph} WHERE id = {ph}"
        cursor.execute(sql_u_order, (log_status, now, str(order_id)))

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
            SELECT c.*, fp.name AS farmer_name, u.email AS farmer_email, COALESCE(fp.is_verified, FALSE) AS is_verified
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
            SELECT c.*, fp.name AS farmer_name, fp.phone AS farmer_phone, u.email AS farmer_email, COALESCE(fp.is_verified, FALSE) AS is_verified
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
        query = """
            SELECT 
                (SELECT count(*) FROM users WHERE role = 'farmer') AS total_farmers,
                (SELECT count(*) FROM users WHERE role = 'buyer') AS total_buyers,
                (SELECT count(*) FROM crops WHERE status = 'available') AS active_listings,
                (SELECT COALESCE(SUM(quantity), 0) FROM crops WHERE status = 'available') AS total_listed_qty,
                (SELECT count(*) FROM orders WHERE status = 'Pending') AS pending_orders,
                (SELECT count(*) FROM orders WHERE status = 'Accepted') AS accepted_orders,
                (SELECT count(*) FROM orders WHERE status = 'Completed') AS completed_orders
        """
        cursor.execute(query)
        row = cursor.fetchone()
        dict_row = _dict_row(row) or {}
        return {
            'total_farmers': int(dict_row.get('total_farmers') or 0),
            'total_buyers': int(dict_row.get('total_buyers') or 0),
            'active_listings': int(dict_row.get('active_listings') or 0),
            'total_listed_qty': float(dict_row.get('total_listed_qty') or 0.0),
            'pending_orders': int(dict_row.get('pending_orders') or 0),
            'accepted_orders': int(dict_row.get('accepted_orders') or 0),
            'completed_orders': int(dict_row.get('completed_orders') or 0)
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
    tables = ["order_status_history", "logistics_profiles", "email_notifications", "orders", "crops", "farmer_profiles", "buyer_profiles", "verification_tokens", "audit_logs", "users"]
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




# --- LOGISTICS ROLE & FULFILLMENT SERVICES ---

VALID_LOGISTICS_TRANSITIONS = {
    'NONE': ['LOGISTICS_REQUESTED', 'PICKUP_SCHEDULED'],
    'LOGISTICS_REQUESTED': ['PICKUP_SCHEDULED', 'CANCELLED'],
    'PICKUP_SCHEDULED': ['PICKED_UP', 'DELIVERY_FAILED', 'CANCELLED'],
    'PICKED_UP': ['IN_TRANSIT', 'RETURN_TO_FARMER', 'DELIVERY_FAILED'],
    'IN_TRANSIT': ['OUT_FOR_DELIVERY', 'DELIVERY_FAILED', 'RETURN_TO_FARMER'],
    'OUT_FOR_DELIVERY': ['DELIVERED', 'DELIVERY_FAILED', 'RETURN_TO_FARMER'],
    'DELIVERED': ['SETTLED', 'PAYMENT_COLLECTED', 'SETTLEMENT_PENDING'],
    'PAYMENT_COLLECTED': ['SETTLED', 'SETTLEMENT_PENDING'],
    'SETTLEMENT_PENDING': ['SETTLED'],
    'SETTLED': [],
    'DELIVERY_FAILED': ['RETURN_TO_FARMER', 'PICKUP_SCHEDULED'],
    'RETURN_TO_FARMER': [],
    'CANCELLED': []
}

def ensure_seed_logistics_user():
    try:
        user = get_user_by_email("logistics@cropsync.com")
        from werkzeug.security import generate_password_hash
        pw_hash = generate_password_hash("logistics123", method='pbkdf2:sha256')
        user_id = user['id'] if user else None
        create_user(
            email="logistics@cropsync.com",
            password_hash=pw_hash,
            role="logistics",
            name="CropSync Logistics",
            phone="+91 9876543210",
            address="National Logistics Hub, Sector 4",
            location="Pan-India",
            organization="CropSync Freight Services",
            user_id=user_id,
            status="active",
            email_verified=True,
            phone_verified=True
        )
    except Exception as e:
        print("[!] Error in ensure_seed_logistics_user:", e)


def get_all_logistics_users():
    conn, db_type = get_connection()
    cursor = None
    try:
        cursor = conn.cursor()
        query = """
            SELECT u.id, u.email, u.account_status, u.created_at,
                   COALESCE(lp.company_name, 'CropSync Logistics') as name,
                   COALESCE(lp.phone, '+91 9876543210') as phone,
                   COALESCE(lp.service_area, 'Pan-India') as address
            FROM users u
            LEFT JOIN logistics_profiles lp ON u.id = lp.user_id
            WHERE u.role = 'logistics'
            ORDER BY u.created_at DESC
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        return [_dict_row(r) for r in rows]
    except Exception as e:
        print("[!] Error in get_all_logistics_users:", e)
        return []
    finally:
        release_connection(conn, cursor)

def _enrich_order_addresses(order):
    if not order:
        return order
    p_addr = (order.get('pickup_address') or '').strip()
    if not p_addr or p_addr == 'Farm Address':
        order['pickup_address'] = order.get('farmer_address') or order.get('farmer_location') or 'Farm Address'
    d_addr = (order.get('delivery_address') or '').strip()
    if not d_addr or d_addr == 'Delivery Address':
        order['delivery_address'] = order.get('buyer_address') or order.get('buyer_location') or 'Delivery Address'
    return order

def get_logistics_orders(logistics_user_id=None, status_filter=None, search=None):
    conn, db_type = get_connection()
    cursor = None
    try:
        cursor = conn.cursor()
        ph = "%s" if db_type == "postgres" else "?"
        sql = f"""
            SELECT o.*,
                   fp.name as farmer_name, fp.phone as farmer_phone, fp.location as farmer_location, fp.address as farmer_address,
                   bp.name as buyer_name, bp.phone as buyer_phone, bp.location as buyer_location, bp.address as buyer_address,
                   fu.email as farmer_email, bu.email as buyer_email
            FROM orders o
            JOIN users fu ON o.farmer_id = fu.id
            JOIN users bu ON o.buyer_id = bu.id
            LEFT JOIN farmer_profiles fp ON o.farmer_id = fp.user_id
            LEFT JOIN buyer_profiles bp ON o.buyer_id = bp.user_id
            WHERE o.fulfillment_method = 'Logistics Partner'
        """
        params = []
        if status_filter and status_filter != 'ALL':
            sql += f" AND o.logistics_status = {ph}"
            params.append(status_filter)
        if search:
            sql += f" AND (LOWER(o.crop_name) LIKE {ph} OR LOWER(fp.name) LIKE {ph} OR LOWER(bp.name) LIKE {ph} OR LOWER(CAST(o.id AS TEXT)) LIKE {ph})"
            s_term = f"%{search.lower()}%"
            params.extend([s_term, s_term, s_term, s_term])
        sql += " ORDER BY o.created_at DESC"
        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall()
        return [_enrich_order_addresses(_dict_row(r)) for r in rows]
    except Exception as e:
        print("[!] Error in get_logistics_orders:", e)
        return []
    finally:
        release_connection(conn, cursor)

def get_logistics_order_by_id(order_id):
    conn, db_type = get_connection()
    cursor = None
    try:
        cursor = conn.cursor()
        ph = "%s" if db_type == "postgres" else "?"
        sql = f"""
            SELECT o.*,
                   fp.name as farmer_name, fp.phone as farmer_phone, fp.location as farmer_location, fp.address as farmer_address,
                   bp.name as buyer_name, bp.phone as buyer_phone, bp.location as buyer_location, bp.address as buyer_address,
                   fu.email as farmer_email, bu.email as buyer_email
            FROM orders o
            JOIN users fu ON o.farmer_id = fu.id
            JOIN users bu ON o.buyer_id = bu.id
            LEFT JOIN farmer_profiles fp ON o.farmer_id = fp.user_id
            LEFT JOIN buyer_profiles bp ON o.buyer_id = bp.user_id
            WHERE o.id = {ph}
        """
        cursor.execute(sql, (str(order_id),))
        row = cursor.fetchone()
        return _enrich_order_addresses(_dict_row(row))
    except Exception as e:
        print(f"[!] Error in get_logistics_order_by_id({order_id}):", e)
        return None
    finally:
        release_connection(conn, cursor)

def get_logistics_dashboard_stats(logistics_user_id=None):
    conn, db_type = get_connection()
    cursor = None
    try:
        cursor = conn.cursor()
        sql = """
            SELECT 
                COUNT(*) as total_logistics_orders,
                COUNT(CASE WHEN logistics_status = 'LOGISTICS_REQUESTED' THEN 1 END) as new_orders,
                COUNT(CASE WHEN logistics_status = 'PICKUP_SCHEDULED' THEN 1 END) as pickup_pending,
                COUNT(CASE WHEN logistics_status IN ('PICKED_UP', 'IN_TRANSIT') THEN 1 END) as in_transit,
                COUNT(CASE WHEN logistics_status = 'OUT_FOR_DELIVERY' THEN 1 END) as out_for_delivery,
                COUNT(CASE WHEN logistics_status IN ('DELIVERED', 'PAYMENT_COLLECTED', 'SETTLEMENT_PENDING', 'SETTLED') THEN 1 END) as delivered,
                COUNT(CASE WHEN payment_status = 'COLLECTED' THEN 1 END) as payment_collected,
                COUNT(CASE WHEN settlement_status = 'SETTLEMENT_PENDING' THEN 1 END) as settlement_pending,
                COUNT(CASE WHEN settlement_status = 'SETTLED' THEN 1 END) as settled
            FROM orders
            WHERE fulfillment_method = 'Logistics Partner'
        """
        cursor.execute(sql)
        row = cursor.fetchone()
        d = _dict_row(row) or {}
        return {
            'total_logistics_orders': _val(d.get('total_logistics_orders'), 0),
            'new_orders': _val(d.get('new_orders'), 0),
            'pickup_pending': _val(d.get('pickup_pending'), 0),
            'in_transit': _val(d.get('in_transit'), 0),
            'out_for_delivery': _val(d.get('out_for_delivery'), 0),
            'delivered': _val(d.get('delivered'), 0),
            'payment_collected': _val(d.get('payment_collected'), 0),
            'settlement_pending': _val(d.get('settlement_pending'), 0),
            'settled': _val(d.get('settled'), 0),
        }
    except Exception as e:
        print("[!] Error in get_logistics_dashboard_stats:", e)
        return {
            'total_logistics_orders': 0, 'new_orders': 0, 'pickup_pending': 0,
            'in_transit': 0, 'out_for_delivery': 0, 'delivered': 0,
            'payment_collected': 0, 'settlement_pending': 0, 'settled': 0
        }
    finally:
        release_connection(conn, cursor)

def get_order_status_history(order_id):
    conn, db_type = get_connection()
    cursor = None
    try:
        cursor = conn.cursor()
        ph = "%s" if db_type == "postgres" else "?"
        sql = f"SELECT * FROM order_status_history WHERE order_id = {ph} ORDER BY created_at ASC"
        cursor.execute(sql, (str(order_id),))
        rows = cursor.fetchall()
        return [_dict_row(r) for r in rows]
    except Exception as e:
        print("[!] Error in get_order_status_history:", e)
        return []
    finally:
        release_connection(conn, cursor)

def _valid_user_id_or_none(cursor, user_id, ph):
    if not user_id:
        return None
    try:
        cursor.execute(f"SELECT id FROM users WHERE id = {ph}", (str(user_id),))
        row = cursor.fetchone()
        return str(user_id) if row else None
    except Exception:
        return None

def update_logistics_order_status_atomic(order_id, next_status, updated_by_user_id, updated_by_role='logistics', notes=None):
    conn, db_type = get_connection()
    cursor = None
    try:
        cursor = conn.cursor()
        ph = "%s" if db_type == "postgres" else "?"
        now = datetime.utcnow().isoformat()
        
        # 1. Fetch current order
        sql_fetch = f"SELECT * FROM orders WHERE id = {ph}"
        cursor.execute(sql_fetch, (str(order_id),))
        order_row = cursor.fetchone()
        order = _dict_row(order_row)
        if not order:
            return False, "Order not found.", None
            
        current_status = order.get('logistics_status') or 'NONE'
        
        # 2. Server-side State Machine Validation
        valid_next = VALID_LOGISTICS_TRANSITIONS.get(current_status, [])
        if next_status not in valid_next:
            return False, f"Invalid status transition from {current_status} to {next_status}.", None
            
        # 3. Update order fields based on transition
        update_fields = [f"logistics_status = {ph}", f"updated_at = {ph}"]
        params = [next_status, now]
        
        if next_status == 'PICKUP_SCHEDULED':
            update_fields.append(f"pickup_scheduled_at = {ph}")
            params.append(now)
        elif next_status == 'PICKED_UP':
            update_fields.append(f"picked_up_at = {ph}")
            params.append(now)
        elif next_status == 'DELIVERED':
            update_fields.append(f"delivered_at = {ph}")
            update_fields.append(f"payment_collected_at = {ph}")
            update_fields.append("payment_status = 'paid'")
            update_fields.append("settlement_status = 'SETTLEMENT_PENDING'")
            params.extend([now, now])
        elif next_status == 'PAYMENT_COLLECTED':
            update_fields.append("payment_status = 'paid'")
            update_fields.append(f"payment_collected_at = {ph}")
            update_fields.append("settlement_status = 'SETTLEMENT_PENDING'")
            params.append(now)
        elif next_status == 'SETTLEMENT_PENDING':
            update_fields.append("settlement_status = 'SETTLEMENT_PENDING'")
        elif next_status == 'SETTLED':
            update_fields.append("settlement_status = 'SETTLEMENT_PENDING'")
            update_fields.append(f"settlement_at = {ph}")
            params.append(now)
            
        params.append(str(order_id))
        sql_update = f"UPDATE orders SET {', '.join(update_fields)} WHERE id = {ph}"
        cursor.execute(sql_update, tuple(params))
        
        # 4. Record entry in order_status_history audit table
        valid_user_id = _valid_user_id_or_none(cursor, updated_by_user_id, ph)
        hid = str(uuid.uuid4())
        sql_hist = f"""
            INSERT INTO order_status_history (id, order_id, previous_status, new_status, updated_by_id, updated_by_role, notes, created_at)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
        """
        cursor.execute(sql_hist, (hid, str(order_id), current_status, next_status, valid_user_id, updated_by_role, notes or f"Status updated to {next_status}", now))
        
        conn.commit()
        
        # Fetch updated order to return
        cursor.execute(sql_fetch, (str(order_id),))
        updated_order = _dict_row(cursor.fetchone())
        return True, f"Order status updated to {next_status}.", updated_order
    except Exception as e:
        print("[!] Error in update_logistics_order_status_atomic:", e)
        try: conn.rollback()
        except: pass
        return False, f"Server error: {e}", None
    finally:
        release_connection(conn, cursor)

def farmer_confirm_payment_received_atomic(order_id, farmer_id):
    conn, db_type = get_connection()
    cursor = None
    try:
        cursor = conn.cursor()
        ph = "%s" if db_type == "postgres" else "?"
        now = datetime.utcnow().isoformat()
        
        sql_fetch = f"SELECT * FROM orders WHERE id = {ph}"
        cursor.execute(sql_fetch, (str(order_id),))
        order = _dict_row(cursor.fetchone())
        if not order:
            return False, "Order not found.", None
            
        if str(order['farmer_id']) != str(farmer_id):
            return False, "Unauthorized action.", None
            
        if order['settlement_status'] == 'SETTLED':
            return False, "Payment is already marked as settled.", order
            
        is_logistics = (order.get('fulfillment_method') == 'Logistics Partner')
        new_logistics_status = 'SETTLED' if is_logistics else (order.get('logistics_status') or 'NONE')

        sql_update = f"""
            UPDATE orders 
            SET settlement_status = 'SETTLED', 
                logistics_status = {ph}, 
                status = 'Completed', 
                settlement_at = {ph}, 
                updated_at = {ph} 
            WHERE id = {ph}
        """
        cursor.execute(sql_update, (new_logistics_status, now, now, str(order_id)))
        
        valid_farmer_id = _valid_user_id_or_none(cursor, farmer_id, ph)
        hid = str(uuid.uuid4())
        sql_hist = f"""
            INSERT INTO order_status_history (id, order_id, previous_status, new_status, updated_by_id, updated_by_role, notes, created_at)
            VALUES ({ph}, {ph}, {ph}, 'SETTLED', {ph}, 'farmer', 'Farmer confirmed receipt of payout settlement.', {ph})
        """
        cursor.execute(sql_hist, (hid, str(order_id), order.get('logistics_status', 'SETTLEMENT_PENDING'), valid_farmer_id, now))
        
        conn.commit()
        
        cursor.execute(sql_fetch, (str(order_id),))
        updated_order = _dict_row(cursor.fetchone())
        return True, "Payment receipt confirmed.", updated_order
    except Exception as e:
        print("[!] Error in farmer_confirm_payment_received_atomic:", e)
        try: conn.rollback()
        except: pass
        return False, f"Server error: {e}", None
    finally:
        release_connection(conn, cursor)

def buyer_confirm_order_received_atomic(order_id, buyer_id):
    conn, db_type = get_connection()
    cursor = None
    try:
        cursor = conn.cursor()
        ph = "%s" if db_type == "postgres" else "?"
        now = datetime.utcnow().isoformat()
        
        sql_fetch = f"SELECT * FROM orders WHERE id = {ph}"
        cursor.execute(sql_fetch, (str(order_id),))
        order = _dict_row(cursor.fetchone())
        if not order:
            return False, "Order not found.", None
            
        if str(order['buyer_id']) != str(buyer_id):
            return False, "Unauthorized action.", None
            
        if order['status'] != 'Accepted':
            return False, f"Cannot confirm receipt for an order with status '{order['status']}'.", order
            
        val_db = True if db_type == "postgres" else 1
        sql_update = f"""
            UPDATE orders 
            SET buyer_confirmed_receipt = {ph}, 
                updated_at = {ph} 
            WHERE id = {ph}
        """
        cursor.execute(sql_update, (val_db, now, str(order_id)))
        
        valid_buyer_id = _valid_user_id_or_none(cursor, buyer_id, ph)
        hid = str(uuid.uuid4())
        sql_hist = f"""
            INSERT INTO order_status_history (id, order_id, previous_status, new_status, updated_by_id, updated_by_role, notes, created_at)
            VALUES ({ph}, {ph}, 'Accepted', 'BUYER_RECEIVED', {ph}, 'buyer', 'Buyer confirmed receipt of crop order.', {ph})
        """
        cursor.execute(sql_hist, (hid, str(order_id), valid_buyer_id, now))
        
        conn.commit()
        
        cursor.execute(sql_fetch, (str(order_id),))
        updated_order = _dict_row(cursor.fetchone())
        return True, "Order receipt confirmed by buyer.", updated_order
    except Exception as e:
        print("[!] Error in buyer_confirm_order_received_atomic:", e)
        try: conn.rollback()
        except: pass
        return False, f"Server error: {e}", None
    finally:
        release_connection(conn, cursor)
