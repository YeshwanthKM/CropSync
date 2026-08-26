import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import db


def verify_live_db():
    print("=== Testing Database Connection & Tables ===")
    conn, db_type = db.get_connection()
    cursor = conn.cursor()
    print("Database Type:", db_type)

    # 1. Inspect crops table
    cursor.execute("SELECT id, farmer_id, crop_name, quantity, price_per_kg, location, status, created_at FROM crops")
    crops = [_dict_row(r) for r in cursor.fetchall()]
    print(f"Total Crops in 'crops' table: {len(crops)}")
    for c in crops:
        print(" Crop:", c)

    # 2. Inspect crop_price_history table
    cursor.execute("SELECT id, crop_id, crop_name, location, price_per_kg, recorded_at FROM crop_price_history")
    history = [_dict_row(r) for r in cursor.fetchall()]
    print(f"Total History Records in 'crop_price_history' table: {len(history)}")
    for h in history:
        print(" History:", h)

    # 3. Test sync_existing_crops_to_history() directly
    print("\nExecuting sync_existing_crops_to_history()...")
    db.sync_existing_crops_to_history()

    cursor.execute("SELECT count(*) FROM crop_price_history")
    count = cursor.fetchone()[0]
    print(f"Total History Records after sync: {count}")

    # 4. Test get_crop_price_trends('Rice')
    print("\nTesting get_crop_price_trends('Rice'):")
    trends = db.get_crop_price_trends('Rice', 'All Locations', '30d')
    print("Trends Result:", trends)

    conn.close()

def _dict_row(row):
    if row is None: return None
    d = dict(row) if not isinstance(row, dict) else row.copy()
    return d

if __name__ == '__main__':
    verify_live_db()
