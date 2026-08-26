import unittest
import uuid
import db
import services.email_service as email_service
from app import app

class Phase4TestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        db.init_db()

        # Seed test Farmer and Buyer users
        self.farmer_email = f"farmer_p4_{uuid.uuid4().hex[:6]}@test.com"
        self.farmer_id = db.create_user(self.farmer_email, "hash", "farmer", name="Phase4 Farmer", location="Erode", phone="9876543210")
        db.update_email_verified(self.farmer_id, True)

        self.buyer_email = f"buyer_p4_{uuid.uuid4().hex[:6]}@test.com"
        self.buyer_id = db.create_user(self.buyer_email, "hash", "buyer", name="Phase4 Buyer", location="Chennai", phone="9123456789")
        db.update_email_verified(self.buyer_id, True)

        # Seed test Crop listing
        self.crop_id = db.create_crop(
            farmer_id=self.farmer_id,
            crop_name="Rice",
            quantity=100.0,
            price_per_kg=30.0,
            location="Erode"
        )

    def test_1_new_order_creation_and_notification(self):
        """Test placing a new order creates Pending status and logs email notification."""
        with self.client.session_transaction() as sess:
            sess['buyer_user'] = {'id': self.buyer_id, 'email': self.buyer_email, 'role': 'buyer', 'name': 'Phase4 Buyer'}

        res = self.client.post('/place_order', data={'crop_id': self.crop_id, 'quantity': '20'})
        self.assertEqual(res.status_code, 302)

        orders = db.get_orders_for_buyer(self.buyer_id)
        self.assertEqual(len(orders), 1)
        order = orders[0]
        self.assertEqual(order['status'], 'Pending')
        self.assertEqual(float(order['quantity']), 20.0)
        self.assertEqual(float(order['total_price']), 600.0)

        # Server-side Privacy check for Pending order
        self.assertIsNone(order['farmer_phone'])
        self.assertIsNone(order['farmer_email'])

        # Check email notification log
        notifs = db.get_email_notifications_for_order(order['id'])
        self.assertTrue(len(notifs) >= 1)
        self.assertEqual(notifs[0]['notification_type'], 'NEW_ORDER')

    def test_2_order_acceptance_stock_reduction_and_contact_unmasking(self):
        """Test accepting order atomically reduces stock, updates status, and unmasks farmer contact."""
        order_id = db.create_order(
            buyer_id=self.buyer_id,
            farmer_id=self.farmer_id,
            crop_id=self.crop_id,
            crop_name="Rice",
            quantity=30.0,
            total_price=900.0
        )

        with self.client.session_transaction() as sess:
            sess['farmer_user'] = {'id': self.farmer_id, 'email': self.farmer_email, 'role': 'farmer', 'name': 'Phase4 Farmer'}

        res = self.client.get(f'/accept_order/{order_id}')
        self.assertEqual(res.status_code, 302)

        # Verify crop stock reduced from 100 to 70
        crop = db.get_crop_by_id(self.crop_id)
        self.assertEqual(float(crop['quantity']), 70.0)

        # Verify order status is Accepted
        orders = db.get_orders_for_buyer(self.buyer_id)
        order = next(o for o in orders if str(o['id']) == str(order_id))
        self.assertEqual(order['status'], 'Accepted')

        # Verify Farmer Contact details are now unmasked for buyer
        self.assertIsNotNone(order['farmer_email'])
        self.assertIsNotNone(order['farmer_phone'])

        # Verify acceptance email notification log
        notifs = db.get_email_notifications_for_order(order_id)
        acc_notifs = [n for n in notifs if n['notification_type'] == 'ORDER_ACCEPTED']
        self.assertTrue(len(acc_notifs) >= 1)

    def test_3_order_rejection_workflow(self):
        """Test rejecting order updates status without stock reduction."""
        order_id = db.create_order(
            buyer_id=self.buyer_id,
            farmer_id=self.farmer_id,
            crop_id=self.crop_id,
            crop_name="Rice",
            quantity=15.0,
            total_price=450.0
        )

        with self.client.session_transaction() as sess:
            sess['farmer_user'] = {'id': self.farmer_id, 'email': self.farmer_email, 'role': 'farmer'}

        res = self.client.get(f'/reject_order/{order_id}')
        self.assertEqual(res.status_code, 302)

        # Verify stock remains 100
        crop = db.get_crop_by_id(self.crop_id)
        self.assertEqual(float(crop['quantity']), 100.0)

        # Verify order status is Rejected
        orders = db.get_orders_for_buyer(self.buyer_id)
        order = next(o for o in orders if str(o['id']) == str(order_id))
        self.assertEqual(order['status'], 'Rejected')
        self.assertIsNone(order['farmer_phone'])

    def test_4_duplicate_action_protection(self):
        """Test calling accept on an already accepted order prevents double stock reduction."""
        order_id = db.create_order(
            buyer_id=self.buyer_id,
            farmer_id=self.farmer_id,
            crop_id=self.crop_id,
            crop_name="Rice",
            quantity=25.0,
            total_price=750.0
        )

        # First acceptance
        success1, msg1 = db.accept_order_atomic(order_id, self.farmer_id)
        self.assertTrue(success1)
        self.assertEqual(float(db.get_crop_by_id(self.crop_id)['quantity']), 75.0)

        # Second acceptance attempt
        success2, msg2 = db.accept_order_atomic(order_id, self.farmer_id)
        self.assertFalse(success2)
        self.assertIn("already accepted", msg2.lower())
        # Stock should remain 75.0 (no double drop)
        self.assertEqual(float(db.get_crop_by_id(self.crop_id)['quantity']), 75.0)

    def test_5_insufficient_stock_protection(self):
        """Test accepting an order exceeding available quantity fails gracefully."""
        large_order_id = db.create_order(
            buyer_id=self.buyer_id,
            farmer_id=self.farmer_id,
            crop_id=self.crop_id,
            crop_name="Rice",
            quantity=500.0,
            total_price=15000.0
        )

        success, msg = db.accept_order_atomic(large_order_id, self.farmer_id)
        self.assertFalse(success)
        self.assertIn("insufficient stock", msg.lower())
        # Stock remains 100
        self.assertEqual(float(db.get_crop_by_id(self.crop_id)['quantity']), 100.0)

    def test_6_order_completion_workflow(self):
        """Test completing an accepted order."""
        order_id = db.create_order(
            buyer_id=self.buyer_id,
            farmer_id=self.farmer_id,
            crop_id=self.crop_id,
            crop_name="Rice",
            quantity=10.0,
            total_price=300.0
        )
        db.accept_order_atomic(order_id, self.farmer_id)

        with self.client.session_transaction() as sess:
            sess['buyer_user'] = {'id': self.buyer_id, 'email': self.buyer_email, 'role': 'buyer'}

        res = self.client.get(f'/complete_order/{order_id}')
        self.assertEqual(res.status_code, 302)

        orders = db.get_orders_for_buyer(self.buyer_id)
        order = next(o for o in orders if str(o['id']) == str(order_id))
        self.assertEqual(order['status'], 'Completed')

    def test_7_authorization_security(self):
        """Test unauthorized farmer cannot accept another farmer's order."""
        other_farmer_id = db.create_user(f"other_farmer_{uuid.uuid4().hex[:6]}@test.com", "hash", "farmer")
        order_id = db.create_order(
            buyer_id=self.buyer_id,
            farmer_id=self.farmer_id,
            crop_id=self.crop_id,
            crop_name="Rice",
            quantity=10.0,
            total_price=300.0
        )

        success, msg = db.accept_order_atomic(order_id, other_farmer_id)
        self.assertFalse(success)
        self.assertIn("unauthorized", msg.lower())

if __name__ == '__main__':
    unittest.main()
