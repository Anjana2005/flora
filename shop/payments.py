"""UPI / WhatsApp helpers for Flora orders."""
from urllib.parse import quote

from django.conf import settings


def get_upi_id():
    return (getattr(settings, 'UPI_ID', None) or '7591927789@fam').strip()


def get_upi_name():
    # Optional display name — wrong pn often makes GPay/PhonePe fail
    # when deep-linking, while manual entry still works.
    return (getattr(settings, 'UPI_MERCHANT_NAME', None) or '').strip()


def get_whatsapp_number():
    return getattr(settings, 'WHATSAPP_ORDER_NUMBER', '919074860867')


def _amount_str(amount):
    return f"{float(amount):.2f}"


def build_upi_link(amount, order_ref, note=None):
    """
    Personal UPI pay intent (works like manual “Send money to UPI ID”).

    Why site buttons used to fail while manual app pay worked:
    - Passing a wrong `pn` (payee name) makes many apps reject the transfer
      even when the UPI ID is valid. Manual entry looks up the real name.
    - Keep the intent minimal: pa + am + cu (+ short tn).
    """
    pa = get_upi_id()
    am = _amount_str(amount)
    # Note: keep short and simple (letters/numbers only if possible)
    tn = ''.join(ch for ch in (note or str(order_ref)) if ch.isalnum())[:40] or 'FloraOrder'

    # Do NOT pre-encode @ in pa. Build query manually.
    parts = [
        f'pa={pa}',
        f'am={am}',
        'cu=INR',
        f'tn={tn}',
    ]
    # Only include pn if explicitly set and non-empty (must match bank name)
    pn = get_upi_name()
    if pn:
        parts.insert(1, f'pn={quote(pn, safe="")}')

    return 'upi://pay?' + '&'.join(parts)


def build_upi_qr_url(upi_link, size=280):
    """Single-encode the full UPI string for the QR image API."""
    return (
        'https://api.qrserver.com/v1/create-qr-code/'
        f'?size={size}x{size}&margin=10&data={quote(upi_link, safe="")}'
    )


def build_android_intent_link(amount, order_ref):
    """
    Android Chrome-friendly intent URL (more reliable than raw upi:// from web).
    """
    base = build_upi_link(amount, order_ref)
    query = base.split('?', 1)[1]
    # package-less intent lets user pick any UPI app
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


def build_order_whatsapp_url(order, request=None):
    order_id = f'FLORA{order.id}'
    total = float(order.get_total_cost())
    full_address = ', '.join(
        part
        for part in [order.address, order.city, order.postal_code, order.country]
        if part
    )

    lines = [
        '*New Order - Flora*',
        '',
        f'Order ID: {order_id}',
        f'Customer: {order.first_name} {order.last_name}'.strip(),
        f'Phone: {order.phone}',
        f'Address: {full_address}',
        '',
        '*Order Details:*',
    ]

    for item in order.items.select_related('product', 'product__category').all():
        category_name = (
            item.product.category.name
            if item.product and item.product.category
            else 'N/A'
        )
        product_name = item.product.name if item.product else 'Deleted Product'
        size = item.size or 'Not selected'
        qty = item.quantity
        subtotal = float(item.price) * qty
        lines.extend(
            [
                f'* {product_name}',
                f'Category: {category_name}',
                f'Size: {size}',
                f'Qty: {qty}',
                f'Price: Rs {subtotal:.2f}',
                '',
            ]
        )

    maps_link = (
        'https://www.google.com/maps/search/?api=1&query='
        + quote(full_address or order.address or '')
    )

    payment_page = ''
    if request is not None:
        payment_page = request.build_absolute_uri(f'/order/{order.id}/pay/')

    lines.extend(
        [
            f'*Total Amount:* Rs {total:.2f}',
            '',
            '*Pay via UPI (manual — most reliable):*',
            f'UPI ID: {get_upi_id()}',
            f'Amount: Rs {total:.2f}',
            f'Note: {order_id}',
        ]
    )
    if payment_page:
        lines.extend(['', 'Payment page:', payment_page])
    lines.extend(['', 'Location Map:', maps_link])

    message = '\n'.join(lines)
    return 'https://wa.me/' + get_whatsapp_number() + '?text=' + quote(message)
