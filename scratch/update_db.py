import re

with open("db.py", "r") as f:
    content = f.read()

# 1. Add logistics_profiles table DDL to Postgres section
postgres_ddl_addition = """
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
"""

if "CREATE TABLE IF NOT EXISTS logistics_profiles" not in content:
    content = content.replace("CREATE TABLE IF NOT EXISTS farmer_profiles (", postgres_ddl_addition + "\n                CREATE TABLE IF NOT EXISTS farmer_profiles (")

# 2. Add logistics_profiles table DDL to SQLite section
sqlite_ddl_addition = """
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
"""

if "CREATE TABLE IF NOT EXISTS logistics_profiles" not in content.split("else:")[1]:
    content = content.replace("CREATE TABLE IF NOT EXISTS farmer_profiles (", sqlite_ddl_addition + "\n                CREATE TABLE IF NOT EXISTS farmer_profiles (", 1)

# 3. Add column migrations for orders in init_db
order_column_migrations = """
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
"""

if "Order Logistics Column Migrations" not in content:
    content = content.replace("conn.commit()", order_column_migrations + "\n            conn.commit()", 1)

with open("db.py", "w") as f:
    f.write(content)

print("[+] db.py DDL updated.")
