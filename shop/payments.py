"""UPI / WhatsApp helpers for Flora orders."""
from urllib.parse import quote

from django.conf import settings


def get_upi_id():
    return (getattr(settings, 'UPI_ID', None) or '7591927789@fam').strip()


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


def build_upi_link(amount, order_ref, note=None, tr=None):
    """
    Unique UPI pay intent for a specific order / QR time slot.
    Pure upi:// link so GPay/PhonePe open payment instantly.
    """
    pa = get_upi_id()
    am = _amount_str(amount)
    tn = ''.join(ch for ch in (note or str(order_ref)) if ch.isalnum())[:40] or 'FloraOrder'
    tr_val = ''.join(ch for ch in str(tr or order_ref) if ch.isalnum())[:35] or tn

    parts = [
        f'pa={pa}',
        f'am={am}',
        'cu=INR',
        f'tn={tn}',
        f'tr={tr_val}',
    ]
    pn = get_upi_name()
    if pn:
        parts.insert(1, f'pn={quote(pn, safe="")}')

    return 'upi://pay?' + '&'.join(parts)


def build_upi_qr_url(upi_link, size=280):
    """
    Prefer a local unique QR image (data URI) so every payment has its own scanner.
    Fallback to external API if qrcode is unavailable.
    """
    try:
        return build_upi_qr_data_uri(upi_link, size=size)
    except Exception:
        return (
            'https://api.qrserver.com/v1/create-qr-code/'
            f'?size={size}x{size}&margin=10&data={quote(upi_link, safe="")}'
        )


def build_upi_qr_data_uri(upi_link, size=280):
    """Generate a PNG QR as data URI — unique for this upi_link payload."""
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
    Build UPI link + QR for one order.

    Prefer pure upi:// in the QR so GPay/PhonePe open payment instantly.
    (Admin Paid is set when customer opens the pay-now link / notify path.)
    """
    order_ref = f'FLORA{order.id}'
    amount = order.get_total_cost()
    if slot is None:
        slot, _ = current_qr_slot()
    tr = build_payment_ref(order.id, f'S{slot}')
    upi_link = build_upi_link(amount, order_ref, note=order_ref, tr=tr)

    # Pure UPI in QR = payment app opens in ~1 second (no website wait)
    qr_payload = upi_link

    return {
        'order_ref': order_ref,
        'amount_str': _amount_str(amount),
        'tr': tr,
        'slot': slot,
        'seconds_left': seconds_until_qr_refresh(),
        'rotate_seconds': QR_ROTATE_SECONDS,
        'upi_link': upi_link,
        'qr_url': build_upi_qr_url(qr_payload, size=size),
        'scan_page_url': scan_page_url or '',
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

