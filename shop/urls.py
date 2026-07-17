from django.urls import path
from . import views

app_name = 'shop'

urlpatterns = [
    path('', views.home, name='home'),
    path('shop/', views.product_list, name='product_list'),
    path('shop/<slug:category_slug>/', views.product_list, name='product_list_by_category'),
    path('offers/', views.offer_center, name='offer_center'),
    path('product/<int:id>/<slug:slug>/', views.product_detail, name='product_detail'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('checkout/', views.checkout, name='checkout'),
    path('order/<int:order_id>/pay/', views.order_pay, name='order_pay'),

    # Blog URLs
    path('blog/create/', views.create_blog, name='create_blog'),
    path('blog/', views.blog_list, name='blog_list'),
    path('blog/<int:id>/', views.blog_detail, name='blog_detail'),
    path('blog/<int:id>/edit/', views.edit_blog, name='edit_blog'),
    path('blog/<int:id>/delete/', views.delete_blog, name='delete_blog'),
    
    # Admin URLs (using dashboard instead of admin to avoid conflict with Django admin)
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('dashboard/products/', views.admin_products, name='admin_products'),
    path('dashboard/products/create/', views.admin_product_create, name='admin_product_create'),
    path('dashboard/products/<int:id>/', views.admin_product_detail, name='admin_product_detail'),
    path('dashboard/products/<int:id>/delete/', views.admin_product_delete, name='admin_product_delete'),
    path('dashboard/products/<int:id>/add-image/', views.admin_product_add_image, name='admin_product_add_image'),
    path('dashboard/products/image/<int:id>/delete/', views.admin_product_delete_image, name='admin_product_delete_image'),
    path('dashboard/categories/', views.admin_categories, name='admin_categories'),
    path('dashboard/categories/create/', views.admin_category_create, name='admin_category_create'),
    path('dashboard/categories/<int:id>/', views.admin_category_detail, name='admin_category_detail'),
    path('dashboard/categories/<int:id>/delete/', views.admin_category_delete, name='admin_category_delete'),
    path('dashboard/contacts/', views.admin_contacts, name='admin_contacts'),
    path('dashboard/contacts/<int:id>/', views.admin_contact_detail, name='admin_contact_detail'),
    path('dashboard/contacts/<int:id>/delete/', views.admin_contact_delete, name='admin_contact_delete'),
    path('dashboard/contacts/<int:id>/reply/', views.admin_contact_reply, name='admin_contact_reply'),
    path('dashboard/orders/', views.admin_orders, name='admin_orders'),
    path('dashboard/orders/<int:id>/', views.admin_order_detail, name='admin_order_detail'),
    path('dashboard/blogs/', views.admin_blogs, name='admin_blogs'),
    path('dashboard/blogs/create/', views.admin_blog_create, name='admin_blog_create'),
    path('dashboard/blogs/<int:id>/', views.admin_blog_detail, name='admin_blog_detail'),
    path('dashboard/blogs/<int:id>/edit/', views.admin_blog_edit, name='admin_blog_edit'),
    path('dashboard/blogs/<int:id>/delete/', views.admin_blog_delete, name='admin_blog_delete'),
    path('dashboard/offers/', views.admin_offers, name='admin_offers'),
    path('dashboard/offers/create/', views.admin_offer_create, name='admin_offer_create'),
    path('dashboard/offers/<int:id>/', views.admin_offer_detail, name='admin_offer_detail'),
    path('dashboard/offers/<int:id>/edit/', views.admin_offer_edit, name='admin_offer_edit'),
    path('dashboard/offers/<int:id>/delete/', views.admin_offer_delete, name='admin_offer_delete'),
    path('profile/', views.profile, name='profile'),
]