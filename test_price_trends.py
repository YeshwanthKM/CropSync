import unittest
import json
import uuid
import db
from app import app

class TestCropPriceTrends(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_01_record_price_observation_on_listing_creation_and_update(self):
        """Verify price observation is recorded when listing is created and updated, but NOT on page views."""
        # Setup farmer
        farmer_email = f"trend_farmer_{uuid.uuid4().hex[:6]}@test.com"
        farmer_id = db.create_user(farmer_email, "pass123", "farmer", "Trend Farmer", phone="9876543210", location="Salem", status="active", email_verified=True, phone_verified=True)


        initial_trends = db.get_crop_price_trends("Rice", "Salem", "30d")
        initial_obs = initial_trends['total_observations'] if initial_trends['has_data'] else 0

        # Create crop listing: Rice, 500kg, ₹34/kg, Salem
        crop_id = db.create_crop(farmer_id, "Rice", 500, 34.0, "Salem")
        self.assertIsNotNone(crop_id)

        # Retrieve price trends -> Should have +1 observation
        trends1 = db.get_crop_price_trends("Rice", "Salem", "30d")
        self.assertTrue(trends1['has_data'])
        self.assertEqual(trends1['total_observations'], initial_obs + 1)
        self.assertEqual(trends1['min_price'], 34.0)

        # Update crop price to ₹38/kg
        db.update_crop_price(crop_id, farmer_id, 38.0)

        # Retrieve price trends -> Should now have +2 observations relative to initial
        trends2 = db.get_crop_price_trends("Rice", "Salem", "30d")
        self.assertTrue(trends2['has_data'])
        self.assertEqual(trends2['total_observations'], initial_obs + 2)
        self.assertEqual(trends2['min_price'], 34.0)
        self.assertEqual(trends2['max_price'], 38.0)

        # Page view should NOT create duplicate observations
        response = self.app.get('/price-trends?crop=Rice&location=Salem')
        self.assertEqual(response.status_code, 200)

        trends3 = db.get_crop_price_trends("Rice", "Salem", "30d")
        self.assertEqual(trends3['total_observations'], initial_obs + 2)  # Observation count unchanged!


    def test_02_empty_and_insufficient_data_states(self):
        """Verify clear messaging for non-existent crops or locations."""
        trends = db.get_crop_price_trends("NonExistentCrop123", "UnknownCity", "30d")
        self.assertFalse(trends['has_data'])
        self.assertEqual(trends['total_observations'], 0)
        self.assertIn("No CropSync price data available", trends['message'])

    def test_03_price_trends_routes(self):
        """Verify /price-trends HTML page and /api/price-trends JSON endpoint."""
        # HTML Page
        res_html = self.app.get('/price-trends')
        self.assertEqual(res_html.status_code, 200)
        self.assertIn(b'Crop Price Trends', res_html.data)
        self.assertIn(b'CropSync Marketplace Price Trend', res_html.data)

        # API JSON Endpoint
        res_json = self.app.get('/api/price-trends?crop=Rice&location=Salem&period=30d')
        self.assertEqual(res_json.status_code, 200)
        data = json.loads(res_json.data.decode('utf-8'))
        self.assertIn('crop_name', data)
        self.assertIn('period', data)

    def test_04_available_crops_and_locations(self):
        """Verify available dropdown options come from actual database records."""
        crops = db.get_available_trend_crops()
        locations = db.get_available_trend_locations()
        self.assertIsInstance(crops, list)
        self.assertIsInstance(locations, list)
        self.assertGreater(len(crops), 0)
        self.assertGreater(len(locations), 0)

if __name__ == '__main__':
    unittest.main()
