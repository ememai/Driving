# Driving

## Payment method details

MoMo/Airtel payment codes, the MoMo phone number, recipient name, admin notification WhatsApp number, and public
support phone number are managed together in the single **Site Settings** record
and admin page. Payment details are rendered on the
payment page and remain visible to customers; they are configurable details, not
secrets. Run `python manage.py migrate` after deployment. The migration preserves
existing payment details and initializes the admin notification number from
`ADMIN_PHONE_NUMBER`. That environment setting remains a fallback for notification
delivery if the database record cannot be read.