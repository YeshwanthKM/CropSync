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

    @staticmethod
    def delete_user_by_email(email):
        """
        Purges user record from Supabase Auth so the email is 100% freed up for new registrations.
        """
        service_key = (
            os.environ.get('SUPABASE_SERVICE_KEY') or 
            os.environ.get('SUPABASE_SERVICE_ROLE_KEY') or 
            SUPABASE_KEY
        )
        if not SUPABASE_URL or not service_key:
            return

        endpoint_search = f"{SUPABASE_URL.rstrip('/')}/auth/v1/admin/users"
        headers = {
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
            "Content-Type": "application/json"
        }

        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            req = urllib.request.Request(endpoint_search, headers=headers, method='GET')
            with urllib.request.urlopen(req, context=ctx) as resp:
                users_data = json.loads(resp.read().decode('utf-8'))
                users_list = users_data.get('users', []) if isinstance(users_data, dict) else (users_data if isinstance(users_data, list) else [])
                for u in users_list:
                    if u.get('email', '').lower() == email.lower():
                        uid = u.get('id')
                        del_endpoint = f"{SUPABASE_URL.rstrip('/')}/auth/v1/admin/users/{uid}"
                        del_req = urllib.request.Request(del_endpoint, headers=headers, method='DELETE')
                        with urllib.request.urlopen(del_req, context=ctx) as _:
                            print(f"[+] Successfully purged user {email} ({uid}) from Supabase Auth")
                        break
        except Exception as e:
            print("[!] Notice during Supabase Auth user delete:", e)


import os
import json
import ssl
import smtplib
import urllib.request
import urllib.error
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class EmailService:
    @staticmethod
    def send_verification_email(email, token):
        confirm_url = f"https://crop-sync.vercel.app/confirm-email?token={token}"
        gmail_user = (os.environ.get('GMAIL_USER') or os.environ.get('SMTP_USER') or '').strip()
        gmail_pass = (os.environ.get('GMAIL_APP_PASSWORD') or os.environ.get('SMTP_PASS') or '').strip().replace(' ', '')
        resend_api_key = (os.environ.get('RESEND_API_KEY') or '').strip()

        
        # Method 1: Direct Gmail / Custom SMTP Dispatch via Python smtplib (Sends to ANY email)
        if gmail_user and gmail_pass:
            try:
                smtp_host = os.environ.get('SMTP_HOST') or 'smtp.gmail.com'
                smtp_port = int(os.environ.get('SMTP_PORT') or 587)

                msg = MIMEMultipart('alternative')
                msg['Subject'] = "CropSync Email Verification"
                msg['From'] = f"CropSync Team <{gmail_user}>"
                msg['Reply-To'] = gmail_user
                msg['To'] = email


                text_content = f"Welcome to CropSync!\n\nPlease verify your email address by opening this link in your browser:\n{confirm_url}\n\nThank you,\nCropSync Team"
                html_content = f"""
                <div style="font-family: Arial, sans-serif; max-width: 500px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px;">
                    <h2 style="color: #27ae60; text-align: center;">🌾 Welcome to CropSync</h2>
                    <p style="font-size: 16px; color: #333; line-height: 1.5;">
                        Thank you for registering! Please click the button below to confirm your email address and activate your account:
                    </p>
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{confirm_url}" style="background-color: #27ae60; color: #ffffff; padding: 12px 24px; text-decoration: none; font-weight: bold; border-radius: 5px; font-size: 16px; display: inline-block;">
                            ✓ Confirm Email Address
                        </a>
                    </div>
                    <p style="font-size: 14px; color: #777; text-align: center;">
                        Or copy and paste this URL into your browser:<br>
                        <a href="{confirm_url}" style="color: #27ae60;">{confirm_url}</a>
                    </p>
                </div>
                """
                msg.attach(MIMEText(text_content, 'plain'))
                msg.attach(MIMEText(html_content, 'html'))


                with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
                    server.starttls()
                    server.login(gmail_user, gmail_pass)
                    server.sendmail(gmail_user, email, msg.as_string())

                print(f"[+] Verification email sent directly via Gmail SMTP to {email}")
                return True, None
            except Exception as e:
                print(f"[!] Gmail SMTP error sending to {email}:", e)
                return False, f"SMTP Error: {str(e)}"

        # Method 2: Resend API Dispatch
        elif resend_api_key:
            endpoint = "https://api.resend.com/emails"
            headers = {
                "Authorization": f"Bearer {resend_api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "from": "CropSync <onboarding@resend.dev>",
                "to": [email],
                "subject": "🌾 Verify your CropSync Email Address",
                "html": f"""
                <div style="font-family: Arial, sans-serif; max-width: 500px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px;">
                    <h2 style="color: #27ae60; text-align: center;">🌾 Welcome to CropSync</h2>
                    <p style="font-size: 16px; color: #333; line-height: 1.5;">
                        Thank you for registering! Please click the button below to confirm your email address and activate your account:
                    </p>
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{confirm_url}" style="background-color: #27ae60; color: #ffffff; padding: 12px 24px; text-decoration: none; font-weight: bold; border-radius: 5px; font-size: 16px; display: inline-block;">
                            ✓ Confirm Email Address
                        </a>
                    </div>
                    <p style="font-size: 14px; color: #777; text-align: center;">
                        Or copy and paste this URL into your browser:<br>
                        <a href="{confirm_url}" style="color: #27ae60;">{confirm_url}</a>
                    </p>
                </div>
                """
            }
            try:
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                req = urllib.request.Request(endpoint, data=json.dumps(payload).encode('utf-8'), headers=headers, method='POST')
                with urllib.request.urlopen(req, context=ctx) as resp:
                    print(f"[+] Direct email sent via Resend API to {email}")
                    return True, None
            except urllib.error.HTTPError as e:
                error_text = e.read().decode('utf-8')
                print(f"[!] Resend API HTTPError ({e.code}): {error_text}")
                try:
                    err_json = json.loads(error_text)
                    msg = err_json.get('message') or err_json.get('name') or f"Resend Error {e.code}"
                    return False, f"Resend API: {msg}"
                except Exception:
                    return False, f"Resend HTTP {e.code}"
            except Exception as e:
                print(f"[!] Resend API error sending email to {email}:", e)
                return False, str(e)
        else:
            print(f"[+] [DEV MODE EMAIL] Verification link for {email}: {confirm_url}")
            return False, "Email service credentials not configured"




