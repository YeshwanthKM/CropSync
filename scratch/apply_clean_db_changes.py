with open("db.py", "r") as f:
    content = f.read()

# 1. Update users table role CHECK constraint in Postgres & SQLite DDL
content = content.replace(
    "role TEXT CHECK (role IN ('farmer', 'buyer', 'admin')) NOT NULL",
    "role TEXT CHECK (role IN ('farmer', 'buyer', 'admin', 'logistics')) NOT NULL"
)

# 2. Add Postgres DDL for logistics_profiles and order_status_history
pg_profiles_ddl = """
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
content = content.replace("CREATE TABLE IF NOT EXISTS farmer_profiles (", pg_profiles_ddl + "\n                CREATE TABLE IF NOT EXISTS farmer_profiles (", 1)

# 3. Add SQLite DDL for logistics_profiles and order_status_history
sqlite_profiles_ddl = """
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
# Replace the second occurrence (which is inside the SQLite block)
parts = content.split("CREATE TABLE IF NOT EXISTS farmer_profiles (")
if len(parts) >= 3:
    content = parts[0] + "CREATE TABLE IF NOT EXISTS farmer_profiles (" + parts[1] + sqlite_profiles_ddl + "\n                CREATE TABLE IF NOT EXISTS farmer_profiles (" + parts[2]

