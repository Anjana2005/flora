# Flora E-Commerce Platform
## Wear the Positivity

Flora is a modern, full-featured e-commerce platform specializing in women's and kids' fashion. Built with Django, it offers a seamless shopping experience with integrated blog functionality.

## Features

### 🛍️ E-Commerce Features
- **Product Management**: Complete product catalog with categories, sizes, colors, and variants
- **Shopping Cart**: Session-based cart with quantity management
- **Product Filtering**: Filter by category, product type, style, and search
- **Responsive Design**: Mobile-friendly interface with modern UI/UX
- **Product Details**: Comprehensive product pages with image galleries
- **Featured Products**: Highlight special items on homepage
- **Discount System**: Support for sale prices and discount percentages

### 📝 Blog System
- **Full Blog Platform**: Create, manage, and publish blog posts
- **Category System**: Organize posts by topics
- **Comments**: User engagement with moderated comments
- **Featured Posts**: Highlight important content
- **Tags**: Additional content organization
- **Views Tracking**: Monitor post popularity

### 🎨 Design Features
- **Modern UI**: Clean, vibrant design with gradient accents
- **Custom Fonts**: Google Fonts integration (Poppins, Playfair Display)
- **Icons**: Font Awesome for beautiful icons
- **Animations**: Smooth transitions and hover effects
- **Color Scheme**: Pink/Purple gradient theme reflecting positivity

### 🔧 Technical Features
- **Django 4.x**: Modern Python web framework
- **Session-based Cart**: No login required for shopping
- **Image Upload**: Support for product and blog images
- **Admin Interface**: Comprehensive Django admin for management
- **SEO Ready**: Meta tags and semantic HTML
- **Pagination**: Efficient content loading

## Installation & Setup

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Step 1: Clone or Download
```bash
cd flora_ecommerce
```

### Step 2: Create Virtual Environment (Recommended)
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Database Setup
```bash
# Create database tables
python manage.py makemigrations
python manage.py migrate
```

### Step 5: Create Superuser (Admin Account)
```bash
python manage.py createsuperuser
```
Follow the prompts to create your admin account.

### Step 6: Create Media Directories
```bash
# Windows
mkdir media\products media\categories media\blog

# Linux/Mac
mkdir -p media/products media/categories media/blog
```

### Step 7: Run Development Server
```bash
python manage.py runserver
```

Visit `http://127.0.0.1:8000` in your browser!

## Usage Guide

### Admin Panel
Access the admin panel at `http://127.0.0.1:8000/admin`

#### Adding Products
1. Login to admin panel
2. Go to "Products" → "Add Product"
3. Fill in product details:
   - Name, category, description
   - Price and discount price (optional)
   - Product type (Women/Kids)
   - Style (Traditional/Western/Fusion)
   - Stock quantity
4. Add product images via "Product Images"
5. Add available sizes via "Product Sizes"
6. Add available colors via "Product Colors"
7. Save

#### Managing Categories
1. Go to "Categories" → "Add Category"
2. Enter name, description
3. Upload category image (optional)
4. Save

#### Creating Blog Posts
1. Go to "Posts" → "Add Post"
2. Fill in title, content, excerpt
3. Select category
4. Upload featured image
5. Set status to "Published"
6. Mark as "Featured" for homepage display
7. Save

#### Managing Comments
1. Comments require admin approval
2. Go to "Comments"
3. Review and activate appropriate comments

### Frontend Usage
- **Homepage**: Browse featured products and categories
- **Shop**: View all products with filtering options
- **Product Detail**: See product information, add to cart
- **Cart**: Review items, update quantities
- **Checkout**: Enter shipping details (demo mode)
- **Blog**: Read fashion tips and style inspiration
- **About/Contact**: Learn about Flora

## Project Structure

```
flora_ecommerce/
├── flora_project/          # Project configuration
│   ├── settings.py         # Django settings
│   ├── urls.py             # URL routing
│   └── wsgi.py             # WSGI config
├── shop/                   # E-commerce app
│   ├── models.py           # Product, Category models
│   ├── views.py            # Shop views
│   ├── admin.py            # Admin configuration
│   └── urls.py             # Shop URLs
├── blog/                   # Blog app
│   ├── models.py           # Post, Comment models
│   ├── views.py            # Blog views
│   ├── admin.py            # Admin configuration
│   └── urls.py             # Blog URLs
├── cart/                   # Shopping cart app
│   ├── cart.py             # Cart class
│   ├── views.py            # Cart views
│   └── context_processors.py
├── templates/              # HTML templates
│   ├── base.html           # Base template
│   ├── shop/               # Shop templates
│   ├── blog/               # Blog templates
│   └── cart/               # Cart templates
├── media/                  # Uploaded files
├── static/                 # Static files (if any)
├── manage.py               # Django management
└── requirements.txt        # Python dependencies
```

## Configuration

### Settings (flora_project/settings.py)
- `DEBUG`: Set to `False` in production
- `SECRET_KEY`: Change for production
- `ALLOWED_HOSTS`: Add your domain
- Database configuration
- Media and static files settings

### Customization
- **Colors**: Edit CSS variables in `templates/base.html`
- **Logo**: Update navbar logo text/icon
- **Content**: Modify text in templates
- **Features**: Add/remove features in footer

## Production Deployment

### Important Changes for Production
1. Set `DEBUG = False` in settings.py
2. Change `SECRET_KEY` to a secure random string
3. Update `ALLOWED_HOSTS` with your domain
4. Use PostgreSQL or MySQL instead of SQLite
5. Configure static files with WhiteNoise or CDN
6. Set up proper media file storage (AWS S3, etc.)
7. Enable HTTPS
8. Configure email backend for notifications

### Recommended Hosting
- Heroku
- DigitalOcean
- AWS Elastic Beanstalk
- PythonAnywhere

## Features Roadmap

### Potential Enhancements
- [ ] User authentication and accounts
- [ ] Wishlist functionality
- [ ] Product reviews and ratings
- [ ] Payment gateway integration
- [ ] Order management system
- [ ] Email notifications
- [ ] Newsletter subscription
- [ ] Social sharing
- [ ] Advanced search
- [ ] Size guide
- [ ] Product recommendations
- [ ] Multi-language support

## Support

For issues or questions:
- Check Django documentation: https://docs.djangoproject.com
- Review code comments in files
- Ensure all dependencies are installed
- Check admin panel for data management

## License

This is a demonstration project for educational purposes.

## Credits

**Created for Flora - Wear the Positivity**

- Framework: Django
- Icons: Font Awesome
- Fonts: Google Fonts (Poppins, Playfair Display)
- Design: Custom modern gradient theme

---

*Happy Shopping! 🌸*"# shopping" 
