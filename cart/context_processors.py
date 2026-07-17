from .cart import Cart
from shop.models import Category


def cart(request):
    """Make cart available to all templates"""
    return {'cart': Cart(request)}


def categories(request):
    """Make categories available to all templates for navbar dropdowns"""
    women_categories = Category.objects.filter(category_type='women')
    kids_categories = Category.objects.filter(category_type='kids')
    return {
        'women_categories': women_categories,
        'kids_categories': kids_categories,
    }
