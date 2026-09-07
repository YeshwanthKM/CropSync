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
        fulfillment_method = order.get('fulfillment_method', 'Direct Collection')
        cod_amount = order.get('cod_amount') or order.get('total_price')
        pickup_address = order.get('pickup_address') or farmer.get('address') or farmer.get('location', '')

        base_url = get_app_base_url()
        view_url = f"{base_url}/login"

        if fulfillment_method == 'Logistics Partner':
            subject = f"Your CropSync Order #{order_id[:8]} — Logistics Delivery & Tracking Update"
        else:
            subject = f"Your CropSync Direct Order Has Been Accepted — #{order_id[:8]}"

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
                fulfillment_method=fulfillment_method,
                cod_amount=cod_amount,
                pickup_address=pickup_address,
                view_url=view_url
            )
        except Exception:
            if fulfillment_method == 'Logistics Partner':
                notice_html = f"""
                <div style="background: #eff6ff; border-left: 4px solid #3b82f6; padding: 15px; border-radius: 6px; margin: 15px 0; color: #1e3a8a;">
                    <p style="margin: 0 0 5px 0; font-weight: bold; color: #1d4ed8;">🚛 Logistics Partner Delivery:</p>
                    <p style="margin: 0; font-size: 14px;">Your order is assigned to CropSync Logistics! Our agent will collect the produce from the farmer, deliver it to your address, and collect Cash on Delivery (COD: ₹{cod_amount}) upon delivery. You will receive live status updates at each milestone.</p>
                </div>
                """
            else:
                notice_html = f"""
                <div style="background: #f0fdf4; border-left: 4px solid #22c55e; padding: 15px; border-radius: 6px; margin: 15px 0; color: #14532d;">
                    <p style="margin: 0 0 5px 0; font-weight: bold; color: #15803d;">🤝 Direct Collection & Farmer Connection:</p>
                    <p style="margin: 0; font-size: 14px;">Please contact the farmer directly using the details below to coordinate payment and pickup/delivery:<br>
                    • <strong>Farmer Name:</strong> {farmer_name}<br>
                    • <strong>Email:</strong> {farmer_email}<br>
                    • <strong>Phone:</strong> {farmer_phone}<br>
                    • <strong>Farm Address:</strong> {pickup_address}</p>
                </div>
                """

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
                    <p><strong>Fulfillment:</strong> {fulfillment_method}</p>
                </div>
                {notice_html}
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


