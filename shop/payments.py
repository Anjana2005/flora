"""UPI / WhatsApp helpers for Flora orders."""
from urllib.parse import quote

from django.conf import settings


def get_upi_id():
    # Keep VPA exactly as registered in the bank/UPI app (no spaces)
    return (getattr(settings, 'UPI_ID', None) or 'flora1101@axl').strip()


def get_upi_name():
    return (getattr(settings, 'UPI_MERCHANT_NAME', None) or 'Flora').strip()


def get_whatsapp_number():
    return getattr(settings, 'WHATSAPP_ORDER_NUMBER', '919074860867')


def _amount_str(amount):
    """UPI amount: two decimals, no commas, no currency symbol."""
    return f"{float(amount):.2f}"


def build_upi_link(amount, order_ref, note=None):
    """
    Build a standard UPI deep link (NPCI pay intent).

    Important: do NOT pre-percent-encode the whole query with urlencode and then
    encode again for QR — that turns @ into %2540 and apps reject the payee.
    Keep `pa` (UPI ID) raw; only encode name/note values that may have spaces.
    """
    pa = get_upi_id()
    pn = get_upi_name()
    am = _amount_str(amount)
    tn = (note or f"Order {order_ref}")[:50]

    # Raw @ in pa is required so single encoding (QR / browser) is correct
    return (
        "upi://pay"
        f"?pa={pa}"
        f"&pn={quote(pn, safe='')}"
        f"&am={am}"
        f"&cu=INR"
        f"&tn={quote(tn, safe='')}"
    )


def build_upi_qr_url(upi_link, size=280):
    """
    QR image that encodes the UPI string once.
    Encode the full deep-link once for the image API query param.
    """
    return (
        "https://api.qrserver.com/v1/create-qr-code/"
        f"?size={size}x{size}&margin=8&data={quote(upi_link, safe='')}"
    )


def build_gpay_link(amount, order_ref):
    """Google Pay — try modern gpay:// first; tez:// as fallback is same query."""
    base = build_upi_link(amount, order_ref)
    # Same query string as upi://pay?...
    query = base.split('?', 1)[1]
    return f"gpay://upi/pay?{query}"


def build_gpay_tez_link(amount, order_ref):
    base = build_upi_link(amount, order_ref)
    query = base.split('?', 1)[1]
    return f"tez://upi/pay?{query}"


def build_phonepe_link(amount, order_ref):
    base = build_upi_link(amount, order_ref)
    query = base.split('?', 1)[1]
    return f"phonepe://pay?{query}"


def build_paytm_link(amount, order_ref):
    base = build_upi_link(amount, order_ref)
    query = base.split('?', 1)[1]
    return f"paytmmp://pay?{query}"


def build_order_whatsapp_url(order, request=None):
    """
    WhatsApp share for the shop.
    Plain UPI ID + amount (never embed a fragile upi:// inside WA text).
    """
    order_id = f"FLORA{order.id}"
    total = float(order.get_total_cost())
    full_address = ", ".join(
        part
        for part in [order.address, order.city, order.postal_code, order.country]
        if part
    )

    lines = [
        "*New Order - Flora*",
        "",
        f"Order ID: {order_id}",
        f"Customer: {order.first_name} {order.last_name}".strip(),
        f"Phone: {order.phone}",
        f"Address: {full_address}",
        "",
        "*Order Details:*",
    ]

    for item in order.items.select_related('product', 'product__category').all():
        category_name = (
            item.product.category.name
            if item.product and item.product.category
            else "N/A"
        )
        product_name = item.product.name if item.product else "Deleted Product"
        size = item.size or "Not selected"
        qty = item.quantity
        subtotal = float(item.price) * qty
        lines.extend(
            [
                f"* {product_name}",
                f"Category: {category_name}",
                f"Size: {size}",
                f"Qty: {qty}",
                f"Price: Rs {subtotal:.2f}",
                "",
            ]
        )

    maps_link = (
        "https://www.google.com/maps/search/?api=1&query="
        + quote(full_address or order.address or "")
    )

    payment_page = ""
    if request is not None:
        payment_page = request.build_absolute_uri(f"/order/{order.id}/pay/")

    lines.extend(
        [
            f"*Total Amount:* Rs {total:.2f}",
            "",
            "*How to pay (UPI):*",
            f"1) Open GPay / PhonePe / Paytm",
            f"2) Send money to: {get_upi_id()}",
            f"3) Amount: Rs {total:.2f}",
            f"4) Add note: {order_id}",
        ]
    )
    if payment_page:
        lines.extend(["", "Or open payment page:", payment_page])

    lines.extend(["", "Location Map:", maps_link])

    message = "\n".join(lines)
    return "https://wa.me/" + get_whatsapp_number() + "?text=" + quote(message)
