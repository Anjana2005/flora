# from urllib import request
# from django.shortcuts import render, get_object_or_404, redirect
# from django.core.paginator import Paginator
# from django.contrib.auth import authenticate, login
# from django.contrib.auth.models import User
# from django.contrib.auth.decorators import login_required
# from django.contrib import messages
# from .models import Category, Product, Contact
# from django.contrib.auth.decorators import login_required
# from django.shortcuts import render
# from django.contrib.auth.decorators import login_required
# from django.shortcuts import render
# from .models import Order
import json
import os
from urllib import request as urllib_request
from urllib.parse import urlencode
from cart.cart import Cart

from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import datetime
from .models import Category, Product, Contact, Order, OrderItem, OfferSale

# def cart_add(request, product_id):
#     product = Product.objects.get(id=product_id)
#     cart = request.session.get("cart", {})

#     size = request.POST.get("size") or cart.get(str(product_id), {}).get("size")
#     quantity = int(request.POST.get("quantity", 1))

#     print("=== CART ADD DEBUG ===")
#     print("Product:", product.name)
#     print("Size from POST:", request.POST.get("size"))
#     print("Quantity:", quantity)
#     print("Cart before:", cart)

#     cart[str(product_id)] = {
#         "name": product.name,
#         "price": float(product.get_display_price()),
#         "quantity": quantity,
#         "size": size,
#     }

#     request.session["cart"] = cart
#     request.session.modified = True

#     print("Cart after:", cart)
#     print("======================")

#     return redirect("cart:cart_detail")


def resolve_google_place_id():
    api_key = os.environ.get('GOOGLE_PLACES_API_KEY', '').strip()
    if not api_key:
        return ''

    place_id = os.environ.get('GOOGLE_PLACE_ID', '').strip()
    if place_id:
        return place_id

    # Use the known Flora place ID when no environment value is set.
    default_flora_place_id = 'ChIJ47M4SnrvpzsRZ06fOD9XFzs'
    if default_flora_place_id:
        return default_flora_place_id

    place_query = os.environ.get('GOOGLE_PLACE_QUERY', 'Flora Thrissur, Kerala').strip()
    if not place_query:
        return ''

    endpoint = 'https://maps.googleapis.com/maps/api/place/findplacefromtext/json'
    params = {
        'input': place_query,
        'inputtype': 'textquery',
        'fields': 'place_id',
        'language': 'en',
        'key': api_key,
    }

    try:
        url = f"{endpoint}?{urlencode(params)}"
        with urllib_request.urlopen(url, timeout=10) as response:
            payload = response.read().decode('utf-8')
        data = json.loads(payload)
        candidates = data.get('candidates', [])
        if candidates:
            return candidates[0].get('place_id', '')
    except Exception:
        return ''

    return ''


def fetch_google_reviews():
    api_key = os.environ.get('GOOGLE_PLACES_API_KEY', '').strip()
    place_id = resolve_google_place_id()
    if not api_key or not place_id:
        return []

    endpoint = 'https://maps.googleapis.com/maps/api/place/details/json'
    params = {
        'place_id': place_id,
        'fields': 'reviews',
        'language': 'en',
        'key': api_key,
    }

    try:
        url = f"{endpoint}?{urlencode(params)}"
        with urllib_request.urlopen(url, timeout=10) as response:
            payload = response.read().decode('utf-8')
        data = json.loads(payload)
        reviews = data.get('result', {}).get('reviews', []) or []

        filtered_reviews = []
        for review in reviews:
            rating = int(review.get('rating', 0))
            if rating >= 3:
                filtered_reviews.append({
                    'author_name': review.get('author_name', 'Customer'),
                    'rating': rating,
                    'stars': '★' * min(5, max(0, rating)),
                    'text': review.get('text', ''),
                    'relative_time_description': review.get('relative_time_description', ''),
                })
        return filtered_reviews
    except Exception:
        return []


@login_required
def profile(request):
    raw_orders = Order.objects.filter(email=request.user.email).order_by('-created_at')
    orders = []
    total_spent = 0
    for order in raw_orders:
        order.total = sum(item.price * item.quantity for item in order.items.all())
        total_spent += order.total
        orders.append(order)
    paid_count = sum(1 for o in orders if o.paid)
    return render(request, 'shop/profile.html', {
        'orders': orders,
        'total_spent': total_spent,
        'paid_count': paid_count,
    })

def product_list(request, category_slug=None):
    """Display list of products, optionally filtered by category"""
    category = None
    categories = Category.objects.all()
    products = Product.objects.filter(available=True)
    
    # Filter by category if provided
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=category)
    
    # Filter by product type
    product_type = request.GET.get('type')
    if product_type in ['women', 'kids']:
        products = products.filter(product_type=product_type)
    
    # Filter by style
    style = request.GET.get('style')
    if style in ['traditional', 'western', 'fusion']:
        products = products.filter(style=style)
    
    # Search functionality
    search_query = request.GET.get('search')
    if search_query:
        products = products.filter(name__icontains=search_query)
    
    # Pagination
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'category': category,
        'categories': categories,
        'page_obj': page_obj,
        'products': page_obj,
        'search_query': search_query,
    }
    return render(request, 'shop/product/list.html', context)


def product_detail(request, id, slug):
    """Display individual product details"""
    product = get_object_or_404(Product, id=id, slug=slug, available=True)
    
    # Get related products from the same category
    related_products = Product.objects.filter(
        category=product.category,
        available=True
    ).exclude(id=product.id)[:4]
    
    context = {
        'product': product,
        'related_products': related_products,
    }
    return render(request, 'shop/product/detail.html', context)