def send_logistics_status_email(order, recipient_email, recipient_name, subject, title, body_text, notification_type='LOGISTICS_STATUS_UPDATE'):
    """Sends a logistics milestone notification safely without raising exceptions."""
    try:
        if not recipient_email:
            return False, "Recipient email missing"

        order_id = str(order.get('id', ''))
        crop_name = order.get('crop_name', 'Crop')
        quantity = order.get('quantity', 0)
        total_price = order.get('total_price', 0)
        fulfillment_method = order.get('fulfillment_method', 'Logistics Partner')

        base_url = get_app_base_url()
        view_url = f"{base_url}/login"

        try:
            html_content = render_template(
                'emails/logistics_status_update.html',
                order_id=order_id,
                crop_name=crop_name,
                quantity=quantity,
                total_price=total_price,
                recipient_name=recipient_name,
                title=title,
                body_text=body_text,
                fulfillment_method=fulfillment_method,
                logistics_status=order.get('logistics_status', ''),
                view_url=view_url
            )
        except Exception:
            html_content = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px;">
                <h2 style="color: #27ae60; text-align: center;">🚛 CropSync Logistics Update</h2>
                <p>Hello <strong>{recipient_name}</strong>,</p>
                <h3 style="color: #333;">{title}</h3>
                <p style="font-size: 15px; color: #555; line-height: 1.5;">{body_text}</p>
                <div style="background: #f9f9f9; padding: 15px; border-radius: 6px; margin: 15px 0;">
                    <p><strong>Order ID:</strong> #{order_id[:8]}</p>
                    <p><strong>Crop:</strong> {crop_name}</p>
                    <p><strong>Quantity:</strong> {quantity} kg</p>
                    <p><strong>Order Amount:</strong> ₹{total_price}</p>
                    <p><strong>Fulfillment Method:</strong> {fulfillment_method}</p>
                    <p><strong>Current Status:</strong> {order.get('logistics_status', 'Updated')}</p>
                </div>
                <p style="text-align: center; margin-top: 25px;">
                    <a href="{view_url}" style="background: #27ae60; color: #fff; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold;">View Order on CropSync</a>
                </p>
            </div>
            """

        sent, err = _send_raw_email(recipient_email, subject, html_content)
        status_str = 'SENT' if sent else 'FAILED'
        db.log_email_notification(
            order_id=order_id,
            recipient_user_id=None,
            notification_type=notification_type,
            recipient_email=recipient_email,
            status=status_str,
            error_message=err
        )
        return sent, err
    except Exception as e:
        print(f"[!] Exception in send_logistics_status_email ({subject}):", e)
        return False, str(e)


def dispatch_logistics_milestone_emails(order, next_status):
    """Triggers appropriate email notifications to Farmer, Buyer, and Logistics based on milestone status."""
    try:
        order_id = str(order.get('id', ''))
        crop_name = order.get('crop_name', 'Crop')

        farmer = db.get_user_by_id(order.get('farmer_id')) if order.get('farmer_id') else {}
        buyer = db.get_user_by_id(order.get('buyer_id')) if order.get('buyer_id') else {}
        
        farmer_email = order.get('farmer_email') or (farmer.get('email') if farmer else None)
        buyer_email = order.get('buyer_email') or (buyer.get('email') if buyer else None)
        farmer_name = order.get('farmer_name') or (farmer.get('name') if farmer else 'Farmer')
        buyer_name = order.get('buyer_name') or (buyer.get('name') if buyer else 'Buyer')

        if next_status == 'LOGISTICS_REQUESTED':
            # Email to prototype logistics user
            logistics_user = db.get_user_by_email("logistics@cropsync.com")
            if logistics_user and logistics_user.get('email'):
                send_logistics_status_email(
                    order=order,
                    recipient_email=logistics_user['email'],
                    recipient_name=logistics_user.get('name', 'CropSync Logistics'),
                    subject=f"New CropSync Logistics Order #{order_id[:8]} Assigned",
                    title="New Logistics Fulfillment Assignment",
                    body_text=f"A new logistics fulfillment request for {order.get('quantity', 0)} kg of {crop_name} has been assigned to your portal.",
                    notification_type='NEW_LOGISTICS_ORDER'
                )

        elif next_status == 'PICKUP_SCHEDULED':
            if farmer_email:
                send_logistics_status_email(
                    order=order,
                    recipient_email=farmer_email,
                    recipient_name=farmer_name,
                    subject=f"CropSync Order #{order_id[:8]} – Pickup Scheduled",
                    title="Logistics Pickup Scheduled",
                    body_text=f"Pickup for your {crop_name} order #{order_id[:8]} has been scheduled by CropSync Logistics.",
                    notification_type='PICKUP_SCHEDULED'
                )
            if buyer_email:
                send_logistics_status_email(
                    order=order,
                    recipient_email=buyer_email,
                    recipient_name=buyer_name,
                    subject=f"CropSync Order #{order_id[:8]} – Pickup Scheduled",
                    title="Logistics Fulfillment Started",
                    body_text=f"Your order for {crop_name} is scheduled for pickup from the farmer.",
                    notification_type='LOGISTICS_STARTED'
                )

        elif next_status == 'PICKED_UP':
            if farmer_email:
                send_logistics_status_email(
                    order=order,
                    recipient_email=farmer_email,
                    recipient_name=farmer_name,
                    subject=f"CropSync Order #{order_id[:8]} – Crop Picked Up",
                    title="Crop Picked Up from Farm",
                    body_text=f"CropSync Logistics has successfully picked up your {crop_name} shipment.",
                    notification_type='FARMER_PICKED_UP'
                )
            if buyer_email:
                send_logistics_status_email(
                    order=order,
                    recipient_email=buyer_email,
                    recipient_name=buyer_name,
                    subject=f"CropSync Order #{order_id[:8]} – Order Picked Up",
                    title="Produce Picked Up",
                    body_text=f"Your {crop_name} order has been collected from the farmer and is being prepared for dispatch.",
                    notification_type='BUYER_PICKED_UP'
                )

        elif next_status == 'IN_TRANSIT':
            if buyer_email:
                send_logistics_status_email(
                    order=order,
                    recipient_email=buyer_email,
                    recipient_name=buyer_name,
                    subject=f"CropSync Order #{order_id[:8]} – Order In Transit",
                    title="Shipment In Transit",
                    body_text=f"Your {crop_name} shipment is currently in transit to your delivery location.",
                    notification_type='IN_TRANSIT'
                )

        elif next_status == 'OUT_FOR_DELIVERY':
            if buyer_email:
                send_logistics_status_email(
                    order=order,
                    recipient_email=buyer_email,
                    recipient_name=buyer_name,
                    subject=f"CropSync Order #{order_id[:8]} – Out for Delivery",
                    title="Out for Delivery Today",
                    body_text=f"Your {crop_name} shipment is out for delivery today. Please have cash/payment ready upon arrival.",
                    notification_type='OUT_FOR_DELIVERY'
                )

        elif next_status == 'DELIVERED':
            if buyer_email:
                send_logistics_status_email(
                    order=order,
                    recipient_email=buyer_email,
                    recipient_name=buyer_name,
                    subject=f"CropSync Order #{order_id[:8]} – Order Delivered",
                    title="Order Delivered Successfully",
                    body_text=f"Your {crop_name} order #{order_id[:8]} has been delivered successfully.",
                    notification_type='BUYER_DELIVERED'
                )
            if farmer_email:
                send_logistics_status_email(
                    order=order,
                    recipient_email=farmer_email,
                    recipient_name=farmer_name,
                    subject=f"CropSync Order #{order_id[:8]} – Order Delivered",
                    title="Shipment Delivered to Buyer",
                    body_text=f"Your produce for order #{order_id[:8]} has been delivered to the buyer.",
                    notification_type='FARMER_DELIVERED'
                )

        elif next_status == 'PAYMENT_COLLECTED':
            if farmer_email:
                send_logistics_status_email(
                    order=order,
                    recipient_email=farmer_email,
                    recipient_name=farmer_name,
                    subject=f"CropSync Order #{order_id[:8]} – Payment Collected",
                    title="COD Payment Collected",
                    body_text=f"Cash on Delivery payment for order #{order_id[:8]} has been collected by CropSync Logistics.",
                    notification_type='PAYMENT_COLLECTED'
                )

        elif next_status == 'SETTLEMENT_PENDING':
            if farmer_email:
                send_logistics_status_email(
                    order=order,
                    recipient_email=farmer_email,
                    recipient_name=farmer_name,
                    subject=f"CropSync Order #{order_id[:8]} – Settlement Pending",
                    title="Farmer Settlement Pending",
                    body_text=f"Settlement of ₹{order.get('farmer_settlement_amount', order.get('total_price'))} for order #{order_id[:8]} is currently pending processing.",
                    notification_type='SETTLEMENT_PENDING'
                )

        elif next_status == 'SETTLED':
            if farmer_email:
                send_logistics_status_email(
                    order=order,
                    recipient_email=farmer_email,
                    recipient_name=farmer_name,
                    subject=f"CropSync Order #{order_id[:8]} – Farmer Settlement Completed",
                    title="Farmer Settlement Completed",
                    body_text=f"Settlement of ₹{order.get('farmer_settlement_amount', order.get('total_price'))} for order #{order_id[:8]} has been completed.",
                    notification_type='SETTLEMENT_COMPLETED'
                )

    except Exception as e:
        print("[!] Exception in dispatch_logistics_milestone_emails:", e)

