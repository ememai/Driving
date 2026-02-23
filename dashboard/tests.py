from django.test import TestCase, Client
from django.urls import reverse
from app.models import UserProfile, Plan

from django.test import override_settings

@override_settings(ALLOWED_HOSTS=['testserver','localhost','127.0.0.1'])
class SubscriptionDashboardUITest(TestCase):
    def setUp(self):
        # create staff user
        self.staff = UserProfile.objects.create_user(
            phone_number='250780000000', email='admin@example.com', password='testpass',
            is_staff=True
        )
        # create regular user with email and phone
        self.user = UserProfile.objects.create_user(
            phone_number='250781111111', email='user@example.com', password='userpass',
            name='Test User'
        )
        # create a default plan; dashboard_add_subscription will also reference this
        Plan.objects.create(plan='Basic', price=1000)
        self.client = Client()
        # force login to ensure staff user is authenticated regardless of backend
        self.client.force_login(self.staff)

    def test_user_dropdown_rendering(self):
        url = reverse('admin_subscription_dashboard')
        response = self.client.get(url)
        # make sure request succeeded and capture body in case of failure
        self.assertEqual(response.status_code, 200, f"Unexpected status {response.status_code}: {response.content}")
        content = response.content.decode('utf-8')
        # the dropdown renders each user via their __str__ method, which currently
        # returns the email address (with an optional leading space). just check for
        # the email since that's what appears in the HTML.
        expected = self.user.email
        self.assertIn(expected, content)

    def test_update_shows_errors(self):
        # create a subscription to update using the plan created in setUp
        from app.models import Subscription
        plan = Plan.objects.first()
        sub = Subscription.objects.create(user=self.user, plan=plan)
        # post with invalid data (empty plan)
        url = reverse('subscription_update', args=[sub.id])
        response = self.client.post(url, {'plan': ''})
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        # should contain our generic message and field-level error
        self.assertIn('Please correct the errors below', content)
        self.assertIn('Plan: This field is required.', content)
    
    def test_update_handles_deleted_user(self):
        """Simulate an orphaned subscription by removing the user via raw SQL.

        MySQL enforces FK constraints, so the normal ORM delete would cascade and
        remove the subscription too.  We'll temporarily disable FK checks so the
        user row is gone but the subscription remains.
        """
        from app.models import Subscription
        plan = Plan.objects.first()
        sub = Subscription.objects.create(user=self.user, plan=plan)
        # delete the user row with foreign key checks off
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute('SET FOREIGN_KEY_CHECKS=0;')
            cursor.execute('DELETE FROM app_userprofile WHERE id=%s;', [self.user.id])
            cursor.execute('SET FOREIGN_KEY_CHECKS=1;')
        # now the subscription exists but its user_id points nowhere
        url = reverse('subscription_update', args=[sub.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn('unknown user', content)

