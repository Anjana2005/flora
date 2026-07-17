"""UPI / WhatsApp helpers for Flora orders."""
import json
from urllib.parse import quote

from django.conf import settings


def get_upi_id():
    return (getattr(settings, 'UPI_ID', None) or 'flora1101@axl').strip()


def is_valid_upi_id(value):
    """
    Basic UPI ID check: something@handle (e.g. name@oksbi, 98xxxx@ybl).
    Stops empty / spam submissions without a real-looking VPA.
    """
    import re
    v = (value or '').strip().lower()
    if not v or len(v) < 5 or len(v) > 100:
        return False
    # local@handle — handle is letters/digits (oksbi, ybl, paytm, fam, etc.)
    return bool(re.match(r'^[a-z0-9._-]{2,64}@[a-z0-9]{2,20}$', v))


def get_upi_name():
    # Empty by default — wrong payee name breaks UPI deep links for personal VPAs
    return (getattr(settings, 'UPI_MERCHANT_NAME', None) or '').strip()


def get_whatsapp_number():
    """WhatsApp number that receives new order / paid confirmations."""
    numbers = get_whatsapp_numbers()
    return numbers[0] if numbers else '919605531101'


def get_whatsapp_numbers():
    """Order-notification WhatsApp number(s) — digits with country code."""
    configured = getattr(settings, 'WHATSAPP_SHOP_NUMBERS', None) or []
    numbers = []
    for n in configured:
        digits = ''.join(ch for ch in str(n) if ch.isdigit())
        if digits and digits not in numbers:
            numbers.append(digits)
    primary = getattr(settings, 'WHATSAPP_ORDER_NUMBER', None) or '919605531101'
    primary = ''.join(ch for ch in str(primary) if ch.isdigit())
    if primary and primary not in numbers:
        numbers.insert(0, primary)
    if not numbers:
        numbers = ['919605531101']
    return numbers


def _amount_str(amount):
    return f"{float(amount):.2f}"


# How often the on-screen QR refreshes (new tr code). Longer = less flicker.
QR_ROTATE_SECONDS = 600  # 10 minutes


def current_qr_slot(now=None):
    """Time bucket for rotating scanners."""
    import time
    t = int(now if now is not None else time.time())
    return t // QR_ROTATE_SECONDS, t


def seconds_until_qr_refresh(now=None):
    import time
    t = int(now if now is not None else time.time())
    return QR_ROTATE_SECONDS - (t % QR_ROTATE_SECONDS)


def build_payment_ref(order_id, extra=''):
    """Unique transaction reference for one order payment QR."""
    base = f"FLORA{order_id}"
    extra = ''.join(ch for ch in str(extra) if ch.isalnum())[:12]
    if extra:
        return f"{base}{extra}"[:35]
    return base[:35]


def sanitize_upi_note(value, max_len=40):
    """UPI tn/tr: letters, digits, space, hyphen — apps often show this as Remarks."""
    raw = str(value or '').strip()
    cleaned = []
    for ch in raw:
        if ch.isalnum() or ch in (' ', '-', '_'):
            cleaned.append(ch)
    text = ''.join(cleaned).strip() or 'FloraOrder'
    # Collapse spaces
    text = ' '.join(text.split())
    return text[:max_len]


def build_order_note_code(order_id):
    """Default note code embedded in every scanner (shows in UPI payment remarks)."""
    return f'FLORA{order_id}'


def upi_app_response(upi_link, note_code='', amount_str='', shop_upi='', already_paid=True):
    """
    Open UPI app with amount + note pre-filled (HTML bridge; no 302 to upi://).
    Same link as the QR: tn= note comes automatically in GPay/PhonePe.
    """
    from django.http import HttpResponse
    from django.utils.html import escape

    intent = build_android_upi_intent(upi_link)
    safe_upi = escape(upi_link or '')
    safe_intent = escape(intent or upi_link or '')
    js_upi = json.dumps(upi_link or '')
    js_intent = json.dumps(intent or upi_link or '')
    safe_note = escape(note_code or '')
    safe_amt = escape(str(amount_str or ''))
    safe_shop = escape(shop_upi or get_upi_id())
    paid_line = (
        'Already paid in admin'
        if already_paid
        else 'Note + amount open automatically in UPI'
    )
    html = f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Open UPI · {safe_note}</title>
