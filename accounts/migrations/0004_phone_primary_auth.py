"""
Migration: Phone-first auth — phone becomes the USERNAME_FIELD on User.
"""
from django.db import migrations, models


def populate_phones(apps, schema_editor):
    db = schema_editor.connection
    with db.cursor() as cursor:
        # Get phone → user_id map from Customer (first occurrence wins)
        cursor.execute(
            "SELECT user_id, phone FROM accounts_customer "
            "WHERE phone IS NOT NULL AND phone != '' ORDER BY user_id"
        )
        phone_map = {}
        used_phones = set()
        for user_id, phone in cursor.fetchall():
            phone = phone.strip()
            if phone and phone not in used_phones:
                phone_map[user_id] = phone
                used_phones.add(phone)

        cursor.execute('SELECT id FROM accounts_user ORDER BY id')
        for (user_id,) in cursor.fetchall():
            phone = phone_map.get(user_id, '')
            if not phone:
                # Generate unique placeholder that won't clash
                phone = f'0100000{user_id:04d}'
            cursor.execute(
                'UPDATE accounts_user SET phone_temp = %s WHERE id = %s',
                [phone, user_id]
            )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_wishlist'),
    ]

    operations = [
        # Step 1: Add nullable phone_temp
        migrations.AddField(
            model_name='user',
            name='phone_temp',
            field=models.CharField(max_length=20, null=True, blank=True),
        ),
        # Step 2: Populate from Customer or generate placeholder
        migrations.RunPython(populate_phones, noop),
        # Step 3: Make email nullable (no table rebuild needed)
        migrations.AlterField(
            model_name='user',
            name='email',
            field=models.EmailField(blank=True, null=True, verbose_name='email address'),
        ),
        # Step 4: Rename phone_temp → phone, then make unique+not-null via RunSQL
        # (avoid AlterField's table rebuild which re-applies unique on partially set data)
        migrations.RenameField(model_name='user', old_name='phone_temp', new_name='phone'),
        migrations.RunSQL(
            # SQLite doesn't support ALTER COLUMN, so we rebuild the table via Django's mechanism
            # Instead, just create a unique index which is what unique=True does
            sql='CREATE UNIQUE INDEX accounts_user_phone_uniq ON accounts_user (phone)',
            reverse_sql='DROP INDEX IF EXISTS accounts_user_phone_uniq',
        ),
        # Step 5: Remove phone from Customer (moved to User)
        migrations.RemoveField(model_name='customer', name='phone'),
    ]
