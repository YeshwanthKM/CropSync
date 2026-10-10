import os
import unittest
import uuid
from datetime import datetime, timedelta
import db

class SubscriptionSystemTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        os.environ['DATABASE_URL'] = ''
        db.init_db()

    def setUp(self):
        self.farmer_email = f"farmer_sub_{uuid.uuid4().hex[:6]}@test.com"
        self.buyer_email = f"buyer_sub_{uuid.uuid4().hex[:6]}@test.com"
        self.admin_email = f"admin_sub_{uuid.uuid4().hex[:6]}@test.com"

        self.farmer_id = db.create_user(
            email=self.farmer_email,
            password_hash="pbkdf2:sha256:fakehash",
            role="farmer",
            name="Test Farmer",
            status="active"
        )
        self.buyer_id = db.create_user(
            email=self.buyer_email,
            password_hash="pbkdf2:sha256:fakehash",
            role="buyer",
            name="Test Buyer",
            status="active"
        )
        self.admin_id = db.create_user(
            email=self.admin_email,
            password_hash="pbkdf2:sha256:fakehash",
            role="admin",
            name="Test Admin",
            status="active"
        )

    # 1. New farmer receives Free plan
    def test_01_new_farmer_receives_free_plan(self):
        sub = db.get_active_subscription(self.farmer_id)
        self.assertIsNotNone(sub)
        self.assertEqual(sub['plan_key'], 'free_farmer')
        self.assertEqual(sub['active_listing_limit'], 5)
        self.assertEqual(sub['access_source'], 'free')

    # 2. New buyer receives Free plan
    def test_02_new_buyer_receives_free_plan(self):
        sub = db.get_active_subscription(self.buyer_id)
        self.assertIsNotNone(sub)
        self.assertEqual(sub['plan_key'], 'free_buyer')
        self.assertEqual(sub['monthly_order_limit'], 5)
        self.assertEqual(sub['access_source'], 'free')

    # 3 & 4. Free farmer can create 5 listings, but 6th is rejected
    def test_03_04_free_farmer_listing_limit_enforcement(self):
        for i in range(5):
            crop_id = db.create_crop(self.farmer_id, f"Crop {i}", 100, 25.0, "Test Location")
            self.assertIsNotNone(crop_id)

        # 5 active listings exist now
        count = db.get_farmer_active_listings_count(self.farmer_id)
        self.assertEqual(count, 5)

        # 6th creation must raise ValueError
        with self.assertRaises(ValueError) as ctx:
            db.create_crop(self.farmer_id, "Crop 6", 100, 25.0, "Test Location")
        self.assertIn("reached the limit of 5 active crop listings", str(ctx.exception))

    # 5. Listing becomes inactive allows new creation
    def test_05_farmer_inactive_listing_allows_new(self):
        crops = []
        for i in range(5):
            crops.append(db.create_crop(self.farmer_id, f"Crop {i}", 100, 25.0, "Test Location"))

        # Mark 1 crop as sold (inactive)
        db.update_crop_quantity(crops[0], 0)
        self.assertEqual(db.get_farmer_active_listings_count(self.farmer_id), 4)

        # Farmer can now create another listing
        new_crop_id = db.create_crop(self.farmer_id, "New Replacement Crop", 100, 30.0, "Test Location")
        self.assertIsNotNone(new_crop_id)
        self.assertEqual(db.get_farmer_active_listings_count(self.farmer_id), 5)

    # 6 & 7. Free buyer order limit enforcement (5 max per month)
    def test_06_07_free_buyer_order_limit_enforcement(self):
        crop_id = db.create_crop(self.farmer_id, "Wheat", 1000, 25.0, "Test Location")

        for i in range(5):
            order_id = db.create_order(self.buyer_id, self.farmer_id, crop_id, "Wheat", 10, 250.0)
            self.assertIsNotNone(order_id)

        count = db.get_buyer_monthly_orders_count(self.buyer_id)
        self.assertEqual(count, 5)

        with self.assertRaises(ValueError) as ctx:
            db.create_order(self.buyer_id, self.farmer_id, crop_id, "Wheat", 10, 250.0)
        self.assertIn("reached your limit of 5 orders this month", str(ctx.exception))

    # 8. Monthly order allowance calculation
    def test_08_monthly_order_calculation(self):
        crop_id = db.create_crop(self.farmer_id, "Rice", 1000, 30.0, "Test Location")
        db.create_order(self.buyer_id, self.farmer_id, crop_id, "Rice", 10, 300.0)
        count = db.get_buyer_monthly_orders_count(self.buyer_id)
        self.assertEqual(count, 1)

    # 9. Farmer Plus applies 20 active listing limit
    def test_09_farmer_plus_limit(self):
        db.assign_user_subscription(self.farmer_id, 'farmer_plus', access_source='admin_grant', action_source='admin_grant')
        sub = db.get_active_subscription(self.farmer_id)
        self.assertEqual(sub['plan_key'], 'farmer_plus')
        self.assertEqual(sub['active_listing_limit'], 20)

        for i in range(6):
            db.create_crop(self.farmer_id, f"Plus Crop {i}", 50, 20.0, "Test Location")
        self.assertEqual(db.get_farmer_active_listings_count(self.farmer_id), 6)

    # 10. Buyer Plus applies 20 monthly order limit
    def test_10_buyer_plus_limit(self):
        db.assign_user_subscription(self.buyer_id, 'buyer_plus', access_source='admin_grant', action_source='admin_grant')
        sub = db.get_active_subscription(self.buyer_id)
        self.assertEqual(sub['plan_key'], 'buyer_plus')
        self.assertEqual(sub['monthly_order_limit'], 20)

        crop_id = db.create_crop(self.farmer_id, "Plus Crop", 1000, 20.0, "Test Location")
        for i in range(6):
            db.create_order(self.buyer_id, self.farmer_id, crop_id, "Plus Crop", 5, 100.0)
        self.assertEqual(db.get_buyer_monthly_orders_count(self.buyer_id), 6)

    # 11 & 13. Admin grant activates immediately and records source
    def test_11_13_admin_grant_activation(self):
        sub = db.grant_admin_subscription(self.admin_id, self.farmer_id, 'farmer_plus', duration_days=30, reason='Support grant')
        self.assertEqual(sub['access_source'], 'admin_grant')
        self.assertEqual(sub['plan_key'], 'farmer_plus')

        history = db.get_user_subscription_history(self.farmer_id)
        self.assertGreater(len(history), 0)
        latest = history[0]
        self.assertEqual(latest['action_source'], 'admin_grant')

    # 12. Unauthorized user cannot grant premium access
    def test_12_unauthorized_admin_grant(self):
        with self.assertRaises(PermissionError):
            db.grant_admin_subscription(self.buyer_id, self.farmer_id, 'farmer_plus')

    # 14. Expired access returns to Free plan
    def test_14_expired_access_fallback(self):
        # Create a subscription that expired yesterday
        conn, db_type = db.get_connection()
        cursor = conn.cursor()
        ph = "%s" if db_type == "postgres" else "?"
        yesterday = (datetime.utcnow() - timedelta(days=1)).isoformat()
        
        plan = db.get_plan_by_key('farmer_plus')
        sub_id = str(uuid.uuid4())
        sql = f"""
            INSERT INTO user_subscriptions (id, user_id, plan_id, plan_key, status, start_date, expiry_date, access_source, created_at, updated_at)
            VALUES ({ph}, {ph}, {ph}, 'farmer_plus', 'active', {ph}, {ph}, 'admin_grant', {ph}, {ph})
        """
        cursor.execute(sql, (sub_id, str(self.farmer_id), plan['id'], yesterday, yesterday, yesterday, yesterday))
        conn.commit()

        # get_active_subscription should auto-expire it and revert to free_farmer
        sub = db.get_active_subscription(self.farmer_id)
        self.assertEqual(sub['plan_key'], 'free_farmer')

    # 15 & 16. Revoking admin grant returns user to free, preserving existing listings
    def test_15_16_revoke_admin_grant(self):
        db.grant_admin_subscription(self.admin_id, self.farmer_id, 'farmer_plus', duration_days=30)
        
        # Create 6 listings
        crops = []
        for i in range(6):
            crops.append(db.create_crop(self.farmer_id, f"Crop {i}", 50, 20.0, "Test Location"))

        # Revoke access
        db.revoke_admin_subscription(self.admin_id, self.farmer_id, reason="Trial end")
        sub = db.get_active_subscription(self.farmer_id)
        self.assertEqual(sub['plan_key'], 'free_farmer')

        # Existing 6 listings remain intact in DB
        self.assertEqual(db.get_farmer_active_listings_count(self.farmer_id), 6)

        # But adding a 7th listing is blocked
        with self.assertRaises(ValueError):
            db.create_crop(self.farmer_id, "Blocked Crop 7", 50, 20.0, "Test Location")

    # 17. Payment preparation & verification test
    def test_17_payment_checkout_and_verify(self):
        order = db.create_payment_order(self.farmer_id, 'farmer_plus')
        self.assertEqual(order['amount'], 99.0)
        self.assertEqual(order['status'], 'created')

        success, msg, sub = db.verify_and_activate_payment_subscription(
            user_id=self.farmer_id,
            plan_key='farmer_plus',
            gateway_order_id=order['gateway_order_id'],
            gateway_payment_id='pay_test_123456',
            signature_valid=True
        )
        self.assertTrue(success)
        self.assertEqual(sub['access_source'], 'payment')
        self.assertEqual(sub['plan_key'], 'farmer_plus')

if __name__ == '__main__':
    unittest.main()
