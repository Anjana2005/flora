from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.contrib import messages
from urllib.parse import quote

from shop.models import Product, Order, OrderItem
from .cart import Cart
from urllib.parse import quote


@require_POST
def cart_add(request, product_id):
    """Add product to cart"""
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    quantity = int(request.POST.get('quantity', 1))
    size = request.POST.get('size') or None

    # Validate size selection if product has sizes
    if product.sizes.exists() and not size:
        messages.error(request, 'Please select a size.')
        return redirect('shop:product_detail', id=product.id, slug=product.slug)

    # Check if selected size is available
    if size:
        try:
            product_size = product.sizes.get(size=size)
            if product_size.quantity < quantity:
                messages.error(
                    request,
                    f'Only {product_size.quantity} items available in size {product_size.get_size_display()}.'
                )
                return redirect('shop:product_detail', id=product.id, slug=product.slug)
        except Exception:
            messages.error(request, 'Selected size is not available.')
            return redirect('shop:product_detail', id=product.id, slug=product.slug)
    elif product.stock < quantity:
        messages.error(request, f'Only {product.stock} items available.')
        return redirect('shop:product_detail', id=product.id, slug=product.slug)

    cart.add(product=product, quantity=quantity, size=size, override_quantity=False)
    size_text = f" (Size: {dict(product.sizes.model.SIZE_CHOICES).get(size, size)})" if size else ""
    messages.success(request, f'{product.name}{size_text} added to cart!')

    # Buy Now goes straight to checkout; normal Add to Cart stays on cart page
    if request.POST.get('buy_now') == '1':
        return redirect('cart:checkout')
    return redirect('cart:cart_detail')


@require_POST
def cart_remove(request, product_id):
    """Remove product from cart"""
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    size = request.POST.get('size') or None
    cart.remove(product, size)
    size_text = f" (Size: {dict(product.sizes.model.SIZE_CHOICES).get(size, size)})" if size else ""
    messages.success(request, f'{product.name}{size_text} removed from cart!')
    return redirect('cart:cart_detail')


def cart_detail(request):
    """Display cart contents"""
    cart = Cart(request)

    for item in cart:
        item['update_quantity_form'] = {
            'quantity': item['quantity'],
            'override': True
        }

    context = {
        'cart': cart,
    }
    return render(request, 'cart/detail.html', context)


@require_POST
def cart_update(request, product_id):
    """Update product quantity in cart"""
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    quantity = int(request.POST.get('quantity', 1))
    size = request.POST.get('size') or None

    if quantity > 0:
        if size:
            try:
                product_size = product.sizes.get(size=size)
                if product_size.quantity < quantity:
                    messages.error(
                        request,
                        f'Only {product_size.quantity} items available in size {product_size.get_size_display()}.'
                    )
                    return redirect('cart:cart_detail')
            except Exception:
                messages.error(request, 'Selected size is not available.')
                return redirect('cart:cart_detail')
        elif product.stock < quantity:
            messages.error(request, f'Only {product.stock} items available.')
            return redirect('cart:cart_detail')

        cart.add(product=product, quantity=quantity, size=size, override_quantity=True)
        messages.success(request, 'Cart updated!')
    else:
        cart.remove(product, size)
        size_text = f" (Size: {dict(product.sizes.model.SIZE_CHOICES).get(size, size)})" if size else ""
        messages.success(request, f'{product.name}{size_text} removed from cart!')

    return redirect('cart:cart_detail')


def checkout(request):
    """Checkout page - place order and open WhatsApp with plain-text order details."""
    cart = Cart(request)

    if len(cart) == 0:
        messages.warning(request, 'Your cart is empty!')
        return redirect('shop:product_list')

    if request.method == 'POST':
        try:
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            email = request.POST.get('email', '').strip()
            phone = request.POST.get('phone', '').strip()
            address = request.POST.get('address', '').strip()
            city = request.POST.get('city', '').strip()
            postal = request.POST.get('postal', '').strip()
            country = request.POST.get('country', 'India').strip() or 'India'

            order = Order.objects.create(
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                address=address,
                city=city,
                postal_code=postal,
                country=country,
            )

            for item in cart:
                OrderItem.objects.create(
                    order=order,
                    product=item.get('product'),
                    price=item.get('price'),
                    quantity=item.get('quantity'),
                    size=item.get('size') or '',
                )

            order_items = OrderItem.objects.select_related(
                'product', 'product__category'
            ).filter(order=order)

            order_id = f"FLORA{order.id}"
            full_address = ", ".join(part for part in [address, city, postal, country] if part)

            lines = [
                "*New Order - Flora*",
                "",
                f"Order ID: {order_id}",
                f"Customer: {first_name} {last_name}".strip(),
                f"Phone: {phone}",
                f"Address: {full_address}",
                "",
                "*Order Details:*",
            ]

            total = 0
            for item in order_items:
                category_name = item.product.category.name if item.product and item.product.category else "N/A"
                product_name = item.product.name if item.product else "Deleted Product"
                size = item.size or "Not selected"
                qty = item.quantity
                price = float(item.price)
                subtotal = price * qty
                total += subtotal

                lines.extend([
                    f"* {product_name}",
                    f"Category: {category_name}",
                    f"Size: {size}",
                    f"Qty: {qty}",
                    f"Price: ₹{subtotal:.2f}",
                    "",
                ])

            maps_query = quote(full_address or address or "")
            maps_link = "https://www.google.com/maps/search/?api=1&query=" + maps_query
            merchant_name = "Flora Store"
            upi_link = (
                f"upi://pay?pa=flora1101@axl"
                f"&pn={quote(merchant_name)}"
                f"&am={total:.2f}"
                f"&cu=INR"
                f"&tn={quote(f'Order {order_id}')}" 
            )

            lines.extend([
                f"*Total Amount:* ₹{total:.2f}",
                "",
                "Location Map:",
                maps_link,
                "",
                "Pay here:",
                upi_link,
            ])

            message = "\n".join(lines)
            cart.clear()

            whatsapp_number = "919074860867"
            whatsapp_url = "https://wa.me/" + whatsapp_number + "?text=" + quote(message)
            return redirect(whatsapp_url)

        except Exception as e:
            messages.error(request, f'Error placing order: {str(e)}')

    context = {
        'cart': cart,
    }
    return render(request, 'cart/checkout.html', context)
