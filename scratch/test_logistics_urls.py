import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app
from flask import url_for

def test_routes():
    with app.test_request_context():
        u1 = url_for('update_logistics_order_status', order_id='test1234')
        u2 = url_for('update_logistics_status', order_id='test1234')
        u3 = url_for('logistics_order_detail', order_id='test1234')
        print(f"URL 1 (update_logistics_order_status): {u1}")
        print(f"URL 2 (update_logistics_status): {u2}")
        print(f"URL 3 (logistics_order_detail): {u3}")
        assert u1 == '/logistics/order/test1234/update_status'
        assert u3 == '/logistics/order/test1234'
        print("[SUCCESS] All logistics routes build without error!")

if __name__ == '__main__':
    test_routes()
