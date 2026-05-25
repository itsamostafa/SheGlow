from django.db import migrations, models


class Migration(migrations.Migration):
    """Make phone NOT NULL (all values were populated in migration 0004)."""

    dependencies = [
        ('accounts', '0004_phone_primary_auth'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='phone',
            field=models.CharField(
                max_length=20,
                unique=True,
                verbose_name='phone number',
            ),
        ),
    ]
