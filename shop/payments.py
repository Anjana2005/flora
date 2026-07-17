"""UPI / WhatsApp helpers for Flora orders."""
from urllib.parse import quote

from django.conf import settings


def get_upi_id():
    return (getattr(settings, 'UPI_ID', None) or '7591927789@fam').strip()


def get_upi_name():
    # Empty by default — wrong payee name breaks UPI deep links for personal VPAs
    return (getattr(settings, 'UPI_MERCHANT_NAME', None) or '').strip()


def get_whatsapp_number():
    return (
        getattr(settings, 'WHATSAPP_ORDER_NUMBER', None) or '919074860867'
    ).strip().replace('+', '').replace(' ', '')


def _amount_str(amount):
    return f"{float(amount):.2f}"


def build_upi_link(amount, order_ref, note=None):
    """
    Personal UPI pay intent (minimal params).
    Do not force a wrong `pn` — that breaks many apps while manual pay still works.
    """
    pa = get_upi_id()
    am = _amount_str(amount)
    tn = ''.join(ch for ch in (note or str(order_ref)) if ch.isalnum())[:40] or 'FloraOrder'

    parts = [
        f'pa={pa}',
        f'am={am}',
        'cu=INR',
        f'tn={tn}',
    ]
    pn = get_upi_name()
    if pn:
        parts.insert(1, f'pn={quote(pn, safe="")}')

    return 'upi://pay?' + '&'.join(parts)


def build_upi_qr_url(upi_link, size=280):
    return (
        'https://api.qrserver.com/v1/create-qr-code/'
        f'?size={size}x{size}&margin=10&data={quote(upi_link, safe="")}'
    )


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


def build_order_whatsapp_url(order, request=None, paid=None):
    """wa.me link that opens WhatsApp with product + order details prefilled."""
    message = build_order_message(order, request=request, paid=paid)
    return 'https://wa.me/' + get_whatsapp_number() + '?text=' + quote(message)


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


def build_payment_confirmation_whatsapp_url(order, request=None):
    """
    WhatsApp link to the shop number with payment confirmation + order details.
    """
    message = build_payment_confirmation_message(order, request=request)
    return 'https://wa.me/' + get_whatsapp_number() + '?text=' + quote(message)


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

