import unittest
import os
import sys
import uuid

sys.path.insert(0, '/Users/yeshwanth/Documents/Projects/CropSync')
import db
import app as flask_app
import services.ai_service as ai_service

class TestCropSyncAI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ['DATABASE_URL'] = '' # Force SQLite
        db.init_db()
        flask_app.app.config['TESTING'] = True
        cls.client = flask_app.app.test_client()

    def test_1_db_ai_chat_persistence(self):
        farmer_id = f"farmer-ai-{uuid.uuid4().hex[:8]}"
        email = f"testai-{uuid.uuid4().hex[:6]}@cropsync.com"
        db.create_user(email, "hash", "farmer", name="AI Farmer Test", user_id=farmer_id, status="active")

        # Save chat
        query = "What is the MSP rate for wheat?"
        response = "The current MSP rate for wheat is ₹2,275 per quintal."
        success, msg, cid = db.save_cropsync_ai_chat(farmer_id, query, response, category="msp", language="en")
        self.assertTrue(success)
        self.assertIsNotNone(cid)

        # Retrieve history
        history = db.get_cropsync_ai_chat_history(farmer_id)
        self.assertGreaterEqual(len(history), 1)
        self.assertEqual(history[0]['query'], query)
        self.assertEqual(history[0]['response'], response)

    def test_2_ai_service_advice_generation(self):
        # Test MSP advice
        advice_msp = ai_service.generate_agri_advice("What is the paddy MSP price?", category="msp", language="en")
        self.assertIn("MSP", advice_msp)
        self.assertIn("Paddy", advice_msp)

        # Test Tamil response
        advice_ta = ai_service.generate_agri_advice("பயிர் உரம் ஆலோசனை", category="fertilizer", language="ta")
        self.assertIsNotNone(advice_ta)
        self.assertGreater(len(advice_ta), 10)

    def test_3_ai_query_endpoint(self):
        farmer_id = f"farmer-ep-{uuid.uuid4().hex[:8]}"
        email = f"testep-{uuid.uuid4().hex[:6]}@cropsync.com"
        db.create_user(email, "hash", "farmer", name="Endpoint Farmer Test", user_id=farmer_id, status="active")

        with self.client.session_transaction() as sess:
            sess['farmer_user'] = {'id': farmer_id, 'name': 'Endpoint Farmer Test', 'email': email, 'role': 'farmer'}
            sess['farmer_lang'] = 'en'

        resp = self.client.post('/ai/query', json={'query': 'How to control caterpillars on crops?'})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get('success'))
        self.assertIn('response', data)
        self.assertIn('Caterpillar', data.get('response'))

if __name__ == '__main__':
    unittest.main()
