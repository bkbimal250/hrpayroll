# VPS Migration Fix for Shared Database

Since you're using the same database for both local machine and VPS server, here's the simple fix:

## Quick Fix Commands (Run on VPS):

```bash
# 1. Pull the latest changes
git pull origin main

# 2. Fake apply migrations up to 0007 (database already has tables)
python manage.py migrate core 0007 --fake

# 3. Apply only the new migration 0008 (adds gross_salary and net_salary fields)
python manage.py migrate core 0008

# 4. Check status
python manage.py showmigrations core

# 5. Start server
python manage.py runserver 8002
```

## What This Does:

1. **Fakes migrations 0001-0007**: Since your database already has the salary tables, we just mark these migrations as applied without actually running them.

2. **Applies migration 0008**: This adds the new `gross_salary` and `net_salary` fields to the existing salary table.

3. **No data loss**: Your existing salary data remains intact.

## Alternative One-Liner:

```bash
git pull origin main && python manage.py migrate core 0007 --fake && python manage.py migrate core 0008 && python manage.py runserver 8002
```

This should resolve the migration dependency error and get your VPS server running!
