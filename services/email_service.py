import os
import json
import ssl
import smtplib
import urllib.request
import urllib.error
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import render_template
import db

def get_app_base_url():
    return (os.environ.get('APP_BASE_URL') or 'https://crop-sync.vercel.app').rstrip('/')

def _send_raw_email(to_email, subject, html_content, text_content=None):
    gmail_user = (os.environ.get('GMAIL_USER') or os.environ.get('SMTP_USER') or '').strip()
    gmail_pass = (os.environ.get('GMAIL_APP_PASSWORD') or os.environ.get('SMTP_PASS') or '').strip().replace(' ', '')
    resend_api_key = (os.environ.get('RESEND_API_KEY') or '').strip()

    if not text_content:
        text_content = "Please view this email in an HTML-compatible client."

    # 1. SMTP Dispatch (Gmail / Custom SMTP)
    if gmail_user and gmail_pass:
        try:
            smtp_host = os.environ.get('SMTP_HOST') or 'smtp.gmail.com'
            smtp_port = int(os.environ.get('SMTP_PORT') or 587)

            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"CropSync <{gmail_user}>"
            msg['Reply-To'] = gmail_user
            msg['To'] = to_email

            msg.attach(MIMEText(text_content, 'plain'))
            msg.attach(MIMEText(html_content, 'html'))

            with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
                server.starttls()
                server.login(gmail_user, gmail_pass)
                server.sendmail(gmail_user, to_email, msg.as_string())

            return True, None
        except Exception as e:
            print(f"[!] SMTP dispatch error to {to_email}:", e)
            return False, f"SMTP Error: {str(e)}"

    # 2. Resend API Dispatch
    elif resend_api_key:
        endpoint = "https://api.resend.com/emails"
        headers = {
            "Authorization": f"Bearer {resend_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "from": "CropSync <notifications@resend.dev>",
            "to": [to_email],
            "subject": subject,
            "html": html_content
        }
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(endpoint, data=json.dumps(payload).encode('utf-8'), headers=headers, method='POST')
            with urllib.request.urlopen(req, context=ctx) as resp:
                return True, None
        except urllib.error.HTTPError as e:
            error_text = e.read().decode('utf-8')
            print(f"[!] Resend API HTTPError ({e.code}): {error_text}")
            return False, f"Resend API Error {e.code}"
        except Exception as e:
            print(f"[!] Resend API error sending email to {to_email}:", e)
            return False, str(e)

    # 3. Dev Mode Console Log
    else:
        print(f"[+] [DEV MODE EMAIL DISPATCH] To: {to_email} | Subject: {subject}")
        return True, None


