import os
import unittest
import json
import db
import services.ai_service as ai_service
from app import app

class TestPhase3PriceTrends(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db.init_db()
        cls.app = app
        cls.app.config['TESTING'] = True
        cls.client = cls.app.test_client()

        # Create test farmer user
        cls.farmer_email = "farmer_price_test@example.com"
        existing = db.get_user_by_email(cls.farmer_email)
        if existing:
            cls.farmer_id = existing['id']
            cls.farmer_user = existing
        else:
            cls.farmer_id = db.create_user(
                email=cls.farmer_email,
                password_hash="testpass123",
                role="farmer",
                name="Price Trend Farmer",
                phone="9988112233",
                location="Coimbatore"
            )
            cls.farmer_user = db.get_user_by_id(cls.farmer_id)

    def test_01_mandi_db_persistence(self):
        """Test DB saving and retrieving Mandi price benchmarks."""
        success, mid = db.save_mandi_price(
            crop_name="Cotton",
            min_price=68.0,
            max_price=75.0,
            modal_price=72.0,
            msp_benchmark=66.20,
            district="Coimbatore",
            state="Tamil Nadu",
            trend="UP",
            predicted_change_pct=5.2,
            recommendation="Textile industry buying aggressively"
        )
        self.assertTrue(success)
        self.assertIsNotNone(mid)

        trend_item = db.get_mandi_price_trends(crop_name="Cotton")
        self.assertIsNotNone(trend_item)
        self.assertEqual(float(trend_item['modal_price']), 72.0)
        self.assertEqual(trend_item['trend'], "UP")

    def test_02_ai_service_price_trend_english(self):
        """Test ai_service.predict_crop_price_trend in English."""
        res = ai_service.predict_crop_price_trend("Rice", district="Coimbatore", language="en")
        self.assertTrue(res['success'])
        self.assertEqual(res['crop_name'], "Rice")
        self.assertIn("modal_price", res)
        self.assertIn("msp_benchmark", res)
        self.assertIn("recommendation", res)
        self.assertIn("market_analysis", res)

    def test_03_ai_service_price_trend_tamil(self):
        """Test ai_service.predict_crop_price_trend in Tamil."""
        res = ai_service.predict_crop_price_trend("Wheat", district="Coimbatore", language="ta")
        self.assertTrue(res['success'])
        self.assertEqual(res['crop_name'], "Wheat")
        self.assertEqual(res['language'], 'ta')
        self.assertIn("சந்தை", res['market_analysis'])

    def test_04_price_trend_endpoint_unauthorized(self):
        """Test /ai/price_trend blocks unauthorized users."""
        response = self.client.get('/ai/price_trend?crop_name=Rice')
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertFalse(data['success'])

    def test_05_price_trend_endpoint_success(self):
        """Test /ai/price_trend returns valid JSON for authenticated farmer."""
        with self.client.session_transaction() as sess:
            sess['farmer_user'] = self.farmer_user
            sess['farmer_lang'] = 'en'

        response = self.client.get('/ai/price_trend?crop_name=Maize')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['crop_name'], 'Maize')
        self.assertTrue(float(data['modal_price']) > 0)

if __name__ == '__main__':
    unittest.main()