<style>
  body{{font-family:system-ui,sans-serif;background:#fff7f9;color:#5A3F4A;margin:0;padding:2rem 1rem;text-align:center}}
  .card{{max-width:400px;margin:0 auto;background:#fff;border-radius:20px;padding:1.5rem;box-shadow:0 12px 28px rgba(232,122,150,.15)}}
  .ok{{display:inline-block;background:#e3f2fd;color:#0d47a1;font-weight:800;padding:.4rem .8rem;border-radius:999px;margin:.5rem 0}}
  .amt{{font-size:1.75rem;font-weight:800;color:#E87A96}}
  a.btn{{display:block;margin:.7rem 0 0;padding:.9rem 1rem;border-radius:12px;background:#E87A96;color:#fff;font-weight:800;text-decoration:none}}
  p{{font-size:.92rem;line-height:1.45;color:#666}}
  code{{font-weight:800;color:#5A3F4A}}
</style>
</head><body>
<div class="card">
  <h1 style="font-size:1.25rem;margin:0 0 .35rem">Opening UPI…</h1>
  <div class="ok">{paid_line}</div>
  <div class="amt">₹{safe_amt}</div>
  <p>Pay to <code>{safe_shop}</code><br>
  Note will show as: <code>{safe_note}</code></p>
  <a class="btn" id="upi-btn" href="{safe_upi}">Open UPI (note auto-filled)</a>
  <a class="btn" href="{safe_intent}" style="background:#5A3F4A">Open on Android</a>
  <p style="margin-top:1rem;font-size:.85rem">In the app, check Remarks / Message shows <strong>{safe_note}</strong>, then pay.</p>
</div>
<script>
(function(){{
  var u = {js_upi};
  var intent = {js_intent};
  var ua = navigator.userAgent || '';
  var isAndroid = /Android/i.test(ua);
  var target = (isAndroid && intent) ? intent : u;
  if (target) {{
    try {{ window.location.href = target; }} catch (e) {{}}
    setTimeout(function(){{
      try {{ window.location.href = u; }} catch (e) {{}}
    }}, 600);
  }}
}})();
</script>
</body></html>"""
    return HttpResponse(html)


def build_upi_link(amount, order_ref, note=None, tr=None):
    """
    Pure UPI intent so GPay/PhonePe auto-fill:
      - Payee (pa)
      - Amount (am)
      - Note / remarks (tn)  ← order code e.g. FLORA30

    QR and "Open UPI" both use this exact string — never a website URL.
    """
    pa = (get_upi_id() or '').strip().lower()
    am = _amount_str(amount)
    # Order note that must appear in the app Remarks / Message field
    tn = sanitize_upi_note(note or order_ref, max_len=30).replace(' ', '')
    if not tn:
        tn = 'FloraOrder'

    # Standard NPCI order: pa, am, cu, tn — note is tn
    # Do not use website URLs, tr, or wrong pn (breaks personal UPI).
    return f'upi://pay?pa={pa}&am={am}&cu=INR&tn={tn}'


def build_android_upi_intent(upi_link):
    """Android intent so Open UPI reliably hands off to GPay/PhonePe with same note."""
    if not upi_link or not upi_link.startswith('upi://pay?'):
        return upi_link or ''
    query = upi_link.split('?', 1)[1]
    return (
        f'intent://pay?{query}'
        '#Intent;scheme=upi;action=android.intent.action.VIEW;'
        'category=android.intent.category.BROWSABLE;end'
    )


def build_upi_qr_url(upi_link, size=280):
    """QR image whose payload is the pure upi:// string (note inside)."""
    try:
        return build_upi_qr_data_uri(upi_link, size=size)
    except Exception:
        return (
            'https://api.qrserver.com/v1/create-qr-code/'
            f'?size={size}x{size}&margin=10&data={quote(upi_link, safe="")}'
        )


def build_upi_qr_data_uri(upi_link, size=280):
    """Generate a PNG QR as data URI from pure upi:// payload."""
    import base64
    import io

    import qrcode
    from qrcode.constants import ERROR_CORRECT_M

    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    # Exact UPI string — scan opens app with amount + note pre-filled
    qr.add_data(upi_link)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')
    try:
        img = img.resize((size, size))
    except Exception:
        pass
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    b64 = base64.b64encode(buf.getvalue()).decode('ascii')
    return f'data:image/png;base64,{b64}'


def build_order_payment_qr(order, size=280, scan_page_url=None, slot=None):
    """
    Always build a pure UPI QR (not a website link).

    Scanning in GPay/PhonePe auto-fills amount + note (tn=FLORA#).
    Opening UPI uses the same upi_link so note comes automatically.
    scan_page_url is ignored for the QR image (kept only for API compat).
    """
    order_ref = build_order_note_code(order.id)
    payment_note = order_ref
    amount = order.get_total_cost()
    if slot is None:
        slot, _ = current_qr_slot()
    tr = build_payment_ref(order.id, f'S{slot}')

    # Pure UPI only — note auto-fills in payment app
    upi_link = build_upi_link(amount, order_ref, note=payment_note)
    qr_payload = upi_link

    return {
        'order_ref': order_ref,
        'payment_note': payment_note,
        'amount_str': _amount_str(amount),
        'tr': tr,
        'slot': slot,
        'seconds_left': seconds_until_qr_refresh(),
        'rotate_seconds': QR_ROTATE_SECONDS,
        'upi_link': upi_link,
        'android_intent': build_android_upi_intent(upi_link),
        'qr_url': build_upi_qr_url(qr_payload, size=size),
        'scan_page_url': '',
        'shop_upi_id': get_upi_id(),
    }


def build_android_intent_link(amount, order_ref):
    base = build_upi_link(amount, order_ref)
    query = base.split('?', 1)[1]
    return (
        f'intent://pay?{query}'
        '#Intent;scheme=upi;action=android.intent.action.VIEW;end'
    )


def build_gpay_link(amount, order_ref):
    base = build_upi_link(amount, order_ref)
    query = base.split('?', 1)[1]
    return f'gpay://upi/pay?{query}'


def build_phonepe_link(amount, order_ref):
    base = build_upi_link(amount, order_ref)
    query = base.split('?', 1)[1]
    return f'phonepe://pay?{query}'


def build_paytm_link(amount, order_ref):
    base = build_upi_link(amount, order_ref)
    query = base.split('?', 1)[1]
    return f'paytmmp://pay?{query}'


def build_order_message(order, request=None, paid=None):
    """
    Plain-text WhatsApp message with product + order details.
    """
    if paid is None:
        paid = bool(order.paid)

    order_id = f'FLORA{order.id}'
    total = float(order.get_total_cost())
    full_address = ', '.join(
        part
        for part in [order.address, order.city, order.postal_code, order.country]
        if part
    )
    customer = f'{order.first_name} {order.last_name}'.strip()

    lines = [
        '*New Order - Flora Shop Thrissur*',
        '',
        f'*Order ID:* {order_id}',
        f'*Payment status:* {"PAID" if paid else "NOT PAID yet"}',
        '',
        '*Customer details:*',
        f'Name: {customer}',
        f'Phone: {order.phone or "-"}',
        f'Email: {order.email or "-"}',
        f'Address: {full_address or "-"}',
        '',
        '*Products ordered:*',
    ]

    item_no = 0
    for item in order.items.select_related('product', 'product__category').all():
        item_no += 1
        product = item.product
        product_name = product.name if product else 'Deleted product'
        category_name = (
            product.category.name if product and product.category else 'N/A'
        )
        size = (item.size or '').strip() or 'Not selected'
        qty = int(item.quantity or 0)
        unit = float(item.price or 0)
        subtotal = unit * qty
        lines.extend(
            [
                f'{item_no}) *{product_name}*',
                f'   Category: {category_name}',
                f'   Size: {size}',
                f'   Qty: {qty}',
                f'   Unit price: Rs {unit:.2f}',
                f'   Line total: Rs {subtotal:.2f}',
                '',
            ]
        )

    if item_no == 0:
        lines.append('(No items)')
        lines.append('')

    lines.extend(
        [
            f'*Total amount: Rs {total:.2f}*',
            '',
            '*UPI payment:*',
            f'UPI ID: {get_upi_id()}',
            f'Amount: Rs {total:.2f}',
            f'Payment note: {order_id}',
        ]
    )

    if request is not None:
        pay_url = request.build_absolute_uri(f'/order/{order.id}/pay/')
        lines.extend(['', f'Payment page: {pay_url}'])

    maps_query = full_address or order.address or ''
    if maps_query:
        maps_link = (
            'https://www.google.com/maps/search/?api=1&query=' + quote(maps_query)
        )
        lines.extend(['', f'Location: {maps_link}'])

    return '\n'.join(lines)


def build_order_whatsapp_url(order, request=None, paid=None, phone=None):
    """wa.me link that opens WhatsApp with product + order details prefilled."""
    message = build_order_message(order, request=request, paid=paid)
    number = phone or get_whatsapp_number()
    return 'https://wa.me/' + number + '?text=' + quote(message)


def build_order_whatsapp_urls(order, request=None, paid=None):
    """WhatsApp order links for every shop number."""
    message = build_order_message(order, request=request, paid=paid)
    return [
        {
            'phone': n,
            'display': f'+{n}' if not n.startswith('+') else n,
            'url': 'https://wa.me/' + n + '?text=' + quote(message),
        }
        for n in get_whatsapp_numbers()
    ]


def normalize_whatsapp_phone(phone):
    """Normalize Indian mobile numbers to digits for wa.me."""
    if not phone:
        return ''
    digits = ''.join(ch for ch in str(phone) if ch.isdigit())
    if not digits:
        return ''
    # 10-digit Indian mobile → add 91
    if len(digits) == 10 and digits[0] in '6789':
        return '91' + digits
    # Already has country code
    if digits.startswith('91') and len(digits) >= 12:
        return digits
    return digits


def build_payment_confirmation_message(order, request=None):
    """
    Confirmation message after payment is completed (for shop WhatsApp).
    """
    order_id = f'FLORA{order.id}'
    total = float(order.get_total_cost())
    customer = f'{order.first_name} {order.last_name}'.strip()
    full_address = ', '.join(
        part
        for part in [order.address, order.city, order.postal_code, order.country]
        if part
    )

    lines = [
        '*Payment confirmed - Flora Shop Thrissur*',
        '',
        f'*Order ID:* {order_id}',
        f'*Status:* PAID ✓',
        f'*Amount received:* Rs {total:.2f}',
        f'*Customer UPI (payer):* {getattr(order, "payer_upi_id", "") or "-"}',
        f'*UTR / ref:* {getattr(order, "payment_ref", "") or "-"}',
        '',
        '*Customer:*',
        f'Name: {customer}',
        f'Phone: {order.phone or "-"}',
        f'Address: {full_address or "-"}',
        '',
        '*Products (stock reduced):*',
    ]

    for i, item in enumerate(
        order.items.select_related('product', 'product__category').all(), start=1
    ):
        product = item.product
        name = product.name if product else 'Deleted product'
        size = (item.size or '').strip() or 'N/A'
        qty = int(item.quantity or 0)
        subtotal = float(item.price or 0) * qty
        lines.append(f'{i}) {name} | Size: {size} | Qty: {qty} | Rs {subtotal:.2f}')

    lines.extend(
        [
            '',
            f'*Total: Rs {total:.2f}*',
            '',
            'Please pack and arrange delivery for this paid order.',
        ]
    )
    return '\n'.join(lines)


def build_payment_confirmation_whatsapp_url(order, request=None, phone=None):
    """
    WhatsApp link to a shop number with payment confirmation + order details.
    """
    message = build_payment_confirmation_message(order, request=request)
    number = phone or get_whatsapp_number()
    return 'https://wa.me/' + number + '?text=' + quote(message)


def build_payment_confirmation_whatsapp_urls(order, request=None):
    """Payment confirmation links for all shop WhatsApp numbers."""
    message = build_payment_confirmation_message(order, request=request)
    return [
        {
            'phone': n,
            'display': f'+{n[:2]} {n[2:]}' if len(n) > 2 else n,
            'url': 'https://wa.me/' + n + '?text=' + quote(message),
        }
        for n in get_whatsapp_numbers()
    ]


def build_customer_confirmation_whatsapp_url(order, request=None):
    """
    Optional: WhatsApp link to the customer's phone with order confirmation.
    Returns None if phone cannot be normalized.
    """
    phone = normalize_whatsapp_phone(order.phone)
    if not phone:
        return None

    order_id = f'FLORA{order.id}'
    total = float(order.get_total_cost())
    customer = f'{order.first_name} {order.last_name}'.strip() or 'Customer'

    lines = [
        f'Hi {customer},',
        '',
        'Thank you for shopping at *Flora Shop Thrissur*!',
        '',
        f'Your payment for order *{order_id}* is *confirmed*.',
        f'Amount: *Rs {total:.2f}*',
        '',
        '*Items:*',
    ]
    for item in order.items.select_related('product').all():
        name = item.product.name if item.product else 'Item'
        size = (item.size or '').strip()
        size_txt = f' (Size {size})' if size else ''
        lines.append(f'• {name}{size_txt} x {item.quantity}')

    lines.extend(
        [
            '',
            'We will pack your order soon. For help, reply on this chat.',
            '',
            '— Flora Shop Thrissur',
        ]
    )
    return 'https://wa.me/' + phone + '?text=' + quote('\n'.join(lines))