def home(request):
    """Home page with featured products"""
    featured_products = Product.objects.filter(featured=True, available=True)[:8]
    categories = Category.objects.all()[:6]
    
    # Get latest products
    new_arrivals = Product.objects.filter(available=True).order_by('-created_at')[:8]

    current_time = timezone.now()
    offer_sale = OfferSale.objects.filter(active=True).filter(
        Q(start_date__lte=current_time) | Q(start_date__isnull=True),
        Q(end_date__gte=current_time) | Q(end_date__isnull=True)
    ).order_by('-created_at', '-updated_at').first()

    google_reviews = fetch_google_reviews()
    if not google_reviews:
        google_reviews = [
            {
                'author_name': 'Dinooj cp',
                'rating': 5,
                'stars': '★★★★★',
                'text': "I recently visited this Flora kids wear store. The collection of kids' clothing here has trendy designs and excellent quality. The staff are friendly and super helpful in finding the perfect outfit. Highly recommend this shop to anyone looking for stylish and affordable kids wear.",
                'review_date': '1 year ago',
            },
            {
                'author_name': 'nesmi Nelson',
                'rating': 5,
                'stars': '★★★★★',
                'text': 'Best Ladies wear collection shop. Party wear, western wear, and other collections are excellent. Prices are reasonable and quality products are great. Highly recommendable.',
                'review_date': '1 month ago',
            },
            {
                'author_name': 'Rasmi Prabhakar',
                'rating': 5,
                'stars': '★★★★★',
                'text': 'I am a fan of the quality of clothes at this place. Their collection is superb, especially the little ones party wear section. This is a one-stop shop for that perfect birthday dress for your princess, plus they have super trendy cord sets as well. Totally fashionable collection, and the staff is very humble.',
                'review_date': '3 weeks ago',
            },
        ]

    context = {
        'featured_products': featured_products,
        'categories': categories,
        'new_arrivals': new_arrivals,
        'offer_sale': offer_sale,
        'google_reviews': google_reviews,
    }
    return render(request, 'shop/home.html', context)


def offer_center(request):
    """User-facing offer center page"""
    current_time = timezone.now()
    offers = OfferSale.objects.filter(active=True).filter(
        Q(start_date__lte=current_time) | Q(start_date__isnull=True),
        Q(end_date__gte=current_time) | Q(end_date__isnull=True)
    ).order_by('-created_at', '-updated_at')

    return render(request, 'shop/offer_center.html', {
        'offers': offers,
    })


def about(request):
    """About page"""
    return render(request, 'shop/about.html')


def contact(request):
    """Contact page"""
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        subject = request.POST.get('subject')
        message = request.POST.get('message')
        
        Contact.objects.create(
            name=name,
            email=email,
            phone=phone,
            subject=subject,
            message=message
        )
        
        messages.success(request, 'Thank you for contacting us! We will get back to you soon.')
        return redirect('shop:contact')
    
    return render(request, 'shop/contact.html')


def signup(request):
    """User signup page"""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        
        # Validation
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists!')
            return redirect('shop:signup')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered!')
            return redirect('shop:signup')
        
        if password1 != password2:
            messages.error(request, 'Passwords do not match!')
            return redirect('shop:signup')
        
        if len(password1) < 8:
            messages.error(request, 'Password must be at least 8 characters long!')
            return redirect('shop:signup')
        
        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password1
        )
        
        messages.success(request, 'Account created successfully! Please log in.')
        return redirect('shop:login')
    
    return render(request, 'shop/signup.html')


