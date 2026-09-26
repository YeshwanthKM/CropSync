import unittest
import json
import os
import db
from app import app
from services.weather_service import fetch_hyperlocal_weather, DISTRICT_WEATHER_BENCHMARKS
from services.ai_service import get_weather_irrigation_recommendation

class TestPhase4WeatherAdvisor(unittest.TestCase):

    def setUp(self):
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-key'
        self.client = app.test_client()
        db.init_db()

    def test_fetch_hyperlocal_weather_fallback(self):
        """Test regional benchmark weather engine fallback for known districts."""
        w_coimbatore = fetch_hyperlocal_weather('Coimbatore')
        self.assertTrue(w_coimbatore.get('success'))
        self.assertEqual(w_coimbatore.get('location'), 'Coimbatore')
        self.assertIn('temp_c', w_coimbatore)
        self.assertIn('humidity', w_coimbatore)
        self.assertIn('rain_prob', w_coimbatore)
        self.assertIn('wind_kmh', w_coimbatore)

        w_thanjavur = fetch_hyperlocal_weather('Thanjavur')
        self.assertTrue(w_thanjavur.get('success'))
        self.assertEqual(w_thanjavur.get('location'), 'Thanjavur')

    def test_ai_weather_recommendation_english(self):
        """Test AI smart irrigation & spraying advisory generation in English."""
        res = get_weather_irrigation_recommendation('Coimbatore', 'Rice', language='en')
        self.assertTrue(res.get('success'))
        self.assertEqual(res.get('location'), 'Coimbatore')
        self.assertIn('irrigation_status', res)
        self.assertIn('spraying_status', res)
        self.assertIn('advisory_report', res)
        self.assertTrue(len(res['advisory_report']) > 20)

    def test_ai_weather_recommendation_tamil(self):
        """Test AI smart irrigation advisory generation in Tamil."""
        res = get_weather_irrigation_recommendation('Thanjavur', 'Paddy', language='ta')
        self.assertTrue(res.get('success'))
        self.assertEqual(res.get('language'), 'ta')
        self.assertIn('வானிலை', res['advisory_report'])

    def test_db_weather_log_persistence(self):
        """Test saving and retrieving weather advisory logs from DB."""
        ok, wid = db.save_weather_log(
            location='Madurai',
            temp_c=34.0,
            humidity=58.0,
            rain_prob=10.0,
            wind_kmh=9.5,
            condition='Sunny',
            irrigation_status='WATER_TODAY',
            spraying_status='SAFE_WINDOW',
            advisory_report='Water crop today due to high heat.'
        )
        self.assertTrue(ok)
        self.assertIsNotNone(wid)

        latest = db.get_latest_weather_log('Madurai')
        self.assertIsNotNone(latest)
        self.assertEqual(latest.get('location'), 'Madurai')
        self.assertEqual(float(latest.get('temp_c')), 34.0)
        self.assertEqual(latest.get('irrigation_status'), 'WATER_TODAY')

    def test_api_weather_endpoint_authenticated(self):
        """Test GET and POST requests to /ai/weather route with authenticated farmer session."""
        with self.client as c:
            with c.session_transaction() as sess:
                sess['farmer_user'] = {'id': 'test-farmer-id', 'email': 'farmer@cropsync.com'}

            # Test GET query
            res_get = c.get('/ai/weather?location=Salem&crop_name=Wheat')
            self.assertEqual(res_get.status_code, 200)
            data_get = json.loads(res_get.data)
            self.assertTrue(data_get.get('success'))
            self.assertEqual(data_get.get('location'), 'Salem')

            # Test POST JSON query
            res_post = c.post('/ai/weather', json={'location': 'Erode', 'crop_name': 'Turmeric'})
            self.assertEqual(res_post.status_code, 200)
            data_post = json.loads(res_post.data)
            self.assertTrue(data_post.get('success'))
            self.assertEqual(data_post.get('location'), 'Erode')

    def test_api_weather_endpoint_unauthorized(self):
        """Test that unauthenticated requests to /ai/weather are rejected with 401."""
        res = self.client.get('/ai/weather?location=Coimbatore')
        self.assertEqual(res.status_code, 401)
        data = json.loads(res.data)
        self.assertFalse(data.get('success'))

if __name__ == '__main__':
    unittest.main()
