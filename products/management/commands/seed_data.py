from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from products.models import Category, Product, ProductImage
import os
import urllib.request
from pathlib import Path
from django.conf import settings

User = get_user_model()

CATEGORIES = [
    ('Bracelets', 'bracelets', 0),
    ('Necklaces', 'necklaces', 1),
    ('Rings', 'rings', 2),
    ('Anklets', 'anklets', 3),
    ('Chains', 'chains', 4),
    ('Sets', 'sets', 5),
]

PRODUCTS = [
    {
        'name': 'Rose Gold Charm Bracelet',
        'category': 'bracelets',
        'description': 'A delicate rose gold charm bracelet featuring tiny heart pendants. Perfect for everyday wear or gifting to someone special.',
        'price': '350.00',
        'sale_price': None,
        'stock': 15,
        'badge': 'new',
    },
    {
        'name': 'Pearl & Crystal Bracelet',
        'category': 'bracelets',
        'description': 'Elegant freshwater pearls paired with sparkling crystals. This luxurious bracelet adds a touch of sophistication to any outfit.',
        'price': '480.00',
        'sale_price': '380.00',
        'stock': 8,
        'badge': 'sale',
    },
    {
        'name': 'Gold Layered Necklace',
        'category': 'necklaces',
        'description': 'A stunning multi-layer gold necklace that effortlessly elevates any look. Features three delicate chains at different lengths.',
        'price': '520.00',
        'sale_price': None,
        'stock': 12,
        'badge': 'bestseller',
    },
    {
        'name': 'Dainty Star Pendant Necklace',
        'category': 'necklaces',
        'description': 'A minimalist star pendant on a fine gold chain. The perfect everyday necklace for the modern woman.',
        'price': '299.00',
        'sale_price': None,
        'stock': 20,
        'badge': 'new',
    },
    {
        'name': 'Crystal Stackable Ring Set',
        'category': 'rings',
        'description': 'A set of 3 delicate rings designed to be worn together or separately. Features one plain band, one with tiny diamonds, and one with a dainty flower.',
        'price': '390.00',
        'sale_price': '299.00',
        'stock': 10,
        'badge': 'sale',
    },
    {
        'name': 'Adjustable Moonstone Ring',
        'category': 'rings',
        'description': 'A beautiful adjustable ring featuring a genuine moonstone. One size fits all — the perfect gift.',
        'price': '425.00',
        'sale_price': None,
        'stock': 6,
        'badge': 'limited',
    },
    {
        'name': 'Delicate Gold Anklet',
        'category': 'anklets',
        'description': 'A barely-there gold anklet that adds a subtle shimmer to your step. Adjustable length for a perfect fit.',
        'price': '280.00',
        'sale_price': None,
        'stock': 18,
        'badge': 'new',
    },
    {
        'name': 'Boho Beaded Anklet',
        'category': 'anklets',
        'description': 'A colorful beaded anklet with a bohemian flair. Perfect for summer days at the beach or casual outings.',
        'price': '195.00',
        'sale_price': '150.00',
        'stock': 25,
        'badge': 'sale',
    },
    {
        'name': 'Figaro Gold Chain',
        'category': 'chains',
        'description': 'A classic Figaro chain in 18K gold-plated sterling silver. Timeless, versatile, and perfect for layering.',
        'price': '650.00',
        'sale_price': None,
        'stock': 7,
        'badge': 'bestseller',
    },
    {
        'name': 'Bridal Jewelry Set',
        'category': 'sets',
        'description': 'A complete bridal set including necklace, bracelet, earrings, and ring — all in matching rose gold with pearl accents.',
        'price': '1200.00',
        'sale_price': '950.00',
        'stock': 3,
        'badge': 'limited',
    },
]


