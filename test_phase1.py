import sys
import uuid
import unittest
from app import app
import db

class TestCropSyncPhase1(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        db.init_db()

    def test_01_farmer1_login_and_crop_creation(self):
        # 1. Login with demo farmer credentials
        response = self.client.post('/login', data={
            'email': 'farmer1@gmail.com',
            'password': 'farmer123'
        }, follow_redirects=True)
        self.assertIn(b'Farmer Dashboard', response.data)
        
        # 2. Add a new crop listing (Rice @ 25.0 > MSP 21.83)
        response = self.client.post('/farmer_dashboard', data={
            'crop_name': 'rice',
            'quantity': '100',
            'price_per_kg': '25.0'
        }, follow_redirects=True)
        crops = db.get_crops()
        found = any(c['crop_name'].lower() == 'rice' and float(c['quantity']) == 100 for c in crops)
        self.assertTrue(found, "Newly added crop should be persisted in the database")



    def test_02_buyer1_login_and_order_placement(self):
        # 1. Login with demo buyer credentials
        response = self.client.post('/login', data={
            'email': 'buyer1@gmail.com',
            'password': 'buyer123'
        }, follow_redirects=True)
        self.assertIn(b'Buyer Dashboard', response.data)

        # Get available crops from DB
        crops = db.get_crops()
        self.assertGreater(len(crops), 0, "There should be available crops to order")
        target_crop = crops[0]

        # 2. Place an order for 10 kg
        response = self.client.post('/place_order', data={
            'crop_id': target_crop['id'],
            'quantity': '10'
        }, follow_redirects=True)
        self.assertIn(b'Order placed!', response.data)

        # 3. Verify order is in database
        buyer = db.get_user_by_email('buyer1@gmail.com')
        orders = db.get_orders_for_buyer(buyer['id'])
        self.assertGreater(len(orders), 0, "Buyer should have at least 1 order in database")

    def test_03_admin_login_and_user_creation(self):
        # 1. Login with Admin credentials
        response = self.client.post('/login', data={
            'email': 'admin@cropsync.com',
            'password': 'admin123'
        }, follow_redirects=True)
        self.assertIn(b'System Overview', response.data)

        # 2. Create new Farmer account
        new_farmer_email = f'newfarmer_{uuid.uuid4().hex[:6]}@gmail.com'
        response = self.client.post('/admin/create_user', data={
            'role': 'farmer',
            'name': 'New Test Farmer',
            'email': new_farmer_email,
            'password': 'password123',
            'phone': '9999988888',
            'location': 'Salem'
        }, follow_redirects=True)
        self.assertIn(b'Successfully created new farmer account', response.data)

        # 3. Verify new user can log in
        self.client.get('/logout')
        response = self.client.post('/login', data={
            'email': new_farmer_email,
            'password': 'password123'
        }, follow_redirects=True)
        self.assertIn(b'Farmer Dashboard', response.data)

    def test_04_account_suspension_flow(self):
        # 1. Admin suspends user -> purges user so email can be reused
        user = db.get_user_by_email('farmer2@gmail.com')
        if user:
            db.delete_user(user['id'])

        # 2. Verify user is purged and freed up
        purged = db.get_user_by_email('farmer2@gmail.com')
        self.assertIsNone(purged)


    def test_05_admin_authorization_security(self):
        # 1. Farmer attempts to access /admin -> Access Denied (403)
        self.client.post('/login', data={'email': 'farmer1@gmail.com', 'password': 'farmer123'})
        response = self.client.get('/admin')
        self.assertEqual(response.status_code, 403)

        # 2. Buyer attempts to access /admin -> Access Denied (403)
        self.client.post('/login', data={'email': 'buyer1@gmail.com', 'password': 'buyer123'})
        response = self.client.get('/admin')
        self.assertEqual(response.status_code, 403)

        # 3. Unauthenticated access to /admin -> Access Denied (403)
        self.client.get('/logout')
        response = self.client.get('/admin')
        self.assertEqual(response.status_code, 403)

if __name__ == '__main__':
    unittest.main()