def send_new_order_email(order, farmer, buyer=None):
    """Notification sent to Farmer when a new order request is placed."""
    try:
        farmer_email = farmer.get('email')
        if not farmer_email:
            return False, "Farmer email missing"

        order_id = order.get('id')
        crop_name = order.get('crop_name')
        quantity = order.get('quantity')
        unit_price = order.get('unit_price') or round(float(order.get('total_price', 0)) / float(quantity or 1), 2)
        total_price = order.get('total_price')
        location = order.get('location') or farmer.get('location') or 'Marketplace'
        
        base_url = get_app_base_url()
        view_url = f"{base_url}/login"

        subject = f"New Order Request on CropSync — Order #{order_id[:8]}"

        try:
            html_content = render_template(
                'emails/new_order.html',
                order_id=order_id,
                crop_name=crop_name,
                quantity=quantity,
                price=unit_price,
                total=total_price,
                location=location,
                farmer_name=farmer.get('name', 'Farmer'),
                view_url=view_url
            )
        except Exception:
            html_content = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px;">
                <h2 style="color: #27ae60; text-align: center;">🌾 New Order Request — CropSync</h2>
                <p>Hello <strong>{farmer.get('name', 'Farmer')}</strong>,</p>
                <p>You have received a new order request for <strong>{crop_name}</strong>.</p>
                <div style="background: #f9f9f9; padding: 15px; border-radius: 6px; margin: 15px 0;">
                    <p><strong>Order ID:</strong> {order_id[:8]}</p>
                    <p><strong>Crop:</strong> {crop_name}</p>
                    <p><strong>Quantity:</strong> {quantity} kg</p>
                    <p><strong>Price:</strong> ₹{unit_price}/kg</p>
                    <p><strong>Total Amount:</strong> ₹{total_price}</p>
                </div>
                <p style="text-align: center;">
                    <a href="{view_url}" style="background: #27ae60; color: #fff; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold;">Log In to View Order</a>
                </p>
            </div>
            """

        sent, err = _send_raw_email(farmer_email, subject, html_content)
        status_str = 'SENT' if sent else 'FAILED'
        db.log_email_notification(
            order_id=order_id,
            recipient_user_id=farmer.get('id'),
            notification_type='NEW_ORDER',
            recipient_email=farmer_email,
            status=status_str,
            error_message=err
        )
        return sent, err
    except Exception as e:
        print("[!] Exception in send_new_order_email:", e)
        return False, str(e)


def send_order_accepted_email(order, buyer, farmer):
    """Notification sent to Buyer when Farmer accepts their order."""
    try:
        buyer_email = buyer.get('email')
        if not buyer_email:
            return False, "Buyer email missing"

        order_id = order.get('id')
        crop_name = order.get('crop_name')
        quantity = order.get('quantity')
        unit_price = order.get('unit_price') or round(float(order.get('total_price', 0)) / float(quantity or 1), 2)
        total_price = order.get('total_price')
        location = order.get('location') or farmer.get('location') or 'Marketplace'

        base_url = get_app_base_url()
        view_url = f"{base_url}/login"

        subject = f"Your CropSync Order Has Been Accepted — #{order_id[:8]}"

        farmer_name = farmer.get('name', 'Farmer')
        farmer_email = farmer.get('email', 'N/A')
        farmer_phone = farmer.get('phone') or 'Provided upon request'

        try:
            html_content = render_template(
                'emails/order_accepted.html',
                order_id=order_id,
                crop_name=crop_name,
                quantity=quantity,
                price=unit_price,
                total=total_price,
                location=location,
                buyer_name=buyer.get('name', 'Buyer'),
                farmer_name=farmer_name,
                farmer_email=farmer_email,
                farmer_phone=farmer_phone,
                view_url=view_url
            )
        except Exception:
            html_content = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px;">
                <h2 style="color: #27ae60; text-align: center;">✓ Order Accepted — CropSync</h2>
                <p>Hello <strong>{buyer.get('name', 'Buyer')}</strong>,</p>
                <p>Good news! Your order request for <strong>{crop_name}</strong> has been accepted by the farmer.</p>
                <div style="background: #f9f9f9; padding: 15px; border-radius: 6px; margin: 15px 0;">
                    <p><strong>Order ID:</strong> {order_id[:8]}</p>
                    <p><strong>Crop:</strong> {crop_name}</p>
                    <p><strong>Quantity:</strong> {quantity} kg</p>
                    <p><strong>Total Amount:</strong> ₹{total_price}</p>
                    <hr style="border: 0; border-top: 1px solid #ddd; margin: 10px 0;">
                    <p><strong>Farmer Details:</strong></p>
                    <p>Name: {farmer_name}<br>Email: {farmer_email}</p>
                </div>
                <p style="color: #e67e22; font-weight: bold;">Notice: Please contact the farmer directly to coordinate payment and collection/delivery. CropSync connects farmers and buyers directly but does not process payments or provide physical delivery services.</p>
                <p style="text-align: center;">
                    <a href="{view_url}" style="background: #27ae60; color: #fff; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold;">Log In to View Order Details</a>
                </p>
            </div>
            """

        sent, err = _send_raw_email(buyer_email, subject, html_content)
        status_str = 'SENT' if sent else 'FAILED'
        db.log_email_notification(
            order_id=order_id,
            recipient_user_id=buyer.get('id'),
            notification_type='ORDER_ACCEPTED',
            recipient_email=buyer_email,
            status=status_str,
            error_message=err
        )
        return sent, err
    except Exception as e:
        print("[!] Exception in send_order_accepted_email:", e)
        return False, str(e)


