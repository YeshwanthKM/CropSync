import unittest
import os
import sys

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import app
import db

class Phase3TestCase(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        db.init_db()
        db.seed_government_msp_data()

    def test_price_trends_removed(self):
        """Verify price trends endpoints return 404 Not Found."""
        res_pt = self.app.get('/price-trends')
        self.assertEqual(res_pt.status_code, 404)

        res_api = self.app.get('/api/price-trends')
        self.assertEqual(res_api.status_code, 404)

    def test_government_msp_seeding(self):
        """Verify all 12 official Government MSP references are seeded correctly."""
        msps = db.get_all_msp_references()
        self.assertGreaterEqual(len(msps), 12)
        
        rice_msp = db.get_msp_by_crop('Rice')
        self.assertIsNotNone(rice_msp)
        self.assertEqual(float(rice_msp['msp_price_per_kg']), 21.83)

        wheat_msp = db.get_msp_by_crop('Wheat')
        self.assertIsNotNone(wheat_msp)
        self.assertEqual(float(wheat_msp['msp_price_per_kg']), 22.75)

    def test_admin_dashboard_stats(self):
        """Verify Admin Dashboard returns live statistical counters."""
        stats = db.get_admin_dashboard_stats()
        self.assertIn('total_farmers', stats)
        self.assertIn('total_buyers', stats)
        self.assertIn('active_listings', stats)
        self.assertIn('total_listed_qty', stats)
        self.assertIn('pending_orders', stats)
        self.assertIn('accepted_orders', stats)

    def test_admin_route_security(self):
        """Verify non-admin requests to /admin/* are rejected/redirected."""
        res = self.app.get('/admin')
        self.assertIn(res.status_code, (302, 403))

        res_listings = self.app.get('/admin/listings')
        self.assertIn(res_listings.status_code, (302, 403))

        res_orders = self.app.get('/admin/orders')
        self.assertIn(res_orders.status_code, (302, 403))

        res_msp = self.app.get('/admin/msp')
        self.assertIn(res_msp.status_code, (302, 403))

    def test_atomic_stock_reduction(self):
        """Test atomic order acceptance and stock safety reduction."""
        # 1. Create farmer and buyer users
        farmer_id = db.create_user('test_f3@cropsync.com', 'hash', 'farmer', 'Test Farmer 3', location='Coimbatore', email_verified=True)
        buyer_id = db.create_user('test_b3@cropsync.com', 'hash', 'buyer', 'Test Buyer 3', location='Chennai', email_verified=True)

        # 2. Farmer creates crop listing with 100 kg
        crop_id = db.create_crop(farmer_id, 'Rice', 100.0, 25.0, 'Coimbatore')
        
        # 3. Buyer places order for 40 kg
        order_id = db.create_order(buyer_id, farmer_id, crop_id, 'Rice', 40.0, 1000.0)

        # 4. Farmer accepts order atomically
        success, msg = db.accept_order_atomic(order_id, farmer_id)
        self.assertTrue(success)

        # 5. Check remaining stock (100 - 40 = 60 kg)
        crop = db.get_crop_by_id(crop_id)
        self.assertEqual(float(crop['quantity']), 60.0)
        self.assertEqual(crop['status'], 'available')

        # 6. Buyer places order for remaining 60 kg
        order_id_2 = db.create_order(buyer_id, farmer_id, crop_id, 'Rice', 60.0, 1500.0)
        success_2, msg_2 = db.accept_order_atomic(order_id_2, farmer_id)
        self.assertTrue(success_2)

        # 7. Check stock reached 0 kg and status auto-updated to 'sold'
        crop_final = db.get_crop_by_id(crop_id)
        self.assertEqual(float(crop_final['quantity']), 0.0)
        self.assertEqual(crop_final['status'], 'sold')

        # 8. Attempting to accept another order over stock should fail
        order_id_fail = db.create_order(buyer_id, farmer_id, crop_id, 'Rice', 10.0, 250.0)
        success_fail, msg_fail = db.accept_order_atomic(order_id_fail, farmer_id)
        self.assertFalse(success_fail)

    def test_admin_msp_management(self):
        """Test Admin saving and toggling MSP references."""
        success = db.save_msp_reference('Custom Crop', 50.0, 'Custom Cat', 'Kharif', 2025)
        self.assertTrue(success)

        custom_msp = db.get_msp_by_crop('Custom Crop')
        self.assertIsNotNone(custom_msp)
        self.assertEqual(float(custom_msp['msp_price_per_kg']), 50.0)

        toggle_ok = db.toggle_msp_status('Custom Crop', 'inactive')
        self.assertTrue(toggle_ok)

        custom_msp_updated = db.get_msp_by_crop('Custom Crop')
        self.assertEqual(custom_msp_updated['status'], 'inactive')

if __name__ == '__main__':
    unittest.main()
