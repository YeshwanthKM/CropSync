import unittest
import json
import os
import db
from app import app

class TestCropSyncPhase3(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_database_market_intelligence_seeding_and_query(self):
        """Test db.get_market_intelligence returns correct Rice - Salem trends and MSP benchmarks."""
        intel = db.get_market_intelligence(crop_name='Rice', location='Salem')
        self.assertIsNotNone(intel)
        self.assertEqual(intel['crop_name'], 'Rice')
        self.assertEqual(intel['location'], 'Salem')
        self.assertEqual(intel['govt_msp'], 23.00)
        self.assertEqual(intel['current_avg_price'], 40.00)
        self.assertIn('Mar', intel['months'])
        self.assertIn('Aug', intel['months'])
        self.assertEqual(len(intel['prices']), 6)
        self.assertGreater(intel['msp_variance'], 0)

    def test_market_intelligence_html_route(self):
        """Test /market-intelligence page renders successfully with 200 OK."""
        response = self.app.get('/market-intelligence?crop=Rice&location=Salem')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'CropSync Market Intelligence', response.data)
        self.assertIn(b'Rice', response.data)
        self.assertIn(b'Salem', response.data)
        self.assertIn(b'Government MSP', response.data)

    def test_market_intelligence_api_endpoint(self):
        """Test /api/market-intelligence JSON endpoint returns structured crop analytics."""
        response = self.app.get('/api/market-intelligence?crop=Cotton&location=Tiruppur')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['crop_name'], 'Cotton')
        self.assertEqual(data['location'], 'Tiruppur')
        self.assertEqual(data['govt_msp'], 66.20)
        self.assertEqual(data['current_avg_price'], 84.00)

    def test_market_crops_and_locations_list(self):
        """Test db helper functions return all available crops and locations."""
        crops = db.get_all_market_crops()
        locations = db.get_all_market_locations()
        benchmarks = db.get_all_crop_benchmarks()

        self.assertIn('Rice', crops)
        self.assertIn('Wheat', crops)
        self.assertIn('Salem', locations)
        self.assertIn('Coimbatore', locations)
        self.assertGreater(len(benchmarks), 0)

if __name__ == '__main__':
    unittest.main()
