from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.utils import timezone
from django.db.models import Index, UniqueConstraint
from django.contrib.auth.models import User
from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile
from flora_project.settings import compress_image


def _maybe_compress(image_field):
    """Compress only brand-new uploads (not already-stored files)."""
    if not image_field:
        return image_field
    # Fresh upload object
    if isinstance(image_field, (InMemoryUploadedFile, TemporaryUploadedFile)):
        return compress_image(image_field)
    # FieldFile wrapping a new upload
    f = getattr(image_field, 'file', None)
    if isinstance(f, (InMemoryUploadedFile, TemporaryUploadedFile)):
        return compress_image(image_field)
    return image_field


def _persist_image(field_file):
    """Store image bytes in DB so they survive Render redeploys."""
    if not field_file:
        return
    try:
        from .media_storage import persist_media_blob
        persist_media_blob(field_file)
    except Exception:
        # Never break admin save if blob sync fails
        pass


class MediaBlob(models.Model):
    """
    Durable copy of uploaded media (Postgres).
    Render free disk is ephemeral; this keeps product images available.
    """
    path = models.CharField(max_length=500, unique=True, db_index=True)
    data = models.BinaryField()
    content_type = models.CharField(max_length=100, default='image/jpeg')
    size = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['path']

    def __str__(self):
        return f"MediaBlob({self.path}, {self.size} bytes)"


class Order(models.Model):
    first_name = models.CharField(max_length=200)
    last_name = models.CharField(max_length=200, blank=True)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    address = models.CharField(max_length=500)
    city = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default='India')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order #{self.id} - {self.first_name} {self.last_name}"

    def get_total_cost(self):
        return sum(item.price * item.quantity for item in self.items.all())

    def mark_as_paid(self):
        """
        ONLY path that reduces stock. Call after confirmed UPI payment.
        - Sets paid=Yes for admin
        - Decreases ProductSize stock for ordered size (if any)
        - Decreases Product.stock
        - Never runs twice (idempotent)
        Returns True if newly marked paid, False if already paid.
        """
        from django.db import transaction

        with transaction.atomic():
            order = Order.objects.select_for_update().get(pk=self.pk)
            # Guard: never reduce stock without payment / never double-deduct
            if order.paid:
                return False

            for item in order.items.select_related('product').all():
                if not item.product or not item.quantity:
                    continue
                qty = int(item.quantity)
                size = (item.size or '').strip()

                product = Product.objects.select_for_update().get(pk=item.product_id)

                if size:
                    size_row = (
                        ProductSize.objects.select_for_update()
                        .filter(product=product, size=size)
                        .first()
                    )
                    if size_row:
                        new_qty = max(0, int(size_row.quantity) - qty)
                        size_row.quantity = new_qty
                        size_row.available = new_qty > 0
                        size_row.save(update_fields=['quantity', 'available'])

                product.stock = max(0, int(product.stock) - qty)
                product.save(update_fields=['stock'])

            order.paid = True
            order.save(update_fields=['paid'])
            self.paid = True
            return True


class Category(models.Model):
    """Product categories for organizing the shop"""
    CATEGORY_TYPE_CHOICES = [
        ('women', 'Women'),
        ('kids', 'Kids'),
    ]
    
    name = models.CharField(max_length=200, db_index=True)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField(blank=True, null=True)
    category_type = models.CharField(max_length=20, choices=CATEGORY_TYPE_CHOICES, default='women')
    image = models.ImageField(upload_to='categories/', blank=True,null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'category'
        verbose_name_plural = 'categories'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        self.image = _maybe_compress(self.image)
        super().save(*args, **kwargs)
        _persist_image(self.image)

    def get_absolute_url(self):
        return reverse('shop:product_list_by_category', args=[self.slug])


class Product(models.Model):
    """Product model for all items in the shop"""
    PRODUCT_TYPE_CHOICES = [
        ('women', 'Women'),
        ('kids', 'Kids'),
    ]

    STYLE_CHOICES = [
        ('traditional', 'Traditional'),
        ('western', 'Western'),
        ('fusion', 'Fusion'),
    ]

    category = models.ForeignKey(Category, related_name='products', on_delete=models.CASCADE)
    name = models.CharField(max_length=200, db_index=True)
    slug = models.SlugField(max_length=200, db_index=True)
    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPE_CHOICES, default='women')
    style = models.CharField(max_length=20, choices=STYLE_CHOICES, default='traditional')
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    available = models.BooleanField(default=True)
    stock = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    featured = models.BooleanField(default=False)
    
    # Additional product details
    material = models.CharField(max_length=100, blank=True)
    care_instructions = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [Index(fields=['id', 'slug'])]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('shop:product_detail', args=[self.id, self.slug])

    def get_display_price(self):
        """Return the price to display (discount price if available)"""
        return self.discount_price if self.discount_price else self.price

    def get_discount_percentage(self):
        """Calculate discount percentage"""
        if self.discount_price and self.price > self.discount_price:
            return int(((self.price - self.discount_price) / self.price) * 100)
        return 0


