from django.core.management.base import BaseCommand
from orders.models import ShippingZone

ZONES = [
    # Greater Cairo & surroundings
    ('Cairo', 30, 1),
    ('Giza', 30, 1),
    ('Qalyubia', 35, 2),
    # Alexandria
    ('Alexandria', 30, 2),
    # Delta
    ('Dakahlia', 40, 3),
    ('Sharqia', 40, 3),
    ('Gharbia', 40, 3),
    ('Monufia', 40, 3),
    ('Beheira', 40, 3),
    ('Kafr El Sheikh', 40, 3),
    ('Damietta', 40, 3),
    # Canal Zone
    ('Port Said', 45, 3),
    ('Ismailia', 45, 3),
    ('Suez', 45, 3),
    # Upper Egypt
    ('Fayoum', 50, 4),
    ('Beni Suef', 50, 4),
    ('Minya', 50, 4),
    ('Assiut', 50, 5),
    ('Sohag', 50, 5),
    ('Qena', 55, 5),
    ('Luxor', 55, 5),
    ('Aswan', 60, 6),
    # Remote / Border
    ('North Sinai', 60, 5),
    ('South Sinai', 60, 6),
    ('Red Sea', 60, 6),
    ('New Valley', 70, 7),
    ('Matrouh', 70, 7),
]


class Command(BaseCommand):
    help = 'Seed shipping zones for all Egyptian governorates'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help='Delete all zones first')

    def handle(self, *args, **options):
        if options['reset']:
            ShippingZone.objects.all().delete()
            self.stdout.write('Deleted all existing shipping zones.')

        created = updated = 0
        for governorate, fee, days in ZONES:
            obj, was_created = ShippingZone.objects.update_or_create(
                governorate=governorate,
                defaults={'shipping_fee': fee, 'delivery_days': days, 'is_active': True},
            )
            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(self.style.SUCCESS(
            f'Done: {created} created, {updated} updated.'
        ))
