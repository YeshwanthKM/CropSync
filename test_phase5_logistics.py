import unittest
import uuid
from app import app
import db
import services.email_service as email_service

class Phase5LogisticsTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        db.init_db()
        db.ensure_seed_users()
        db.ensure_seed_logistics_user()

    def test_1_prototype_logistics_login(self):
        """Test prototype account logistics@cropsync.com can log in."""
        resp = self.client.post('/login', data={
            'email': 'logistics@cropsync.com',
            'password': 'logistics123'
        }, follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/logistics/dashboard', resp.location)

    def test_2_public_registration_guard(self):
        """Test public registration with logistics role is blocked."""
        resp = self.client.post('/register', data={
            'email': 'hacker_logistics@test.com',
            'password': 'password123',
            'name': 'Hacker Logistics',
            'role': 'logistics'
        }, follow_redirects=True)
        self.assertIn(b'Invalid registration role.', resp.data)

    def test_3_admin_user_creation_for_logistics(self):
        """Test admin can create a new logistics user account."""
        # Login as admin
        self.client.post('/login', data={'email': 'admin@cropsync.com', 'password': 'admin123'})
        
        # Create logistics user
        unique_email = f"logistics_{uuid.uuid4().hex[:6]}@cropsync.com"
        resp = self.client.post('/admin/create_user', data={
            'role': 'logistics',
            'name': 'Express Cargo',
            'email': unique_email,
            'password': 'logistics123pass',
            'phone': '9876543210',
            'organization': 'Express Freight Ltd',
            'location': 'Mumbai',
            'address': 'Terminal 2, Cargo Complex'
        }, follow_redirects=False)
        
        self.assertEqual(resp.status_code, 302)
        user = db.get_user_by_email(unique_email)
        self.assertIsNotNone(user)
        self.assertEqual(user['role'], 'logistics')

    def test_4_logistics_order_creation_and_fields(self):
        """Test placing an order with Logistics Partner computes fees and COD correctly."""
        # Setup farmer and crop
        farmer_id = db.create_user('farmer_log_test@test.com', 'hash', 'farmer', 'Farmer Log', status='active', email_verified=True)
        crop_id = db.create_crop(farmer_id, 'Organic Wheat', 500.0, 30.0, 'Punjab')
        buyer_id = db.create_user('buyer_log_test@test.com', 'hash', 'buyer', 'Buyer Log', status='active', email_verified=True)

        # Place order with Logistics Partner
        order_id = db.create_order(
            buyer_id=buyer_id,
            farmer_id=farmer_id,
            crop_id=crop_id,
            crop_name='Organic Wheat',
            quantity=100.0,
            total_price=3000.0,
            fulfillment_method='Logistics Partner',
            logistics_fee=150.0,
            cod_amount=3150.0,
            farmer_settlement_amount=3000.0,
            pickup_address='Punjab Farm Hub',
            delivery_address='Delhi Central Store'
        )

        order = db.get_logistics_order_by_id(order_id)
        self.assertIsNotNone(order)
        self.assertEqual(order['fulfillment_method'], 'Logistics Partner')
        self.assertEqual(float(order['logistics_fee']), 150.0)
        self.assertEqual(float(order['cod_amount']), 3150.0)
        self.assertEqual(float(order['farmer_settlement_amount']), 3000.0)
        self.assertEqual(order['logistics_status'], 'LOGISTICS_REQUESTED')
        self.assertEqual(order['payment_status'], 'pending')
        self.assertEqual(order['settlement_status'], 'UNSETTLED')

    def test_5_sequential_state_machine_and_validation(self):
        """Test full state machine progression and invalid transition protection."""
        farmer_id = db.create_user('farmer_sm@test.com', 'hash', 'farmer', 'Farmer SM', status='active')
        crop_id = db.create_crop(farmer_id, 'Rice', 200.0, 40.0, 'Haryana')
        buyer_id = db.create_user('buyer_sm@test.com', 'hash', 'buyer', 'Buyer SM', status='active')
        
        order_id = db.create_order(
            buyer_id=buyer_id, farmer_id=farmer_id, crop_id=crop_id,
            crop_name='Rice', quantity=50.0, total_price=2000.0,
            fulfillment_method='Logistics Partner', logistics_fee=150.0,
            cod_amount=2150.0, farmer_settlement_amount=2000.0
        )

        # 1. Invalid direct transition (LOGISTICS_REQUESTED -> SETTLED) should fail
        success, msg, _ = db.update_logistics_order_status_atomic(order_id, 'SETTLED', 'logistics1')
        self.assertFalse(success)
        self.assertIn('Invalid status transition', msg)

        # 2. Valid sequential transitions through delivery
        transitions = [
            'PICKUP_SCHEDULED',
            'PICKED_UP',
            'IN_TRANSIT',
            'OUT_FOR_DELIVERY',
            'DELIVERED',
            'SETTLEMENT_PENDING'
        ]

        for target_status in transitions:
            success, msg, updated = db.update_logistics_order_status_atomic(order_id, target_status, 'logistics1')
            self.assertTrue(success, f"Failed at transition {target_status}: {msg}")
            self.assertEqual(updated['logistics_status'], target_status)

        # 3. Farmer confirms receipt of payment
        f_success, f_msg, final_order = db.farmer_confirm_payment_received_atomic(order_id, farmer_id)
        self.assertTrue(f_success, f"Farmer payment confirmation failed: {f_msg}")
        self.assertEqual(final_order['logistics_status'], 'SETTLED')
        self.assertEqual(final_order['payment_status'], 'paid')
        self.assertEqual(final_order['settlement_status'], 'SETTLED')
        self.assertEqual(final_order['status'], 'Completed')

    def test_6_logistics_rbac_guard(self):
        """Test unauthorized users cannot access logistics endpoints."""
        # Unauthenticated request
        resp = self.client.get('/logistics/dashboard')
        self.assertEqual(resp.status_code, 403)

        # Buyer request
        self.client.post('/login', data={'email': 'buyer1@gmail.com', 'password': 'buyer123'})
        resp = self.client.get('/logistics/dashboard')
        self.assertEqual(resp.status_code, 403)

    def test_7_email_notification_dispatch_logging(self):
        """Test logistics milestone email dispatch creates audit records in email_notifications."""
        farmer_id = db.create_user('farmer_email_t@test.com', 'hash', 'farmer', 'Farmer Mail', status='active', email_verified=True)
        crop_id = db.create_crop(farmer_id, 'Pulses', 100.0, 50.0, 'MP')
        buyer_id = db.create_user('buyer_email_t@test.com', 'hash', 'buyer', 'Buyer Mail', status='active', email_verified=True)
        
        order_id = db.create_order(
            buyer_id=buyer_id, farmer_id=farmer_id, crop_id=crop_id,
            crop_name='Pulses', quantity=10.0, total_price=500.0,
            fulfillment_method='Logistics Partner', logistics_fee=150.0,
            cod_amount=650.0, farmer_settlement_amount=500.0
        )

        _, _, updated_order = db.update_logistics_order_status_atomic(order_id, 'PICKUP_SCHEDULED', 'logistics1')
        email_service.dispatch_logistics_milestone_emails(updated_order, 'PICKUP_SCHEDULED')

        notifications = db.get_email_notifications_for_order(order_id)
        self.assertGreater(len(notifications), 0)
        types = [n['notification_type'] for n in notifications]
        self.assertIn('PICKUP_SCHEDULED', types)

if __name__ == '__main__':
    unittest.main()
