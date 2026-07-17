#!/usr/bin/env bash
# Exit on error
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input

python manage.py migrate

# Create / update superuser (free-tier safe; no one-off jobs needed)
python manage.py shell -c "
from django.contrib.auth import get_user_model
U = get_user_model()
u, created = U.objects.get_or_create(
    username='floradmin',
    defaults={'email': 'floradmin@flora.com'},
)
u.set_password('flora@123')
u.is_staff = True
u.is_superuser = True
u.is_active = True
u.save()
print('SUPERUSER_OK created=' + str(created))
"
