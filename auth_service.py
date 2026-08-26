import os
import json
import ssl
import urllib.request
import urllib.error


SUPABASE_URL = (
    os.environ.get('SUPABASE_URL') or 
    os.environ.get('NEXT_PUBLIC_SUPABASE_URL') or 
    'https://veyfdcxiubcufygjjoqw.supabase.co'
)

SUPABASE_KEY = (
    os.environ.get('SUPABASE_KEY') or 
    os.environ.get('SUPABASE_ANON_KEY') or 
    os.environ.get('NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY') or 
    'sb_publishable_pARznbgYEgmUq-dsR_Okvg_VjQXDvP6'
)

class SupabaseAuthService:
    @staticmethod
    def signup(email, password, user_data=None):
        """
        Registers user with Supabase Auth API over REST HTTP.
        Supabase Auth automatically dispatches the verification email to the user's inbox.
        """
        if not SUPABASE_URL or not SUPABASE_KEY:
            print("[!] Supabase URL/Key missing for Supabase Auth")
            return None, "Supabase Auth configuration missing"

        endpoint = f"{SUPABASE_URL.rstrip('/')}/auth/v1/signup"
        headers = {
            "apikey": SUPABASE_KEY,
            "Content-Type": "application/json"
        }
        payload = {
            "email": email,
            "password": password,
            "data": user_data or {}
        }

        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            req = urllib.request.Request(
                endpoint,
                data=json.dumps(payload).encode('utf-8'),
                headers=headers,
                method='POST'
            )
            with urllib.request.urlopen(req, context=ctx) as resp:
                res_body = json.loads(resp.read().decode('utf-8'))
                return res_body, None

        except urllib.error.HTTPError as e:
            error_text = e.read().decode('utf-8')
            print(f"[!] Supabase Auth HTTPError ({e.code}): {error_text}")
            try:
                err_json = json.loads(error_text)
                msg = err_json.get('msg') or err_json.get('error_description') or err_json.get('message') or f"Auth Error {e.code}"
                return None, msg
            except Exception:
                return None, f"Supabase Auth Error {e.code}"
        except Exception as e:
            print("[!] Supabase Auth unexpected error:", e)
            return None, str(e)