def send_order_rejected_email(order, buyer):
    """Notification sent to Buyer when Farmer rejects their order."""
    try:
        buyer_email = buyer.get('email')
        if not buyer_email:
            return False, "Buyer email missing"

        order_id = order.get('id')
        crop_name = order.get('crop_name')

        base_url = get_app_base_url()
        browse_url = f"{base_url}/login"

        subject = f"Your CropSync Order Update — #{order_id[:8]}"

        try:
            html_content = render_template(
                'emails/order_rejected.html',
                order_id=order_id,
                crop_name=crop_name,
                buyer_name=buyer.get('name', 'Buyer'),
                browse_url=browse_url
            )
        except Exception:
            html_content = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px;">
                <h2 style="color: #e74c3c; text-align: center;">Order Update — CropSync</h2>
                <p>Hello <strong>{buyer.get('name', 'Buyer')}</strong>,</p>
                <p>Unfortunately, your order request for <strong>{crop_name}</strong> (Order #{order_id[:8]}) could not be accepted by the farmer at this time.</p>
                <p>You can continue browsing CropSync for other available listings.</p>
                <p style="text-align: center; margin-top: 25px;">
                    <a href="{browse_url}" style="background: #27ae60; color: #fff; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold;">Log In to Browse Marketplace</a>
                </p>
            </div>
            """

        sent, err = _send_raw_email(buyer_email, subject, html_content)
        status_str = 'SENT' if sent else 'FAILED'
        db.log_email_notification(
            order_id=order_id,
            recipient_user_id=buyer.get('id'),
            notification_type='ORDER_REJECTED',
            recipient_email=buyer_email,
            status=status_str,
            error_message=err
        )
        return sent, err
    except Exception as e:
        print("[!] Exception in send_order_rejected_email:", e)
        return False, str(e)


def send_order_completed_email(order, recipient_user, role):
    """Notification sent when an order is marked Completed."""
    try:
        recipient_email = recipient_user.get('email')
        if not recipient_email:
            return False, "Recipient email missing"

        order_id = order.get('id')
        crop_name = order.get('crop_name')
        quantity = order.get('quantity')
        total_price = order.get('total_price')

        base_url = get_app_base_url()
        dashboard_url = f"{base_url}/login"


        subject = f"CropSync Order Completed — #{order_id[:8]}"

        try:
            html_content = render_template(
                'emails/order_completed.html',
                order_id=order_id,
                crop_name=crop_name,
                quantity=quantity,
                total=total_price,
                recipient_name=recipient_user.get('name', 'User'),
                dashboard_url=dashboard_url
            )
        except Exception:
            html_content = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px;">
                <h2 style="color: #27ae60; text-align: center;">✓ Order Completed — CropSync</h2>
                <p>Hello <strong>{recipient_user.get('name', 'User')}</strong>,</p>
                <p>This CropSync order has been officially marked as <strong>Completed</strong>.</p>
                <div style="background: #f9f9f9; padding: 15px; border-radius: 6px; margin: 15px 0;">
                    <p><strong>Order ID:</strong> {order_id[:8]}</p>
                    <p><strong>Crop:</strong> {crop_name}</p>
                    <p><strong>Quantity:</strong> {quantity} kg</p>
                    <p><strong>Total Amount:</strong> ₹{total_price}</p>
                </div>
                <p style="font-size: 13px; color: #777;">Thank you for using CropSync to connect directly with agricultural trade partners.</p>
            </div>
            """

        sent, err = _send_raw_email(recipient_email, subject, html_content)
        status_str = 'SENT' if sent else 'FAILED'
        db.log_email_notification(
            order_id=order_id,
            recipient_user_id=recipient_user.get('id'),
            notification_type='ORDER_COMPLETED',
            recipient_email=recipient_email,
            status=status_str,
            error_message=err
        )
        return sent, err
    except Exception as e:
        print("[!] Exception in send_order_completed_email:", e)
        return False, str(e)
