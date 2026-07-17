from decimal import Decimal
from django.conf import settings
from shop.models import Product


class Cart:
    """Shopping cart stored in session"""
    
    def __init__(self, request):
        """Initialize the cart"""
        self.session = request.session
        cart = self.session.get(settings.CART_SESSION_ID)
        if not cart:
            # Save an empty cart in the session
            cart = self.session[settings.CART_SESSION_ID] = {}
        self.cart = cart

    def add(self, product, quantity=1, size=None, override_quantity=False):
        """Add a product to the cart or update its quantity"""
        product_id = str(product.id)
        cart_key = f"{product_id}_{size}" if size else product_id
        
        if cart_key not in self.cart:
            self.cart[cart_key] = {
                'quantity': 0,
                'price': str(product.get_display_price()),
                'product_id': product_id,
                'size': size
            }
        if override_quantity:
            self.cart[cart_key]['quantity'] = quantity
        else:
            self.cart[cart_key]['quantity'] += quantity
        self.save()

    def save(self):
        """Mark the session as modified to save changes"""
        self.session.modified = True

    def remove(self, product, size=None):
        """Remove a product from the cart"""
        cart_key = f"{product.id}_{size}" if size else str(product.id)
        if cart_key in self.cart:
            del self.cart[cart_key]
            self.save()

    def __iter__(self):
        """Iterate over the items in the cart and get the products from the database"""
        product_ids = []
        cart_items = []
        
        for cart_key, item_data in self.cart.items():
            if '_' in cart_key:
                product_id, size = cart_key.split('_', 1)
            else:
                product_id = cart_key
                size = None
            
            product_ids.append(product_id)
            cart_items.append({
                'cart_key': cart_key,
                'product_id': product_id,
                'size': size,
                'quantity': item_data['quantity'],
                'price': item_data['price']
            })
        
        products = Product.objects.filter(id__in=product_ids)
        product_dict = {str(p.id): p for p in products}
        
        for item in cart_items:
            product = product_dict.get(item['product_id'])
            if product:
                item['product'] = product
                item['price'] = Decimal(item['price'])
                item['total_price'] = item['price'] * item['quantity']

                # Available stock for the selected size or whole product
                if item['size']:
                    try:
                        product_size = product.sizes.get(size=item['size'])
                        item['size_display'] = product_size.get_size_display()
                        item['available_stock'] = product_size.quantity
                    except Exception:
                        item['size_display'] = item['size']
                        item['available_stock'] = product.stock
                else:
                    item['size_display'] = None
                    item['available_stock'] = product.stock

                yield item

    def __len__(self):
        """Count all items in the cart"""
        return sum(item['quantity'] for item in self.cart.values())

    def get_total_price(self):
        """Calculate the total price of items in the cart"""
        return sum(Decimal(item['price']) * item['quantity'] 
                  for item in self.cart.values())

    def clear(self):
        """Remove cart from session"""
        del self.session[settings.CART_SESSION_ID]
        self.save()