def login_view(request):
    """User login page"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            
            # Redirect admin to dashboard, regular users to product list
            if user.is_staff:
                return redirect('shop:admin_dashboard')
            else:
                return redirect('shop:product_list')
        else:
            messages.error(request, 'Invalid username or password!')
            return redirect('shop:login')
    
    return render(request, 'shop/login.html')


def logout_view(request):
    """User logout"""
    from django.contrib.auth import logout
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('shop:home')


# Admin Views
@login_required(login_url='shop:login')
def admin_dashboard(request):
    """Admin dashboard"""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('shop:home')
    
    total_products = Product.objects.count()
    total_categories = Category.objects.count()
    total_contacts = Contact.objects.count()
    unread_contacts = Contact.objects.filter(read=False).count()
    total_offers = OfferSale.objects.count()
    active_offers = OfferSale.objects.filter(active=True).count()
    from .payments import build_payment_confirmation_whatsapp_urls

    total_orders = Order.objects.count()
    paid_orders = Order.objects.filter(paid=True).count()
    unpaid_orders = Order.objects.filter(paid=False).count()
    recent_orders = list(Order.objects.order_by('-created_at')[:8])
    for order in recent_orders:
        if order.paid:
            order.whatsapp_confirm_links = build_payment_confirmation_whatsapp_urls(
                order, request
            )
            order.whatsapp_confirm_url = (
                order.whatsapp_confirm_links[0]['url']
                if order.whatsapp_confirm_links
                else None
            )
        else:
            order.whatsapp_confirm_links = []
            order.whatsapp_confirm_url = None

    context = {
        'total_products': total_products,
        'total_categories': total_categories,
        'total_contacts': total_contacts,
        'unread_contacts': unread_contacts,
        'total_offers': total_offers,
        'active_offers': active_offers,
        'total_orders': total_orders,
        'paid_orders': paid_orders,
        'unpaid_orders': unpaid_orders,
        'recent_orders': recent_orders,
    }
    return render(request, 'shop/admin/dashboard.html', context)


@login_required(login_url='shop:login')
def admin_products(request):
    """Manage products"""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('shop:home')
    
    products = Product.objects.all().order_by('-created_at')
    paginator = Paginator(products, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'products': page_obj,
    }
    return render(request, 'shop/admin/products.html', context)


@login_required(login_url='shop:login')
def admin_product_detail(request, id):
    """View/Edit product"""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('shop:home')
    
    product = get_object_or_404(Product, id=id)
    
    if request.method == 'POST':
        product.name = request.POST.get('name')
        product.description = request.POST.get('description')
        product.price = request.POST.get('price')
        product.discount_price = request.POST.get('discount_price') or None
        product.stock = request.POST.get('stock')
        product.available = request.POST.get('available') == 'on'
        product.featured = request.POST.get('featured') == 'on'
        product.material = request.POST.get('material')
        product.save()

        # Handle sizes with quantities
        from .models import ProductSize
        sizes = request.POST.getlist('sizes')
        
        # Remove sizes that are no longer selected
        ProductSize.objects.filter(product=product).exclude(size__in=sizes).delete()
        
        # Update or create selected sizes
        for size in sizes:
            if size:
                quantity = request.POST.get(f'quantity_{size}', 0)
                try:
                    quantity = int(quantity) if quantity else 0
                except ValueError:
                    quantity = 0
                
                product_size, created = ProductSize.objects.get_or_create(
                    product=product,
                    size=size,
                    defaults={'quantity': quantity, 'available': quantity > 0}
                )
                
                if not created:
                    product_size.quantity = quantity
                    product_size.available = quantity > 0
                    product_size.save()

        messages.success(request, 'Product updated successfully!')
        return redirect('shop:admin_products')
    
    # Prepare sizes with existing product size data
    from .models import ProductSize
    sizes_list = ProductSize.sizes_for_product_type(product.product_type)
    sizes_with_data = []
    
    for value, label in sizes_list:
        product_size = product.sizes.filter(size=value).first()
        sizes_with_data.append({
            'value': value,
            'label': label,
            'product_size': product_size,
        })
    
    context = {
        'product': product,
        'sizes': sizes_with_data,
    }
    return render(request, 'shop/admin/product_detail.html', context)


@login_required(login_url='shop:login')
def admin_product_delete(request, id):
    """Delete product"""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('shop:home')
    
    product = get_object_or_404(Product, id=id)
    
    if request.method == 'POST':
        product.delete()
        messages.success(request, 'Product deleted successfully!')
        return redirect('shop:admin_products')
    
    context = {
        'product': product,
    }
    return render(request, 'shop/admin/product_delete.html', context)


@login_required(login_url='shop:login')
def admin_contacts(request):
    """Manage contact messages"""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('shop:home')
    
    contacts = Contact.objects.all().order_by('-created_at')
    paginator = Paginator(contacts, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'contacts': page_obj,
    }
    return render(request, 'shop/admin/contacts.html', context)


@login_required(login_url='shop:login')
def admin_orders(request):
    """List all orders for admin"""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('shop:home')

    from .payments import build_payment_confirmation_whatsapp_urls

    orders = Order.objects.all().order_by('-created_at')
    paginator = Paginator(orders, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Attach WhatsApp confirmation links for paid orders on this page
    for order in page_obj:
        if order.paid:
            order.whatsapp_confirm_links = build_payment_confirmation_whatsapp_urls(
                order, request
            )
            order.whatsapp_confirm_url = (
                order.whatsapp_confirm_links[0]['url']
                if order.whatsapp_confirm_links
                else None
            )
        else:
            order.whatsapp_confirm_links = []
            order.whatsapp_confirm_url = None

    context = {
        'orders': page_obj,
    }
    return render(request, 'shop/admin/orders.html', context)


@login_required(login_url='shop:login')
def admin_order_detail(request, id):
    """View single order details; staff can mark as paid (reduces size stock)."""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('shop:home')

    from .payments import (
        build_payment_confirmation_whatsapp_urls,
        build_customer_confirmation_whatsapp_url,
        get_whatsapp_numbers,
    )

    order = get_object_or_404(Order, id=id)
    open_shop_whatsapp = False

    if request.method == 'POST' and request.POST.get('action') == 'mark_paid':
        if order.mark_as_paid():
            messages.success(
                request,
                f'Order #FLORA{order.id} marked Paid. Size stock reduced. '
                f'Send WhatsApp confirmation to shop numbers.',
            )
            open_shop_whatsapp = True
        else:
            messages.info(request, 'Order was already marked as paid.')
            open_shop_whatsapp = True  # still allow resending confirmation

    # compute per-item line totals and order total
    from decimal import Decimal
    items = []
    total = Decimal('0.00')
    for item in order.items.select_related('product').all():
        try:
            line_total = (item.price or Decimal('0.00')) * item.quantity
        except Exception:
            line_total = Decimal('0.00')
        setattr(item, 'line_total', line_total)
        items.append(item)
        try:
            total += line_total
        except Exception:
            pass

    shop_whatsapp_links = []
    customer_whatsapp_url = None
    if order.paid:
        shop_whatsapp_links = build_payment_confirmation_whatsapp_urls(order, request)
        customer_whatsapp_url = build_customer_confirmation_whatsapp_url(order, request)

    context = {
        'order': order,
        'items': items,
        'total_amount': total,
        'shop_whatsapp_links': shop_whatsapp_links,
        'shop_whatsapp_url': shop_whatsapp_links[0]['url'] if shop_whatsapp_links else None,
        'customer_whatsapp_url': customer_whatsapp_url,
        'shop_whatsapp_numbers': get_whatsapp_numbers(),
        'open_shop_whatsapp': open_shop_whatsapp and bool(shop_whatsapp_links),
    }
    return render(request, 'shop/admin/order_detail.html', context)


@login_required(login_url='shop:login')
def admin_contact_detail(request, id):
    """View contact message"""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('shop:home')
    
    contact = get_object_or_404(Contact, id=id)
    contact.read = True
    contact.save()
    
    context = {
        'contact': contact,
    }
    return render(request, 'shop/admin/contact_detail.html', context)


@login_required(login_url='shop:login')
def admin_contact_delete(request, id):
    """Delete contact message"""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('shop:home')
    
    contact = get_object_or_404(Contact, id=id)
    
    if request.method == 'POST':
        contact.delete()
        messages.success(request, 'Contact message deleted successfully!')
        return redirect('shop:admin_contacts')
    
    context = {
        'contact': contact,
    }
    return render(request, 'shop/admin/contact_delete.html', context)


@login_required(login_url='shop:login')
def admin_product_create(request):
    """Create new product"""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('shop:home')
    
    if request.method == 'POST':
        try:
            category_id = request.POST.get('category')
            category = get_object_or_404(Category, id=category_id)
            
            product = Product(
                category=category,
                name=request.POST.get('name'),
                product_type=request.POST.get('product_type'),
                style=request.POST.get('style'),
                description=request.POST.get('description'),
                price=request.POST.get('price'),
                discount_price=request.POST.get('discount_price') or None,
                stock=request.POST.get('stock'),
                available=request.POST.get('available') == 'on',
                featured=request.POST.get('featured') == 'on',
                material=request.POST.get('material'),
                care_instructions=request.POST.get('care_instructions'),
            )
            product.save()
            
            # Handle sizes with quantities
            from .models import ProductSize, ProductImage
            sizes = request.POST.getlist('sizes')
            for size in sizes:
                if size:
                    quantity = request.POST.get(f'quantity_{size}', 0)
                    try:
                        quantity = int(quantity) if quantity else 0
                    except ValueError:
                        quantity = 0
                    
                    ProductSize.objects.create(
                        product=product, 
                        size=size, 
                        quantity=quantity,
                        available=quantity > 0
                    )
            
            # Handle image uploads
            images = request.FILES.getlist('images')
            for image in images:
                if image:
                    ProductImage.objects.create(product=product, image=image)
            
            messages.success(request, 'Product created successfully!')
            return redirect('shop:admin_product_detail', id=product.id)
        except Exception as e:
            messages.error(request, f'Error creating product: {str(e)}')
    
    from .models import ProductSize
    categories = Category.objects.all()
    context = {
        'categories': categories,
        'product_types': Product.PRODUCT_TYPE_CHOICES,
        'styles': Product.STYLE_CHOICES,
        'women_sizes': ProductSize.WOMEN_SIZE_CHOICES,
        'kids_sizes': ProductSize.KIDS_SIZE_CHOICES,
        'sizes': ProductSize.WOMEN_SIZE_CHOICES,  # default shown for women
    }
    return render(request, 'shop/admin/product_create.html', context)


@login_required(login_url='shop:login')
def admin_contact_reply(request, id):
    """Reply to contact message via email"""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('shop:home')
    
    contact = get_object_or_404(Contact, id=id)
    
    if request.method == 'POST':
        try:
            from django.core.mail import send_mail
            
            reply_message = request.POST.get('reply_message')
            subject = f"Re: {contact.get_subject_display()}"
            
            send_mail(
                subject,
                reply_message,
                'noreply@florafashion.com',
                [contact.email],
                fail_silently=False,
            )
            
            messages.success(request, f'Email reply sent to {contact.email}!')
            return redirect('shop:admin_contact_detail', id=contact.id)
        except Exception as e:
            messages.error(request, f'Error sending email: {str(e)}')
    
    contact.read = True
    contact.save()
    
    context = {
        'contact': contact,
    }
    return render(request, 'shop/admin/contact_reply.html', context)


# Category Management Views
@login_required(login_url='shop:login')
def admin_categories(request):
    """Manage categories"""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('shop:home')
    
    categories = Category.objects.all().order_by('name')
    paginator = Paginator(categories, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'categories': page_obj,
    }
    return render(request, 'shop/admin/categories.html', context)


@login_required(login_url='shop:login')
def admin_category_create(request):
    """Create new category"""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('shop:home')

    if request.method == 'POST':
        try:
            category = Category(
                name=request.POST.get('name'),
                description=request.POST.get('description'),
                category_type=request.POST.get('category_type'),
            )
            if 'image' in request.FILES:
                category.image = request.FILES['image']
            category.save()

            messages.success(request, 'Category created successfully!')
            return redirect('shop:admin_categories')
        except Exception as e:
            messages.error(request, f'Error creating category: {str(e)}')

    context = {}
    return render(request, 'shop/admin/category_create.html', context)


@login_required(login_url='shop:login')
def admin_category_detail(request, id):
    """View/Edit category"""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('shop:home')
    
    category = get_object_or_404(Category, id=id)
    
    if request.method == 'POST':
        category.name = request.POST.get('name')
        category.description = request.POST.get('description')
        category.category_type = request.POST.get('category_type')
        if 'image' in request.FILES:
            category.image = request.FILES['image']
        category.save()

        messages.success(request, 'Category updated successfully!')
        return redirect('shop:admin_categories')

    context = {
        'category': category,
    }
    return render(request, 'shop/admin/category_detail.html', context)


@login_required(login_url='shop:login')
def admin_category_delete(request, id):
    """Delete category"""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('shop:home')
    
    category = get_object_or_404(Category, id=id)
    
    if request.method == 'POST':
        category.delete()
        messages.success(request, 'Category deleted successfully!')
        return redirect('shop:admin_categories')
    
    context = {
        'category': category,
    }
    return render(request, 'shop/admin/category_delete.html', context)


@login_required(login_url='shop:login')
def admin_product_add_image(request, id):
    """Add images to product"""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('shop:home')
    
    product = get_object_or_404(Product, id=id)
    
    if request.method == 'POST':
        try:
            from .models import ProductImage
            images = request.FILES.getlist('images')
            
            if not images:
                messages.warning(request, 'No images selected.')
            else:
                count = 0
                for image in images:
                    if image:
                        ProductImage.objects.create(product=product, image=image)
                        count += 1
                
                messages.success(request, f'{count} image(s) uploaded successfully!')
        except Exception as e:
            messages.error(request, f'Error uploading images: {str(e)}')
    
    return redirect('shop:admin_product_detail', id=product.id)


@login_required(login_url='shop:login')
def admin_product_delete_image(request, id):
    """Delete product image"""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('shop:home')
    
    from .models import ProductImage
    image = get_object_or_404(ProductImage, id=id)
    product_id = image.product.id
    
    if request.method == 'POST':
        try:
            image.delete()
            messages.success(request, 'Image deleted successfully!')
        except Exception as e:
            messages.error(request, f'Error deleting image: {str(e)}')
    
    return redirect('shop:admin_product_detail', id=product_id)


# ===========================
# BLOG VIEWS
# ===========================

@login_required(login_url='shop:login')
def create_blog(request):
    """Allow logged-in users to create blog posts"""
    if request.method == 'POST':
        from .models import Blog
        
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        image = request.FILES.get('image')
        
        # Validate input
        if not title or not description:
            messages.error(request, 'Title and description are required.')
            return redirect('shop:create_blog')
        
        try:
            blog = Blog(
                author=request.user,
                title=title,
                description=description,
                image=image if image else None
            )
            blog.save()
            messages.success(request, 'Blog post created successfully!')
            return redirect('shop:blog_list')
        except Exception as e:
            messages.error(request, f'Error creating blog: {str(e)}')
            return redirect('shop:create_blog')
    
    return render(request, 'shop/blog/create.html')


def blog_list(request):
    """Display blogs from other users (exclude current user's blogs)"""
    from .models import Blog
    
    # Get all blogs
    blogs = Blog.objects.all().order_by('-created_at')
    
    # Exclude current user's blogs if logged in
    if request.user.is_authenticated:
        blogs = blogs.exclude(author=request.user)
    
    # Pagination
    paginator = Paginator(blogs, 9)  # 9 blogs per page
    page_number = request.GET.get('page', 1)
    blogs = paginator.get_page(page_number)
    
    context = {
        'blogs': blogs,
        'total_count': paginator.count,
    }
    
    return render(request, 'shop/blog/list.html', context)


def blog_detail(request, id):
    """Display single blog post details"""
    from .models import Blog
    
    blog = get_object_or_404(Blog, id=id)
    
    context = {
        'blog': blog,
    }
    
    return render(request, 'shop/blog/detail.html', context)


@login_required(login_url='shop:login')
def edit_blog(request, id):
    """Allow users to edit their own blog posts"""
    from .models import Blog
    
    blog = get_object_or_404(Blog, id=id)
    
    # Check if user is the author
    if blog.author != request.user:
        messages.error(request, 'You do not have permission to edit this blog.')
        return redirect('shop:blog_list')
    
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        image = request.FILES.get('image')
        
        if not title or not description:
            messages.error(request, 'Title and description are required.')
            return redirect('shop:edit_blog', id=id)
        
        try:
            blog.title = title
            blog.description = description
            if image:
                blog.image = image
            blog.save()
            messages.success(request, 'Blog post updated successfully!')
            return redirect('shop:blog_detail', id=blog.id)
        except Exception as e:
            messages.error(request, f'Error updating blog: {str(e)}')
            return redirect('shop:edit_blog', id=id)
    
    context = {
        'blog': blog,
        'is_edit': True,
    }
    
    return render(request, 'shop/blog/create.html', context)


@login_required(login_url='shop:login')
def delete_blog(request, id):
    """Allow users to delete their own blog posts"""
    from .models import Blog
    
    blog = get_object_or_404(Blog, id=id)
    
    # Check if user is the author
    if blog.author != request.user:
        messages.error(request, 'You do not have permission to delete this blog.')
        return redirect('shop:blog_list')
    
    if request.method == 'POST':
        try:
            blog.delete()
            messages.success(request, 'Blog post deleted successfully!')
            return redirect('shop:blog_list')
        except Exception as e:
            messages.error(request, f'Error deleting blog: {str(e)}')
    
    return render(request, 'shop/blog/delete_confirm.html', {'blog': blog})


# ===========================
# ADMIN BLOG MANAGEMENT
# ===========================

def admin_blogs(request):
    """Admin view to manage all blogs"""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('shop:home')
    
    from .models import Blog
    
    # Get all blogs with pagination
    blogs = Blog.objects.all().order_by('-created_at')
    
    paginator = Paginator(blogs, 10)
    page_number = request.GET.get('page', 1)
    blogs = paginator.get_page(page_number)
    
    context = {
        'blogs': blogs,
        'total_count': paginator.count,
    }
    
    return render(request, 'shop/admin/blogs.html', context)


def admin_blog_detail(request, id):
    """Admin view to see blog details"""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('shop:home')
    
    from .models import Blog
    
    blog = get_object_or_404(Blog, id=id)
    
    context = {
        'blog': blog,
    }
    
    return render(request, 'shop/admin/blog_detail.html', context)


def admin_blog_create(request):
    """Admin view to create blogs"""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('shop:home')
    
    from .models import Blog
    
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        author_id = request.POST.get('author')
        image = request.FILES.get('image')
        
        if not title or not description or not author_id:
            messages.error(request, 'Title, description, and author are required.')
            return redirect('shop:admin_blog_create')
        
        try:
            author = User.objects.get(id=author_id)
            blog = Blog(
                author=author,
                title=title,
                description=description,
                image=image if image else None
            )
            blog.save()
            messages.success(request, 'Blog post created successfully!')
            return redirect('shop:admin_blog_detail', id=blog.id)
        except User.DoesNotExist:
            messages.error(request, 'Selected author does not exist.')
            return redirect('shop:admin_blog_create')
        except Exception as e:
            messages.error(request, f'Error creating blog: {str(e)}')
            return redirect('shop:admin_blog_create')
    
    # Get all users for author selection
    users = User.objects.all().order_by('username')
    context = {
        'users': users,
    }
    
    return render(request, 'shop/admin/blog_create.html', context)


def admin_blog_edit(request, id):
    """Admin view to edit any blog"""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('shop:home')
    
    from .models import Blog
    
    blog = get_object_or_404(Blog, id=id)
    
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        author_id = request.POST.get('author')
        image = request.FILES.get('image')
        
        if not title or not description or not author_id:
            messages.error(request, 'Title, description, and author are required.')
            return redirect('shop:admin_blog_edit', id=id)
        
        try:
            author = User.objects.get(id=author_id)
            blog.title = title
            blog.description = description
            blog.author = author
            if image:
                blog.image = image
            blog.save()
            messages.success(request, 'Blog post updated successfully!')
            return redirect('shop:admin_blog_detail', id=blog.id)
        except User.DoesNotExist:
            messages.error(request, 'Selected author does not exist.')
            return redirect('shop:admin_blog_edit', id=id)
        except Exception as e:
            messages.error(request, f'Error updating blog: {str(e)}')
            return redirect('shop:admin_blog_edit', id=id)
    
    # Get all users for author selection
    users = User.objects.all().order_by('username')
    context = {
        'blog': blog,
        'users': users,
        'is_edit': True,
    }
    
    return render(request, 'shop/admin/blog_create.html', context)


def admin_blog_delete(request, id):
    """Admin view to delete any blog"""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('shop:home')
    
    from .models import Blog
    
    blog = get_object_or_404(Blog, id=id)
    
    if request.method == 'POST':
        try:
            blog.delete()
            messages.success(request, 'Blog post deleted successfully!')
            return redirect('shop:admin_blogs')
        except Exception as e:
            messages.error(request, f'Error deleting blog: {str(e)}')
    
    return render(request, 'shop/admin/blog_delete_confirm.html', {'blog': blog})


@login_required(login_url='shop:login')
def admin_offers(request):
    """Admin view to manage sale offers"""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('shop:home')

    offers = OfferSale.objects.all().order_by('-start_date', '-updated_at')
    paginator = Paginator(offers, 10)
    page_number = request.GET.get('page', 1)
    offers = paginator.get_page(page_number)

    context = {
        'offers': offers,
        'total_count': paginator.count,
    }
    return render(request, 'shop/admin/offers.html', context)


@login_required(login_url='shop:login')
def admin_offer_detail(request, id):
    """Admin view to see offer detail"""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('shop:home')

    offer = get_object_or_404(OfferSale, id=id)

    context = {
        'offer': offer,
    }
    return render(request, 'shop/admin/offer_detail.html', context)


@login_required(login_url='shop:login')
def admin_offer_create(request):
    """Admin view to create a new offer"""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('shop:home')

    if request.method == 'POST':
        image = request.FILES.get('image')
        active = request.POST.get('active') == 'on'
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')

        if not image:
            messages.error(request, 'Offer image is required.')
            return redirect('shop:admin_offer_create')

        start_dt = None
        end_dt = None
        try:
            if start_date:
                start_dt = timezone.make_aware(datetime.fromisoformat(start_date))
            if end_date:
                end_dt = timezone.make_aware(datetime.fromisoformat(end_date))
        except ValueError:
            messages.error(request, 'Invalid date format. Use the provided date picker.')
            return redirect('shop:admin_offer_create')

        offer = OfferSale.objects.create(
            image=image,
            active=active,
            start_date=start_dt,
            end_date=end_dt,
        )

        messages.success(request, 'Offer created successfully!')
        return redirect('shop:admin_offer_detail', id=offer.id)

    return render(request, 'shop/admin/offer_create.html', {'is_edit': False})


@login_required(login_url='shop:login')
def admin_offer_edit(request, id):
    """Admin view to edit a sale offer"""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('shop:home')

    offer = get_object_or_404(OfferSale, id=id)

    if request.method == 'POST':
        image = request.FILES.get('image')
        active = request.POST.get('active') == 'on'
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')

        start_dt = None
        end_dt = None
        try:
            if start_date:
                start_dt = timezone.make_aware(datetime.fromisoformat(start_date))
            if end_date:
                end_dt = timezone.make_aware(datetime.fromisoformat(end_date))
        except ValueError:
            messages.error(request, 'Invalid date format. Use the provided date picker.')
            return redirect('shop:admin_offer_edit', id=id)

        if image:
            offer.image = image
        offer.active = active
        offer.start_date = start_dt
        offer.end_date = end_dt
        offer.save()

        messages.success(request, 'Offer updated successfully!')
        return redirect('shop:admin_offer_detail', id=offer.id)

    context = {
        'offer': offer,
        'is_edit': True,
    }
    return render(request, 'shop/admin/offer_create.html', context)


@login_required(login_url='shop:login')
def admin_offer_delete(request, id):
    """Admin view to delete a sale offer"""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('shop:home')

    offer = get_object_or_404(OfferSale, id=id)

    if request.method == 'POST':
        offer.delete()
        messages.success(request, 'Offer deleted successfully!')
        return redirect('shop:admin_offers')

    return render(request, 'shop/admin/offer_delete_confirm.html', {'offer': offer})


def checkout(request):
    """Place order, then show UPI payment page (also used by cart checkout form)."""
    from cart.cart import Cart
    from .payments import get_upi_id, _amount_str

    cart = Cart(request)

    from .payments import is_valid_upi_id

    def _checkout_context(extra=None):
        ctx = {
            'cart': cart,
            'upi_id': get_upi_id(),
            'order_total': cart.get_total_price(),
            'order_total_str': _amount_str(cart.get_total_price()),
        }
        if extra:
            ctx.update(extra)
        return ctx

    if len(cart) == 0 and request.method != "POST":
        messages.warning(request, 'Your cart is empty!')
        return redirect('shop:product_list')

    if request.method == "POST":
        try:
            first_name = request.POST.get("first_name", "").strip()
            last_name = request.POST.get("last_name", "").strip()
            email = request.POST.get("email", "").strip()
            phone = request.POST.get("phone", "").strip()
            address = request.POST.get("address", "").strip()
            city = request.POST.get("city", "").strip()
            postal = request.POST.get("postal", "").strip()
            country = "India"
            # Customer UPI ID (textarea) — required to reduce spam fake payments
            payer_upi = (request.POST.get("payer_upi_id") or "").strip().lower()
            payer_upi = "".join(payer_upi.split())

            if not first_name or not phone or not address:
                messages.error(request, 'Please fill name, phone and address.')
                return render(
                    request,
                    "cart/checkout.html",
                    _checkout_context({'payer_upi_id': request.POST.get('payer_upi_id', '')}),
                )

            if not is_valid_upi_id(payer_upi):
                messages.error(
                    request,
                    'Please enter your UPI ID in the box (example: yourname@oksbi).',
                )
                return render(
                    request,
                    "cart/checkout.html",
                    _checkout_context({'payer_upi_id': request.POST.get('payer_upi_id', '')}),
                )

            if payer_upi == get_upi_id().lower():
                messages.error(
                    request,
                    'Enter YOUR UPI ID (the one you will pay from), not the shop UPI.',
                )
                return render(
                    request,
                    "cart/checkout.html",
                    _checkout_context({'payer_upi_id': request.POST.get('payer_upi_id', '')}),
                )

            order = Order.objects.create(
                first_name=first_name,
                last_name=last_name,
                email=email or f"order{phone}@flora.local",
                phone=phone,
                address=address,
                city=city,
                postal_code=postal,
                country=country,
                payer_upi_id=payer_upi,
            )

            for item in cart:
                OrderItem.objects.create(
                    order=order,
                    product=item['product'],
                    price=item['price'],
                    quantity=item['quantity'],
                    size=item.get('size') or "",
                )

            cart.clear()
            request.session['last_order_id'] = order.id
            return redirect('shop:order_pay', order_id=order.id)
        except Exception as e:
            messages.error(request, f'Error placing order: {str(e)}')

    return render(request, "cart/checkout.html", _checkout_context())


def order_pay(request, order_id):
    """
    Payment page: UPI scanner only.
    QR changes every 2 minutes (unique tr/slot per order).
    """
    from .payments import build_order_payment_qr, get_upi_id
    from django.urls import reverse

    order = get_object_or_404(Order, id=order_id)

    if order.paid:
        return redirect('shop:order_paid_success', order_id=order.id)

    # Scanner hits site URL → Paid: Yes + WhatsApp to shop
    scan_page_url = request.build_absolute_uri(
        reverse('shop:order_launch_payment', args=[order.id]) + '?method=scan'
    )
    payment = build_order_payment_qr(order, scan_page_url=scan_page_url)

    context = {
        'order': order,
        'order_ref': payment['order_ref'],
        'payment_tr': payment['tr'],
        'qr_slot': payment['slot'],
        'seconds_left': payment['seconds_left'],
        'rotate_seconds': payment['rotate_seconds'],
        'total': order.get_total_cost(),
        'amount_str': payment['amount_str'],
        'shop_upi_id': payment['shop_upi_id'],
        'upi_id': get_upi_id(),
        'payer_upi_id': order.payer_upi_id,
        'upi_link': payment['upi_link'],
        'qr_url': payment['qr_url'],
        'scan_page_url': scan_page_url,
        'qr_api_url': reverse('shop:order_payment_qr_api', args=[order.id]),
        'items': order.items.select_related('product').all(),
    }
    return render(request, 'shop/order_pay.html', context)


def order_payment_qr_api(request, order_id):
    """JSON: fresh UPI scanner for this order (rotates every 2 minutes)."""
    from .payments import build_order_payment_qr
    from django.http import JsonResponse
    from django.urls import reverse

    order = get_object_or_404(Order, id=order_id)
    if order.paid:
        return JsonResponse({'paid': True, 'redirect': reverse('shop:order_paid_success', args=[order.id])})

    scan_page_url = request.build_absolute_uri(
        reverse('shop:order_launch_payment', args=[order.id]) + '?method=scan'
    )
    payment = build_order_payment_qr(order, scan_page_url=scan_page_url)
    return JsonResponse(
        {
            'paid': False,
            'order_ref': payment['order_ref'],
            'tr': payment['tr'],
            'slot': payment['slot'],
            'seconds_left': payment['seconds_left'],
            'rotate_seconds': payment['rotate_seconds'],
            'amount_str': payment['amount_str'],
            'shop_upi_id': payment['shop_upi_id'],
            'upi_link': payment['upi_link'],
            'qr_url': payment['qr_url'],
        }
    )


def order_launch_payment(request, order_id):
    """
    Called when this order's UPI scanner is scanned (or pay link opened).

    1) Always sets order.paid = True so admin shows Paid: Yes ✓
    2) Reduces stock once via mark_as_paid
    3) Opens real UPI app for money transfer, then shop WhatsApp
    """
    from .payments import (
        build_payment_confirmation_whatsapp_url,
        build_order_payment_qr,
        is_valid_upi_id,
    )
    from django.http import HttpResponse
    from django.utils.html import escape

    order = get_object_or_404(Order, id=order_id)
    method = (request.GET.get('method') or 'scan').lower()

    # --- Admin Paid: Yes as soon as this order's scanner is used ---
    if not order.paid:
        payer = (order.payer_upi_id or '').strip().lower()
        if not is_valid_upi_id(payer):
            payer = 'via-scanner'
        order.mark_as_paid(payer_upi_id=payer)
    order.refresh_from_db()

    # Hard fallback so dashboard never stays Paid: No after a scan hit
    if not order.paid:
        Order.objects.filter(pk=order.pk).update(paid=True, payer_upi_id=(order.payer_upi_id or 'via-scanner')[:100])
        order.refresh_from_db()

    whatsapp_url = build_payment_confirmation_whatsapp_url(order, request)
    payment = build_order_payment_qr(order)
    upi_link = payment.get('upi_link') or ''
    amount = payment.get('amount_str') or ''
    shop_upi = payment.get('shop_upi_id') or ''
    order_ref = payment.get('order_ref') or f'FLORA{order.id}'

    # Direct deep-link methods → UPI app only (paid already saved)
    if method in ('upi', 'gpay', 'phonepe', 'paytm', 'android') and upi_link:
        from django.http import HttpResponseRedirect
        return HttpResponseRedirect(upi_link)

    # Scanner / default: confirm Paid, try UPI, then WhatsApp to shop
    safe_wa = escape(whatsapp_url)
    safe_upi = escape(upi_link)
    safe_ref = escape(str(order_ref))
    safe_amt = escape(str(amount))
    safe_shop = escape(str(shop_upi))
    html = f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Paid · {safe_ref}</title>
<style>
  body{{font-family:system-ui,sans-serif;background:#fff7f9;color:#5A3F4A;margin:0;padding:2rem 1rem;text-align:center}}
  .card{{max-width:400px;margin:0 auto;background:#fff;border-radius:20px;padding:1.5rem;box-shadow:0 12px 28px rgba(232,122,150,.15)}}
  h1{{font-size:1.35rem;margin:0 0 .5rem}}
  .ok{{display:inline-block;background:#e8f5e9;color:#1b5e20;font-weight:800;padding:.35rem .75rem;border-radius:999px;margin:.5rem 0 1rem}}
  .amt{{font-size:1.75rem;font-weight:800;color:#E87A96}}
  a.btn{{display:block;margin:.55rem 0;padding:.85rem 1rem;border-radius:12px;text-decoration:none;font-weight:700}}
  .upi{{background:#E87A96;color:#fff}}
  .wa{{background:#25D366;color:#fff}}
  p{{font-size:.92rem;line-height:1.45;color:#666}}
</style>
</head><body>
<div class="card">
  <h1>Order {safe_ref}</h1>
  <div class="ok">Admin: Paid Yes ✓</div>
  <div class="amt">₹{safe_amt}</div>
  <p>Payment recorded for the shop. Complete UPI if your app did not open, then notify the shop on WhatsApp.</p>
  <p style="font-size:.85rem">Shop UPI: <strong>{safe_shop}</strong></p>
  <a class="btn upi" id="upi-btn" href="{safe_upi}">Open UPI payment</a>
  <a class="btn wa" id="wa-btn" href="{safe_wa}">WhatsApp shop (tap Send)</a>
</div>
<script>
(function(){{
  var upi = {upi_link!r};
  var wa = {whatsapp_url!r};
  // Try UPI app first so money can transfer
  if (upi) {{
    try {{ window.location.href = upi; }} catch (e) {{}}
  }}
  // Then open shop WhatsApp so order is notified (admin already Paid: Yes)
  setTimeout(function(){{
    try {{ window.location.href = wa; }} catch (e) {{}}
  }}, 2800);
}})();
</script>
</body></html>"""
    return HttpResponse(html)


def order_confirm_paid(request, order_id):
    """Redirect to payment page — confirmation uses checkout UPI textarea only."""
    return redirect('shop:order_pay', order_id=order_id)


def order_paid_success(request, order_id):
    """If somehow reached without WhatsApp, send them to shop WhatsApp immediately."""
    from .payments import build_payment_confirmation_whatsapp_url
    from django.http import HttpResponseRedirect

    order = get_object_or_404(Order, id=order_id)
    if not order.paid:
        return redirect('shop:order_pay', order_id=order.id)

    # Prefer going straight to shop WhatsApp
    whatsapp_url = build_payment_confirmation_whatsapp_url(order, request)
    if request.GET.get('stay') != '1':
        return HttpResponseRedirect(whatsapp_url)

    return render(
        request,
        'shop/order_paid_success.html',
        {
            'order': order,
            'order_ref': f'FLORA{order.id}',
            'total': order.get_total_cost(),
            'items': order.items.select_related('product').all(),
            'whatsapp_url': whatsapp_url,
            'auto_open_whatsapp': True,
            'payer_upi_id': order.payer_upi_id,
        },
    )


def cart_add_legacy(request, product_id):
    # legacy unused helper kept from older code path
    product = Product.objects.get(id=product_id)
    cart = request.session.get("cart", {})

    size = request.POST.get("size")
    quantity = int(request.POST.get("quantity", 1))

    cart[str(product_id)] = {
        "name": product.name,
        "price": float(product.get_display_price()),
        "quantity": quantity,
        "size": size,
    }

    request.session["cart"] = cart
    request.session.modified = True

    return redirect("cart:cart_detail")
