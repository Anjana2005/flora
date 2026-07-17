"""UPI / WhatsApp helpers for Flora orders."""
from urllib.parse import quote, urlencode

from django.conf import settings


def get_upi_id():
    return getattr(settings, 'UPI_ID', 'flora1101@axl')


def get_upi_name():
    return getattr(settings, 'UPI_MERCHANT_NAME', 'Flora Store')


def get_whatsapp_number():
    return getattr(settings, 'WHATSAPP_ORDER_NUMBER', '919074860867')


def build_upi_link(amount, order_ref, note=None):
    """
    Build a standard UPI deep link.
    amount: number or Decimal
    order_ref: e.g. FLORA12
    """
    am = f"{float(amount):.2f}"
    tn = note or f"Order {order_ref}"
    # urlencode handles spaces/special chars once (do NOT re-quote later)
    query = urlencode(
        {
            'pa': get_upi_id(),
            'pn': get_upi_name(),
            'am': am,
            'cu': 'INR',
            'tn': tn[:80],  # UPI note length limit on some apps
        }
    )
    return f"upi://pay?{query}"


def build_upi_qr_url(upi_link, size=280):
    """QR image URL that encodes the UPI deep link (works on mobile scanners)."""
    return (
        "https://api.qrserver.com/v1/create-qr-code/"
        f"?size={size}x{size}&data={quote(upi_link, safe='')}"
    )


def build_gpay_link(amount, order_ref):
    """Google Pay UPI intent (Android)."""
    am = f"{float(amount):.2f}"
    query = urlencode(
        {
            'pa': get_upi_id(),
            'pn': get_upi_name(),
            'am': am,
            'cu': 'INR',
            'tn': f"Order {order_ref}"[:80],
        }
    )
    return f"tez://upi/pay?{query}"


def build_phonepe_link(amount, order_ref):
    am = f"{float(amount):.2f}"
    query = urlencode(
        {
            'pa': get_upi_id(),
            'pn': get_upi_name(),
            'am': am,
            'cu': 'INR',
            'tn': f"Order {order_ref}"[:80],
        }
    )
    return f"phonepe://pay?{query}"


def build_order_whatsapp_url(order, request=None):
    """
    WhatsApp share message for shop owner.
    Uses PLAIN UPI id + HTTPS payment page (upi:// is often not clickable in WA
    and gets mangled by double-encoding).
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
        payment_page = request.build_absolute_uri(
            f"/order/{order.id}/pay/"
        )

    lines.extend(
        [
            f"*Total Amount:* Rs {total:.2f}",
            "",
            "*Payment (UPI):*",
            f"UPI ID: {get_upi_id()}",
            f"Name: {get_upi_name()}",
            f"Amount: Rs {total:.2f}",
            f"Note: Order {order_id}",
        ]
    )
    if payment_page:
        lines.extend(["", "Customer payment page:", payment_page])

    lines.extend(["", "Location Map:", maps_link])

    message = "\n".join(lines)
    # Encode the whole message ONCE only
    return "https://wa.me/" + get_whatsapp_number() + "?text=" + quote(message)
