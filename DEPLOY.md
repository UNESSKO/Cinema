# Deployment

Local: `.venv/Scripts/python.exe manage.py runserver`.
Settings read .env. See .env.example. Keep secrets and backups private.
Vercel detects manage.py and WSGI and runs collectstatic automatically.
Use Python 3.14 and requirements.txt.
External PostgreSQL and Vercel Blob services have NOT been provisioned, as requested.
Set DJANGO_SECRET_KEY, DATABASE_URL (PostgreSQL with SSL), DJANGO_ALLOWED_HOSTS, DJANGO_CSRF_TRUSTED_ORIGINS, BLOB_READ_WRITE_TOKEN.
VERCEL=1 enables production; DJANGO_PRODUCTION=1 does the same outside Vercel.

To copy data into a NEW EMPTY external database, configure these variables locally and run:

    python manage.py migrate
    python manage.py loaddata backups/deploy-data.json
    python manage.py upload_media

Do not migrate or import during builds. Fixture contains password hashes: keep private. Upload preserves file paths and skips existing objects. Images have public URLs.
backups/before-deploy.sqlite3: original snapshot.
backups/deploy-clone.sqlite3: fresh schema populated from fixture; all 143 serialized objects verified identical, including hashes. Login sessions excluded intentionally.
Historical booking prices remain NULL because old code never persisted them. New bookings save price and discount.
