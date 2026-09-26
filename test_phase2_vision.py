import os
import unittest
import io
import json
import base64
import db
import services.ai_service as ai_service
from app import app

class TestPhase2VisionDiagnostics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db.init_db()
        cls.app = app
        cls.app.config['TESTING'] = True
        cls.client = cls.app.test_client()

        # Create test farmer user
        cls.farmer_email = "farmer_vision_test@example.com"
        existing = db.get_user_by_email(cls.farmer_email)
        if existing:
            cls.farmer_id = existing['id']
            cls.farmer_user = existing
        else:
            cls.farmer_id = db.create_user(
                email=cls.farmer_email,
                password_hash="testpass123",
                role="farmer",
                name="Vision Test Farmer",
                phone="9988776655",
                location="Coimbatore"
            )
            cls.farmer_user = db.get_user_by_id(cls.farmer_id)

    def test_01_db_scan_storage(self):
        """Test database storage and retrieval for AI image scans."""
        scan_id = db.save_cropsync_ai_scan(
            user_id=self.farmer_id,
            image_data="",
            disease_name="Test Leaf Spot",
            severity="Mild",
            diagnosis_report="Test report description for leaf spot",
            language="en"
        )
        self.assertIsNotNone(scan_id)

        history = db.get_cropsync_ai_scans_history(self.farmer_id, limit=5)
        self.assertTrue(len(history) > 0)
        latest = history[0]
        self.assertEqual(latest['disease_name'], "Test Leaf Spot")
        self.assertEqual(latest['severity'], "Mild")

    def test_02_ai_service_vision_fallback_english(self):
        """Test ai_service.diagnose_crop_image in English fallback mode."""
        dummy_base64 = "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP"
        res = ai_service.diagnose_crop_image(dummy_base64, language="en")
        self.assertTrue(res['success'])
        self.assertIn("disease_name", res)
        self.assertIn("severity", res)
        self.assertIn("diagnosis_report", res)
        self.assertIn("Leaf Spot", res['disease_name'])

    def test_03_ai_service_vision_fallback_tamil(self):
        """Test ai_service.diagnose_crop_image in Tamil fallback mode."""
        dummy_base64 = "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP"
        res = ai_service.diagnose_crop_image(dummy_base64, language="ta")
        self.assertTrue(res['success'])
        self.assertIn("இலை", res['disease_name'])
        self.assertIn("சிகிச்சை", res['diagnosis_report'])

    def test_04_ai_diagnose_endpoint_unauthorized(self):
        """Test /ai/diagnose route rejects unauthenticated users."""
        response = self.client.post('/ai/diagnose', json={"image_data": "test"})
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertFalse(data['success'])

    def test_05_ai_diagnose_endpoint_json_payload(self):
        """Test /ai/diagnose route with logged in session using JSON base64."""
        with self.client.session_transaction() as sess:
            sess['farmer_user'] = self.farmer_user
            sess['farmer_lang'] = 'en'

        dummy_base64 = "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP"
        response = self.client.post('/ai/diagnose', json={"image_data": dummy_base64})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])
        self.assertIsNotNone(data.get('disease_name'))
        self.assertIsNotNone(data.get('severity'))

    def test_06_ai_diagnose_endpoint_file_upload(self):
        """Test /ai/diagnose route with multipart file upload."""
        with self.client.session_transaction() as sess:
            sess['farmer_user'] = self.farmer_user
            sess['farmer_lang'] = 'ta'

        dummy_file = (io.BytesIO(b"fake image bytes data"), "leaf.jpg")
        response = self.client.post(
            '/ai/diagnose',
            data={'image': dummy_file},
            content_type='multipart/form-data'
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data.get('language'), 'ta')

if __name__ == '__main__':
    unittest.main()
