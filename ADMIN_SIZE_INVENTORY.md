# Admin Panel: Managing Size Inventory

## How to Set Available Stock for Each Size

### Step-by-Step Guide:

#### **Method 1: Edit Product and Add Size Inventory (Recommended)**

1. **Go to Admin Panel**
   - URL: `http://localhost:8000/admin/`
   - Login with your admin credentials

2. **Navigate to Products**
   - Click: **Shop** → **Products**

3. **Select a Product**
   - Click on the product name you want to manage
   - Example: "FLORASK001"

4. **Find "PRODUCT SIZES" Section**
   - Scroll down on the product edit page
   - You'll see a table titled **"Product sizes"**

5. **Add or Edit Sizes**
   - **To ADD a new size:**
     - Click the **"Add another Product size"** button
     - Select Size (e.g., "Extra Small", "Small", "Medium", etc.)
     - Enter Quantity (e.g., 5)
     - Toggle "Available" checkbox (should be checked)
     - Click Save

   - **To EDIT existing size:**
     - Click on the quantity field in the Product sizes table
     - Change the number (e.g., from 0 to 5)
     - Uncheck "Available" checkbox if out of stock
     - Click Save

#### **Method 2: Manage from Product Size List**

1. **Go to Admin Panel**
   - URL: `http://localhost:8000/admin/`

2. **Navigate to Product Sizes**
   - Click: **Shop** → **Product sizes**

3. **Edit Sizes**
   - Click on a size entry
   - Update **Quantity** field
   - Update **Available** checkbox
   - Click Save

---

## Size Fields Explained

| Field | Description | Example |
|-------|-------------|---------|
| **Product** | Which product this size belongs to | FLORASK001 |
| **Size** | Size option | Extra Small (XS), Small (S), Medium (M), Large (L), Extra Large (XL), Double Extra Large (XXL) |
| **Quantity** | Number of items available for this size | 5, 10, 0 |
| **Available** | Is this size available for purchase? | ✓ Checked = Available, ☐ Unchecked = Hidden from customers |

---

## Example: Setting Up Inventory

**Product: FLORASK001**

| Size | Quantity | Available | Display on Website |
|------|----------|-----------|-------------------|
| Extra Small (XS) | 5 | ✓ | Shows "(5 left)" |
| Small (S) | 10 | ✓ | Shows "(10 left)" |
| Medium (M) | 8 | ✓ | Shows "(8 left)" |
| Large (L) | 0 | ✓ | Shows "Out of Stock" (disabled) |

---

## What Customers Will See

### On Product Detail Page:

**Size Availability Table:**
```
┌─────────────────────────────────────────┐
│ Size Availability                       │
├──────────────┬──────────┬─────────────┤
│ Size         │ Stock    │ Status      │
├──────────────┼──────────┼─────────────┤
│ Extra Small  │ 5        │ In Stock    │
│ Small        │ 10       │ In Stock    │
│ Medium       │ 8        │ In Stock    │
│ Large        │ 0        │ Out of Stock│
├──────────────┴──────────┴─────────────┤
│ Size Selector:                        │
│ [Extra Small (5 left)] [Small (10...] │
│ [Medium (8 left)] [Large Out of Stock]│
└─────────────────────────────────────────┘
```

**Selection Features:**
- Available sizes are clickable (green/enabled)
- Out-of-stock sizes are disabled (grayed out)
- Quantity adjusts to max available for selected size

---

## Tips

✅ **DO:**
- Set quantity to 0 to mark a size as out of stock without deleting it
- Uncheck "Available" checkbox if you want to completely hide a size
- Update quantities regularly based on sales

❌ **DON'T:**
- Delete ProductSize entries (use quantity = 0 instead)
- Leave quantity empty (always enter a number, even if 0)

---

## Database Updates

To automatically populate all sizes for a product with default quantities via bash:

```bash
cd c:\Users\Anjana\Desktop\shopping-main\flora
python manage.py shell

# In Python shell:
from shop.models import Product, ProductSize

product = Product.objects.get(id=6)  # Your product ID
sizes = ['XS', 'S', 'M', 'L', 'XL', 'XXL']

for size in sizes:
    ps, created = ProductSize.objects.get_or_create(
        product=product,
        size=size,
        defaults={'quantity': 10, 'available': True}
    )
    if created:
        print(f"Created {size}: 10 items")
    else:
        print(f"{size} already exists")
```
