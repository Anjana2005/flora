from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.contrib import messages

from shop.models import Product, Order, OrderItem
from .cart import Cart


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
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    size = request.POST.get('size') or None
    cart.remove(product, size)
    messages.success(request, 'Item removed from cart.')
    return redirect('cart:cart_detail')


@require_POST
def cart_update(request, product_id):
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
        messages.success(request, 'Item removed from cart!')

    return redirect('cart:cart_detail')


def cart_detail(request):
    cart = Cart(request)
    return render(request, 'cart/detail.html', {'cart': cart})


def checkout(request):
    """Checkout — place order then go to UPI payment page."""
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
            country = 'India'

            if not first_name or not phone or not address:
                messages.error(request, 'Please fill name, phone and address.')
                return render(request, 'cart/checkout.html', {'cart': cart})

            order = Order.objects.create(
                first_name=first_name,
                last_name=last_name,
                email=email or f'order{phone}@flora.local',
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

            cart.clear()
            request.session['last_order_id'] = order.id
            request.session['open_whatsapp_order'] = order.id
            return redirect('shop:order_pay', order_id=order.id)

        except Exception as e:
            messages.error(request, f'Error placing order: {str(e)}')

    return render(request, 'cart/checkout.html', {'cart': cart})
