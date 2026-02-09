
import os
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'attendance_system.settings')
django.setup()

def check_db():
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES")
        tables = [row[0] for row in cursor.fetchall()]
        print("Tables in database:")
        for table in sorted(tables):
            print(f" - {table}")
        
        cursor.execute("SELECT app, name FROM django_migrations")
        migrations = cursor.fetchall()
        print("\nApplied migrations in django_migrations table:")
        for app, name in sorted(migrations):
            print(f" - {app}: {name}")

if __name__ == "__main__":
    check_db()
