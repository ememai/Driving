# Driving

## Payment method details

MoMo/Airtel payment codes, the MoMo phone number, and recipient name are managed in
Django admin under **Payment Method Settings**. These values are rendered on the
payment page and are visible to customers; they are configurable details, not
secrets. Run `python manage.py migrate` after deployment to create the settings
record with the current payment details as defaults.