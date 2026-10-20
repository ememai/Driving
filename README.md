# Driving

## Payment method details

MoMo/Airtel payment codes, the MoMo phone number, and recipient name are managed in
Django admin under **Payment Method Settings**. These values are rendered on the
payment page and are visible to customers; they are configurable details, not
secrets. Run `python manage.py migrate` after deployment to create the settings
record with the current payment details as defaults.

The WhatsApp recipient for automated admin notifications and the public support
phone number are managed under **Admin Notification Settings** in Django admin.
The migration initializes the notification number from `ADMIN_PHONE_NUMBER` and
the support number to the existing public number. Changes saved in admin take
effect immediately. The environment setting remains a fallback for notification
delivery if the database record cannot be read.