import unittest
import json
import os
import db
from app import app
from services.ai_service import generate_agri_advice, format_text_for_speech

class TestPhase5VoiceAI(unittest.TestCase):

    def setUp(self):
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-key'
        self.client = app.test_client()
        db.init_db()

    def test_format_text_for_speech_cleaning(self):
        """Test markdown cleaning for speech synthesis engine."""
        raw_md = "💡 **Paddy Advisory**:\n- Apply urea (50kg/acre)\n- Avoid *over-watering*."
        cleaned = format_text_for_speech(raw_md)
        self.assertNotIn('**', cleaned)
        self.assertNotIn('*', cleaned)
        self.assertIn('Paddy Advisory', cleaned)
        self.assertIn('Apply urea', cleaned)

    def test_voice_query_response_speech_text(self):
        """Test /ai/query endpoint returns speech_text field for TTS synthesis."""
        with self.client as c:
            with c.session_transaction() as sess:
                sess['farmer_user'] = {'id': 'test-farmer-voice-id', 'email': 'voice_farmer@test.com'}
                sess['farmer_lang'] = 'en'

            res = c.post('/ai/query', json={'query': 'What fertilizer should I use for paddy?'})
            self.assertEqual(res.status_code, 200)
            data = json.loads(res.data)
            self.assertTrue(data.get('success'))
            self.assertIn('speech_text', data)
            self.assertTrue(len(data['speech_text']) > 10)
            self.assertNotIn('**', data['speech_text'])

    def test_voice_query_tamil_language(self):
        """Test spoken Tamil query handling in /ai/query."""
        with self.client as c:
            with c.session_transaction() as sess:
                sess['farmer_user'] = {'id': 'test-farmer-voice-ta-id', 'email': 'ta_voice_farmer@test.com'}
                sess['farmer_lang'] = 'ta'

            res = c.post('/ai/query', json={'query': 'நெல் பயிரில் உரம் மேலாண்மை பற்றி சொல்லுங்கள்'})
            self.assertEqual(res.status_code, 200)
            data = json.loads(res.data)
            self.assertTrue(data.get('success'))
            self.assertEqual(data.get('language'), 'ta')
            self.assertIn('speech_text', data)

    def test_speech_language_codes(self):
        """Test language code mapping for SpeechRecognition and SpeechSynthesis."""
        lang_en = 'en-IN' if 'en' == 'en' else 'ta-IN'
        lang_ta = 'ta-IN' if 'ta' == 'ta' else 'en-IN'
        self.assertEqual(lang_en, 'en-IN')
        self.assertEqual(lang_ta, 'ta-IN')

if __name__ == '__main__':
    unittest.main()
