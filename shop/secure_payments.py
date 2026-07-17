"""
Secure payments via Razorpay (UPI / cards / netbanking).

Orders become Paid only after Razorpay payment signature verification
(or a verified webhook) — never because someone opened a pay link.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings


def razorpay_configured():
    key_id = (getattr(settings, 'RAZORPAY_KEY_ID', None) or '').strip()
    key_secret = (getattr(settings, 'RAZORPAY_KEY_SECRET', None) or '').strip()
    return bool(key_id and key_secret)


def get_razorpay_key_id():
    return (getattr(settings, 'RAZORPAY_KEY_ID', None) or '').strip()


def get_razorpay_key_secret():
    return (getattr(settings, 'RAZORPAY_KEY_SECRET', None) or '').strip()


def get_razorpay_webhook_secret():
    return (getattr(settings, 'RAZORPAY_WEBHOOK_SECRET', None) or '').strip()


def amount_to_paise(amount) -> int:
    """Convert rupees to integer paise for Razorpay."""
    d = Decimal(str(amount)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return int(d * 100)


def get_razorpay_client():
    if not razorpay_configured():
        raise RuntimeError('Razorpay keys are not configured')
    import razorpay

    return razorpay.Client(auth=(get_razorpay_key_id(), get_razorpay_key_secret()))


def create_razorpay_order(order):
    """
    Create (or reuse) a Razorpay order for this shop Order.
    Returns dict: order_id, amount_paise, currency, key_id
    """
    client = get_razorpay_client()
    amount_paise = amount_to_paise(order.get_total_cost())
    if amount_paise < 100:
        raise ValueError('Order amount must be at least ₹1.00')

    # Reuse unpaid Razorpay order if amount still matches
    existing = (order.razorpay_order_id or '').strip()
    if existing:
        try:
            remote = client.order.fetch(existing)
            if (
                str(remote.get('status')) in ('created', 'attempted')
                and int(remote.get('amount') or 0) == amount_paise
            ):
                return {
                    'order_id': existing,
                    'amount_paise': amount_paise,
                    'currency': 'INR',
                    'key_id': get_razorpay_key_id(),
                }
        except Exception:
            pass

    receipt = f'FLORA{order.id}'[:40]
    data = {
        'amount': amount_paise,
        'currency': 'INR',
        'receipt': receipt,
        'notes': {
            'flora_order_id': str(order.id),
            'order_code': f'FLORA{order.id}',
            'payment_note': f'FLORA{order.id}',
            'customer': f'{order.first_name} {order.last_name}'.strip(),
            'phone': (order.phone or '')[:20],
        },
        'payment_capture': 1,
    }
    remote = client.order.create(data=data)
    rz_id = remote['id']
    order.razorpay_order_id = rz_id
    order.save(update_fields=['razorpay_order_id'])
    return {
        'order_id': rz_id,
        'amount_paise': amount_paise,
        'currency': 'INR',
        'key_id': get_razorpay_key_id(),
    }


def verify_payment_signature(razorpay_order_id, razorpay_payment_id, razorpay_signature) -> bool:
    """HMAC-SHA256 signature check (official Razorpay checkout response)."""
    secret = get_razorpay_key_secret()
    if not secret or not razorpay_order_id or not razorpay_payment_id or not razorpay_signature:
        return False
    body = f'{razorpay_order_id}|{razorpay_payment_id}'.encode('utf-8')
    expected = hmac.new(secret.encode('utf-8'), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, razorpay_signature)


def verify_webhook_signature(body: bytes, signature: str) -> bool:
    """Verify X-Razorpay-Signature for webhooks."""
    secret = get_razorpay_webhook_secret() or get_razorpay_key_secret()
    if not secret or not signature:
        return False
    expected = hmac.new(secret.encode('utf-8'), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


