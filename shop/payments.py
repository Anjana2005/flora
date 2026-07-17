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
