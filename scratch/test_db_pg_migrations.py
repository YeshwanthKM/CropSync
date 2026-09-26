import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import db

def test_init():
    print("Initializing database...")
    db.init_db()
    conn, db_type = db.get_connection()
    cursor = conn.cursor()
    print(f"Connected to {db_type}")
    
    if db_type != 'postgres':
        cursor.execute("PRAGMA table_info(orders)")
        cols = [r[1] for r in cursor.fetchall()]
        print("Orders table columns in SQLite:", cols)
        required = [
            'fulfillment_method', 'logistics_partner_id', 'logistics_partner_name',
            'logistics_status', 'logistics_fee', 'cod_amount', 'farmer_settlement_amount',
            'settlement_status', 'pickup_address', 'delivery_address', 'payment_status'
        ]
        for col in required:
            assert col in cols, f"Missing column: {col}"
        print("[SUCCESS] All required order columns are present in SQLite!")
    conn.close()

if __name__ == '__main__':
    test_init()
