from django.db import migrations
from django.db.models import Q


def add_image_column(apps, schema_editor):
    table_name = 'shop_offersale'
    conn = schema_editor.connection
    cursor = conn.cursor()

    if conn.vendor == 'sqlite':
        cursor.execute("PRAGMA table_info('%s')" % table_name)
        cols = [row[1] for row in cursor.fetchall()]
        if 'image' not in cols:
            cursor.execute("ALTER TABLE %s ADD COLUMN image varchar(255)" % table_name)
        return

    if conn.vendor == 'postgresql':
        cursor.execute(
            "SELECT to_regclass(%s)",
            [table_name],
        )
        table_exists = cursor.fetchone()[0] is not None
        if not table_exists:
            return

        cursor.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = %s",
            [table_name],
        )
        cols = {row[0] for row in cursor.fetchall()}
        if 'image' not in cols:
            cursor.execute("ALTER TABLE %s ADD COLUMN image varchar(255)" % table_name)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0004_offersale'),
    ]

    operations = [
        migrations.RunPython(add_image_column, noop),
    ]
