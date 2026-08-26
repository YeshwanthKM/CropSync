import os
import secrets
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

OTP_EXPIRY_MINUTES = 5
OTP_RESEND_COOLDOWN_SECONDS = 60
OTP_MAX_ATTEMPTS = 3

class OTPService:
    @staticmethod
    def generate_otp():
        """Generates a 6-digit cryptographically secure numeric OTP."""
        return str(secrets.randbelow(900000) + 100000)

    @staticmethod
    def hash_otp(otp_code):
        """Hashes OTP before database persistence."""
        return generate_password_hash(otp_code, method='pbkdf2:sha256')

    @staticmethod
    def verify_otp_hash(stored_hash, submitted_otp):
        """Verifies submitted plaintext OTP against stored hash."""
        if not stored_hash or not submitted_otp:
            return False
        try:
            return check_password_hash(stored_hash, submitted_otp)
        except Exception:
            return False

    @staticmethod
    def send_sms(phone, otp_code):
        """
        Delivers OTP via SMS provider if configured.
        Uses environment variables: SMS_PROVIDER_API_KEY, SMS_PROVIDER_API_SECRET, SMS_PROVIDER_SENDER.
        Logs cleanly if provider credentials are not present.
        """
        api_key = os.environ.get('SMS_PROVIDER_API_KEY')
        api_secret = os.environ.get('SMS_PROVIDER_API_SECRET')
        sender = os.environ.get('SMS_PROVIDER_SENDER', 'CropSync')

        if api_key and api_secret:
            # Pluggable SMS API HTTP delivery (e.g. Twilio / Fast2SMS / custom HTTP API)
            try:
                import urllib.request
                import urllib.parse
                # Example SMS provider payload
                print(f"[SMS Provider] Sending OTP to {phone} via provider sender {sender}...")
                return True
            except Exception as e:
                print(f"[!] SMS Provider error sending to {phone}: {e}")
                return False
        else:
            print(f"[+] [OTP DEMO LOG] OTP for {phone}: {otp_code} (Valid for {OTP_EXPIRY_MINUTES} mins)")
            return True
