import unittest
import uuid
from app import app, db
from otp_service import OTPService

class TestCropSyncPhase2(unittest.TestCase):

    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['SECRET_KEY'] = 'test-secret-key'
        self.client = app.test_client()
        db.init_db()

    # 1. Test Demo Accounts Compatibility
    def test_demo_account_logins(self):
        # Admin Demo
        resp = self.client.post('/login', data={'email': 'admin@cropsync.com', 'password': 'admin123'}, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Admin', resp.data)

        # Farmer Demo
        resp = self.client.post('/login', data={'email': 'farmer1@gmail.com', 'password': 'farmer123'}, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Farmer', resp.data)

        # Buyer Demo
        resp = self.client.post('/login', data={'email': 'buyer1@gmail.com', 'password': 'buyer123'}, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Buyer', resp.data)

    # 2. Test Registration Role Protection (Reject admin registration)
    def test_registration_role_protection(self):
        resp = self.client.post('/register', data={
            'role': 'admin',
            'name': 'Hacker Admin',
            'email': 'hacker@admin.com',
            'phone': '9999999999',
            'password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Invalid registration role', resp.data)

    # 3. Test Password Mismatch Validation
    def test_registration_password_mismatch(self):
        resp = self.client.post('/register', data={
            'role': 'farmer',
            'name': 'Test Farmer',
            'email': 'newfarmer1@example.com',
            'phone': '9876543219',
            'location': 'Tirupur',
            'password': 'password123',
            'confirm_password': 'mismatchpassword'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Passwords do not match', resp.data)

    # 4. Test Complete Registration + Email Verification + Phone Verification Flow
    def test_full_registration_and_verification_flow(self):
        test_email = f"farmer_{uuid.uuid4().hex[:6]}@test.com"
        
        # Step A: Register
        resp = self.client.post('/register', data={
            'role': 'farmer',
            'name': 'New Verified Farmer',
            'email': test_email,
            'phone': '9123456789',
            'location': 'Thanjavur',
            'password': 'farmerpassword123',
            'confirm_password': 'farmerpassword123'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Check Your Email', resp.data)

        # Verify initial pending state in DB
        u = db.get_user_by_email(test_email)
        self.assertIsNotNone(u)
        self.assertEqual(u['account_status'], 'pending')
        self.assertFalse(u.get('email_verified'))

        # Step B: Attempt login before verification -> Should be blocked & redirected to verification status
        resp_login_pending = self.client.post('/login', data={
            'email': test_email,
            'password': 'farmerpassword123'
        }, follow_redirects=True)
        self.assertEqual(resp_login_pending.status_code, 200)
        self.assertIn(b'Account Verification Status', resp_login_pending.data)

        # Step C: Complete Email Verification
        with self.client.session_transaction() as sess:
            sess['pending_user_id'] = u['id']
            sess['pending_email'] = test_email

        resp_email_v = self.client.get('/confirm-email', follow_redirects=True)

        self.assertEqual(resp_email_v.status_code, 200)
        self.assertIn(b'Farmer Dashboard', resp_email_v.data)

        # Verify active account status in DB
        u_final = db.get_user_by_email(test_email)
        self.assertEqual(u_final['account_status'], 'active')
        self.assertTrue(u_final.get('email_verified'))


    # 5. Test Admin Portal Status Filters & Audit Logging
    def test_admin_verification_filters_and_audit(self):
        # Login as Admin
        self.client.post('/login', data={'email': 'admin@cropsync.com', 'password': 'admin123'})
        
        # Test Filter Options
        resp_all = self.client.get('/admin/farmers?status=all')
        self.assertEqual(resp_all.status_code, 200)
        self.assertIn(b'Farmer Management', resp_all.data)

        resp_verified = self.client.get('/admin/farmers?status=verified')
        self.assertEqual(resp_verified.status_code, 200)

        resp_pending = self.client.get('/admin/farmers?status=pending')
        self.assertEqual(resp_pending.status_code, 200)

        # Test Audit Logging
        db.log_admin_action('admin1', 'TEST_ACTION', 'f1', 'Testing audit logs')
        logs = db.get_audit_logs(limit=5)
        self.assertGreater(len(logs), 0)

if __name__ == '__main__':
    unittest.main()
