import unittest
import json
import db
from app import app
from services.satellite_service import fetch_satellite_field_analytics
from services.ai_service import get_regenerative_crop_recommendation

class TestPhase6SatelliteDPG(unittest.TestCase):

    def setUp(self):
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-key'
        self.client = app.test_client()
        db.init_db()

    def test_satellite_field_analytics_fetching(self):
        """Test Sentinel-2 satellite NDVI and soil organic carbon metric generation."""
        res = fetch_satellite_field_analytics('Coimbatore')
        self.assertTrue(res.get('success'))
        self.assertEqual(res.get('location'), 'Coimbatore')
        self.assertIn('ndvi', res)
        self.assertIn('ndwi', res)
        self.assertIn('soil_organic_carbon_pct', res)
        self.assertIn('biomass_status', res)

    def test_regenerative_crop_recommendation(self):
        """Test AI regenerative crop plan generation in English & Tamil."""
        res_en = get_regenerative_crop_recommendation('Thanjavur', 'Paddy', language='en')
        self.assertTrue(res_en.get('success'))
        self.assertIn('regenerative_advisory', res_en)
        self.assertIn('Soil Organic Carbon', res_en['regenerative_advisory'])

        res_ta = get_regenerative_crop_recommendation('Madurai', 'Cotton', language='ta')
        self.assertTrue(res_ta.get('success'))
        self.assertIn('செயற்கைகோள்', res_ta['regenerative_advisory'])

    def test_ai_satellite_endpoint_authenticated(self):
        """Test GET request to /ai/satellite route."""
        with self.client as c:
            with c.session_transaction() as sess:
                sess['farmer_user'] = {'id': 'test-sat-id', 'email': 'sat_farmer@test.com'}

            res = c.get('/ai/satellite?location=Salem&crop_name=Maize')
            self.assertEqual(res.status_code, 200)
            data = json.loads(res.data)
            self.assertTrue(data.get('success'))
            self.assertEqual(data.get('location'), 'Salem')

    def test_dpg_open_agro_advisory_api(self):
        """Test open DPG API /api/v1/dpg/agro_advisory for cross-state cooperation."""
        res = self.client.get('/api/v1/dpg/agro_advisory?location=Coimbatore&crop_name=Rice')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data.get('dpg_spec'), 'CropSync Digital Public Good Standard v1.0')
        self.assertIn('weather_advisory', data)
        self.assertIn('regenerative_advisory', data)

    def test_dpg_open_disease_intelligence_api(self):
        """Test open DPG API /api/v1/dpg/disease_intelligence."""
        res = self.client.get('/api/v1/dpg/disease_intelligence')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertIn('disease_intelligence', data)
        self.assertTrue(len(data['disease_intelligence']) > 0)

    def test_dpg_open_satellite_analytics_api(self):
        """Test open DPG API /api/v1/dpg/satellite_analytics."""
        res = self.client.get('/api/v1/dpg/satellite_analytics?location=Erode')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data.get('location'), 'Erode')
        self.assertIn('satellite_data', data)

if __name__ == '__main__':
    unittest.main()