# 4. Add Order Logistics Column Migrations right before conn.commit() in init_db
order_cols_code = """
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
content = content.replace("conn.commit()", order_cols_code + "\n            conn.commit()", 1)

# 5. Update get_user_by_email and get_user_by_id
content = content.replace("COALESCE(fp.name, bp.name, 'Admin') as name,", "COALESCE(fp.name, bp.name, lp.company_name, 'Admin') as name,")
content = content.replace("COALESCE(fp.phone, bp.phone) as phone,", "COALESCE(fp.phone, bp.phone, lp.phone) as phone,")
content = content.replace("COALESCE(fp.address, bp.address) as address,", "COALESCE(fp.address, bp.address, lp.service_area) as address,")
content = content.replace("COALESCE(fp.location, bp.location) as location,", "COALESCE(fp.location, bp.location, lp.service_area) as location,")
content = content.replace("LEFT JOIN buyer_profiles bp ON u.id = bp.user_id", "LEFT JOIN buyer_profiles bp ON u.id = bp.user_id\n                LEFT JOIN logistics_profiles lp ON u.id = lp.user_id")

# 6. Update create_user for logistics profile creation
logistics_postgres_prof = """            elif role == 'buyer':
                prof_sql = \"\"\"
                    INSERT INTO buyer_profiles (user_id, name, phone, organization, address, location)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (user_id) DO UPDATE SET name = EXCLUDED.name, phone = EXCLUDED.phone, organization = EXCLUDED.organization, location = EXCLUDED.location
                \"\"\"
                cursor.execute(prof_sql, (uid, name, phone, organization, address, location))
            elif role == 'logistics':
                prof_sql = \"\"\"
                    INSERT INTO logistics_profiles (user_id, company_name, phone, service_area)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (user_id) DO UPDATE SET company_name = EXCLUDED.company_name, phone = EXCLUDED.phone, service_area = EXCLUDED.service_area
                \"\"\"
                cursor.execute(prof_sql, (uid, name, phone, address or location or "Pan-India"))"""

content = content.replace("""            elif role == 'buyer':
                prof_sql = \"\"\"
                    INSERT INTO buyer_profiles (user_id, name, phone, organization, address, location)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (user_id) DO UPDATE SET name = EXCLUDED.name, phone = EXCLUDED.phone, organization = EXCLUDED.organization, location = EXCLUDED.location
                \"\"\"
                cursor.execute(prof_sql, (uid, name, phone, organization, address, location))""", logistics_postgres_prof)

logistics_sqlite_prof = """            elif role == 'buyer':
                prof_sql = \"\"\"
                    INSERT INTO buyer_profiles (id, user_id, name, phone, organization, address, location, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                \"\"\"
                cursor.execute(prof_sql, (str(uuid.uuid4()), uid, name, phone, organization, address, location, now, now))
            elif role == 'logistics':
                prof_sql = \"\"\"
                    INSERT INTO logistics_profiles (id, user_id, company_name, phone, service_area, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                \"\"\"
                cursor.execute(prof_sql, (str(uuid.uuid4()), uid, name, phone, address or location or "Pan-India", now, now))"""

content = content.replace("""            elif role == 'buyer':
                prof_sql = \"\"\"
                    INSERT INTO buyer_profiles (id, user_id, name, phone, organization, address, location, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                \"\"\"
                cursor.execute(prof_sql, (str(uuid.uuid4()), uid, name, phone, organization, address, location, now, now))""", logistics_sqlite_prof)

# 7. Update create_order to accept optional logistics parameters
old_create_order = """def create_order(buyer_id, farmer_id, crop_id, crop_name, quantity, total_price, order_id=None):

    conn, db_type = get_connection()
    cursor = None
    try:
        cursor = conn.cursor()
        oid = str(order_id) if order_id else str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        ph = "%s" if db_type == "postgres" else "?"
        sql = f\"\"\"
            INSERT INTO orders (id, crop_id, buyer_id, farmer_id, crop_name, quantity, total_price, status, created_at, updated_at)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, 'Pending', {ph}, {ph})
        \"\"\"
        cursor.execute(sql, (oid, str(crop_id), str(buyer_id), str(farmer_id), crop_name, float(quantity), float(total_price), now, now))
        conn.commit()
        return oid
    finally:
        release_connection(conn, cursor)"""

new_create_order = """def create_order(buyer_id, farmer_id, crop_id, crop_name, quantity, total_price, order_id=None, fulfillment_method='Direct Collection', logistics_fee=0.0, cod_amount=0.0, farmer_settlement_amount=0.0, pickup_address="", delivery_address="", logistics_partner_name="CropSync Logistics"):
    conn, db_type = get_connection()
    cursor = None
    try:
        cursor = conn.cursor()
        oid = str(order_id) if order_id else str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        ph = "%s" if db_type == "postgres" else "?"
        log_status = 'LOGISTICS_REQUESTED' if fulfillment_method == 'Logistics Partner' else 'NONE'
        sql = f\"\"\"
            INSERT INTO orders (id, crop_id, buyer_id, farmer_id, crop_name, quantity, total_price, status, fulfillment_method, logistics_partner_name, logistics_status, logistics_fee, cod_amount, farmer_settlement_amount, payment_status, settlement_status, pickup_address, delivery_address, created_at, updated_at)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, 'Pending', {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, 'UNPAID', 'UNSETTLED', {ph}, {ph}, {ph}, {ph})
        \"\"\"
        cursor.execute(sql, (oid, str(crop_id), str(buyer_id), str(farmer_id), crop_name, float(quantity), float(total_price), fulfillment_method, logistics_partner_name, log_status, float(logistics_fee), float(cod_amount), float(farmer_settlement_amount), pickup_address, delivery_address, now, now))
        conn.commit()
        return oid
    finally:
        release_connection(conn, cursor)"""

content = content.replace(old_create_order, new_create_order)

# 8. Update accept_order_atomic to set logistics_status when accepted
old_accept_sql = "sql_u_order = f\"UPDATE orders SET status = 'Accepted', updated_at = {ph} WHERE id = {ph}\"\n        cursor.execute(sql_u_order, (now, str(order_id)))"
new_accept_sql = """log_status = 'LOGISTICS_REQUESTED' if (order.get('fulfillment_method') == 'Logistics Partner' or order.get('logistics_status') == 'LOGISTICS_REQUESTED') else (order.get('logistics_status') or 'NONE')
        sql_u_order = f"UPDATE orders SET status = 'Accepted', logistics_status = {ph}, updated_at = {ph} WHERE id = {ph}"
        cursor.execute(sql_u_order, (log_status, now, str(order_id)))"""

if old_accept_sql in content:
    content = content.replace(old_accept_sql, new_accept_sql)

# 9. Update ensure_seed_users to call ensure_seed_logistics_user()
content = content.replace("def ensure_seed_users():", "def ensure_seed_users():\n    ensure_seed_logistics_user()\n")

# 10. Append Logistics Functions
logistics_code = '''

# --- LOGISTICS ROLE & FULFILLMENT SERVICES ---

VALID_LOGISTICS_TRANSITIONS = {
    'NONE': ['LOGISTICS_REQUESTED', 'PICKUP_SCHEDULED'],
    'LOGISTICS_REQUESTED': ['PICKUP_SCHEDULED', 'CANCELLED'],
    'PICKUP_SCHEDULED': ['PICKED_UP', 'DELIVERY_FAILED', 'CANCELLED'],
    'PICKED_UP': ['IN_TRANSIT', 'RETURN_TO_FARMER', 'DELIVERY_FAILED'],
    'IN_TRANSIT': ['OUT_FOR_DELIVERY', 'DELIVERY_FAILED', 'RETURN_TO_FARMER'],
    'OUT_FOR_DELIVERY': ['DELIVERED', 'DELIVERY_FAILED', 'RETURN_TO_FARMER'],
    'DELIVERED': ['PAYMENT_COLLECTED', 'SETTLEMENT_PENDING'],
    'PAYMENT_COLLECTED': ['SETTLEMENT_PENDING'],
    'SETTLEMENT_PENDING': ['SETTLED'],
    'SETTLED': [],
    'DELIVERY_FAILED': ['RETURN_TO_FARMER', 'PICKUP_SCHEDULED'],
    'RETURN_TO_FARMER': [],
    'CANCELLED': []
}

def ensure_seed_logistics_user():
    try:
        user = get_user_by_email("logistics@cropsync.com")
        if not user:
            from werkzeug.security import generate_password_hash
            pw_hash = generate_password_hash("logistics123", method='pbkdf2:sha256')
            create_user(
                email="logistics@cropsync.com",
                password_hash=pw_hash,
                role="logistics",
                name="CropSync Logistics",
                phone="+91 9876543210",
                address="National Logistics Hub, Sector 4",
                location="Pan-India",
                organization="CropSync Freight Services",
                status="active",
                email_verified=True,
                phone_verified=True
            )
            print("[+] Seed prototype logistics user (logistics@cropsync.com) initialized.")
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
            WHERE (o.fulfillment_method = 'Logistics Partner' OR (o.logistics_status IS NOT NULL AND o.logistics_status != 'NONE'))
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
        return [_dict_row(r) for r in rows]
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
        return _dict_row(row)
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
            WHERE fulfillment_method = 'Logistics Partner' OR (logistics_status IS NOT NULL AND logistics_status != 'NONE')
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
            update_fields.append(f"status = {ph}") # Update main order status to Completed
            params.extend([now, 'Completed'])
        elif next_status == 'PAYMENT_COLLECTED':
            update_fields.append("payment_status = 'COLLECTED'")
            update_fields.append(f"payment_collected_at = {ph}")
            params.append(now)
        elif next_status == 'SETTLEMENT_PENDING':
            update_fields.append("settlement_status = 'SETTLEMENT_PENDING'")
        elif next_status == 'SETTLED':
            update_fields.append("settlement_status = 'SETTLED'")
            update_fields.append(f"settlement_at = {ph}")
            params.append(now)
            
        params.append(str(order_id))
        sql_update = f"UPDATE orders SET {', '.join(update_fields)} WHERE id = {ph}"
        cursor.execute(sql_update, tuple(params))
        
        # 4. Record entry in order_status_history audit table
        hid = str(uuid.uuid4())
        sql_hist = f"""
            INSERT INTO order_status_history (id, order_id, previous_status, new_status, updated_by_id, updated_by_role, notes, created_at)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
        """
        cursor.execute(sql_hist, (hid, str(order_id), current_status, next_status, str(updated_by_user_id) if updated_by_user_id else None, updated_by_role, notes or f"Status updated to {next_status}", now))
        
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
'''

if "def update_logistics_order_status_atomic" not in content:
    content += "\n" + logistics_code

with open("db.py", "w") as f:
    f.write(content)

print("[+] Clean db.py changes applied successfully.")