class ProductImage(models.Model):
    """Multiple images for each product"""
    product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='products/')
    is_primary = models.BooleanField(default=False)
    alt_text = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_primary', 'created_at']

    def __str__(self):
        return f"Image for {self.product.name}"

    def save(self, *args, **kwargs):
        self.image = _maybe_compress(self.image)
        super().save(*args, **kwargs)
        _persist_image(self.image)


class OfferSale(models.Model):
    """Admin-managed sale offers shown on the homepage."""
    image = models.ImageField(upload_to='offers/', blank=True, null=True)
    active = models.BooleanField(default=True)
    start_date = models.DateTimeField(blank=True, null=True)
    end_date = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at', '-updated_at']
        verbose_name = 'offer sale'
        verbose_name_plural = 'offer sales'

    def __str__(self):
        return f"OfferSale #{self.id}"

    def save(self, *args, **kwargs):
        self.image = _maybe_compress(self.image)
        super().save(*args, **kwargs)
        _persist_image(self.image)

    def is_current(self):
        now = timezone.now()
        if not self.active:
            return False
        if self.start_date and self.start_date > now:
            return False
        if self.end_date and self.end_date < now:
            return False
        return True


class ProductSize(models.Model):
    """Available sizes for products"""
    # Women clothing sizes
    WOMEN_SIZE_CHOICES = [
        ('M', 'Medium'),
        ('L', 'Large'),
        ('XL', 'XL'),
        ('2XL', '2XL'),
        ('3XL', '3XL'),
    ]

    # Kids clothing sizes: 16 (about 1 year) to 30
    KIDS_SIZE_CHOICES = [
        ('16', '16 (1 Year)'),
        ('18', '18 (2 Years)'),
        ('20', '20 (3 Years)'),
        ('22', '22 (4 Years)'),
        ('24', '24 (5-6 Years)'),
        ('26', '26 (7-8 Years)'),
        ('28', '28 (9-10 Years)'),
        ('30', '30 (11-12 Years)'),
    ]

    SIZE_CHOICES = WOMEN_SIZE_CHOICES + KIDS_SIZE_CHOICES

    product = models.ForeignKey(Product, related_name='sizes', on_delete=models.CASCADE)
    size = models.CharField(max_length=10, choices=SIZE_CHOICES)
    quantity = models.PositiveIntegerField(default=0, help_text="Stock quantity available for this size")
    available = models.BooleanField(default=True)

    class Meta:
        constraints = [UniqueConstraint(fields=['product', 'size'], name='unique_product_size')]
        ordering = ['size']

    def __str__(self):
        return f"{self.product.name} - {self.get_size_display()} ({self.quantity} in stock)"

    @classmethod
    def sizes_for_product_type(cls, product_type):
        """Return size choices for women or kids products."""
        if product_type == 'kids':
            return list(cls.KIDS_SIZE_CHOICES)
        return list(cls.WOMEN_SIZE_CHOICES)


# class ProductColor(models.Model):
#     """Available colors for products"""
#     product = models.ForeignKey(Product, related_name='colors', on_delete=models.CASCADE)
#     name = models.CharField(max_length=50)
#     hex_code = models.CharField(max_length=7, help_text="Color hex code (e.g., #FF5733)")
#     available = models.BooleanField(default=True)

#     class Meta:
#         constraints = [UniqueConstraint(fields=['product', 'name'], name='unique_product_color')]
#         ordering = ['name']

#     def __str__(self):
#         return f"{self.product.name} - {self.name}"


class Contact(models.Model):
    """Contact form submissions"""
    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    subject = models.CharField(max_length=200, choices=[
        ('order', 'Order Related'),
        ('return', 'Return & Exchange'),
        ('feedback', 'Feedback'),
        ('partnership', 'Partnership'),
        ('other', 'Other'),
    ])
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.subject}"
    
class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name='order_items', on_delete=models.SET_NULL, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    size = models.CharField(max_length=10, blank=True, null=True)  # ✅ add this
    created_at = models.DateTimeField(auto_now_add=True)

class Blog(models.Model):
    """User-posted blogs/articles"""
    author = models.ForeignKey(User, related_name='blogs', on_delete=models.CASCADE)
    title = models.CharField(max_length=300)
    description = models.TextField()
    image = models.ImageField(upload_to='blogs/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} by {self.author.username}"

    def save(self, *args, **kwargs):
        self.image = _maybe_compress(self.image)
        super().save(*args, **kwargs)
        _persist_image(self.image)