def create_placeholder_image(product_slug):
    """Create a simple SVG placeholder image for a product."""
    media_dir = Path(settings.MEDIA_ROOT) / 'products'
    media_dir.mkdir(parents=True, exist_ok=True)

    filename = f'{product_slug}_placeholder.svg'
    filepath = media_dir / filename

    colors = {
        'bracelets': ('#E8C4C4', '#C4919191'),
        'necklaces': ('#C4D4E8', '#9191B4C4'),
        'rings': ('#E8E4C4', '#C4B991C4'),
        'anklets': ('#C4E8C4', '#91C491C4'),
        'chains': ('#E8D4C4', '#C4A191C4'),
        'sets': ('#D4C4E8', '#A191C4C4'),
    }

    slug_parts = product_slug.split('-')
    category_hint = slug_parts[-1] if slug_parts else 'default'

    bg_color = '#F5EEE6'
    accent_color = '#E8C4C4'

    for cat, (bg, acc) in colors.items():
        if cat in product_slug:
            bg_color = bg
            accent_color = acc
            break

    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="400" viewBox="0 0 400 400">
  <rect width="400" height="400" fill="{bg_color}"/>
  <circle cx="200" cy="200" r="80" fill="none" stroke="{accent_color}" stroke-width="2"/>
  <circle cx="200" cy="200" r="60" fill="none" stroke="{accent_color}" stroke-width="1" stroke-dasharray="5,3"/>
  <path d="M160 200 Q200 160 240 200 Q200 240 160 200" fill="{accent_color}" opacity="0.6"/>
  <text x="200" y="320" text-anchor="middle" font-family="Georgia, serif" font-size="16" fill="#999" font-style="italic">SheGlow</text>
</svg>'''

    with open(filepath, 'w') as f:
        f.write(svg_content)

    return f'products/{filename}'


class Command(BaseCommand):
    help = 'Seed the database with sample categories and products'

    def add_arguments(self, parser):
        parser.add_argument('--superuser', action='store_true', help='Also create a superuser (admin@sheglow.com / admin123)')

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('Creating categories...'))
        cat_objects = {}
        for name, slug, order in CATEGORIES:
            cat, created = Category.objects.get_or_create(
                slug=slug,
                defaults={'name': name, 'is_active': True, 'order': order}
            )
            cat_objects[slug] = cat
            status = 'Created' if created else 'Already exists'
            self.stdout.write(f'  {status}: {name}')

        self.stdout.write(self.style.MIGRATE_HEADING('Creating products...'))
        for p_data in PRODUCTS:
            cat_slug = p_data.get('category')
            category = cat_objects.get(cat_slug)

            product, created = Product.objects.update_or_create(
                name=p_data['name'],
                defaults={
                    'category': category,
                    'description': p_data['description'],
                    'price': p_data['price'],
                    'sale_price': p_data.get('sale_price'),
                    'stock': p_data['stock'],
                    'badge': p_data.get('badge', ''),
                    'is_active': True,
                }
            )

            if created:
                if not product.images.exists():
                    image_path = create_placeholder_image(product.slug)
                    ProductImage.objects.create(
                        product=product,
                        image=image_path,
                        alt_text=product.name,
                        is_primary=True,
                        order=0
                    )
                self.stdout.write(f'  Created: {product.name} [{product.badge or "no badge"}]')
            else:
                self.stdout.write(f'  Updated: {product.name}')

        if options['superuser']:
            if not User.objects.filter(email='admin@sheglow.com').exists():
                User.objects.create_superuser(
                    email='admin@sheglow.com',
                    password='admin123',
                    first_name='Admin',
                    last_name='SheGlow',
                )
                self.stdout.write(self.style.SUCCESS('Superuser created: admin@sheglow.com / admin123'))
            else:
                self.stdout.write('Superuser already exists')

        self.stdout.write(self.style.SUCCESS(f'\n✓ Seed complete! {len(PRODUCTS)} products in {len(CATEGORIES)} categories.'))
        self.stdout.write(self.style.SUCCESS('  Run: python manage.py runserver'))
