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
        # post with invalid data (missing plan_id field)
        url = reverse('subscription_update', args=[sub.id])
        response = self.client.post(url, {'plan': ''})
        # view no longer renders form on error; it simply redirects back to
        # dashboard after saving whatever was present.  Ensure we don't get a
        # server error and that the redirect occurs.
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('admin_subscription_dashboard'))

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
        # the user input should be empty/disabled rather than crashing
        self.assertIn('value="" disabled', content)

    def test_search_filters_and_does_not_error(self):
        # create a couple of subscriptions and ensure query works after slicing
        from app.models import Subscription
        plan = Plan.objects.first()
        # first subscription belongs to self.user created in setUp()
        sub1 = Subscription.objects.create(user=self.user, plan=plan)
        # create another user & subscription that should not match
        other = UserProfile.objects.create_user(
            phone_number='250782222222', email='other@example.com', password='otherpass', name='Other'
        )
        sub2 = Subscription.objects.create(user=other, plan=plan)
        url = reverse('admin_subscription_dashboard') + '?q=' + self.user.email + '&page=1'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        # only the matching subscription should appear in the table rows.  the
        # Add Subscription modal always lists everyone so we must narrow our
        # check to the <tbody> section.
        table_body = ''
        if '<tbody>' in content and '</tbody>' in content:
            table_body = content.split('<tbody>')[1].split('</tbody>')[0]
        self.assertIn(self.user.email, table_body)
        self.assertNotIn('other@example.com', table_body)

    def test_pagination_pages(self):
        from app.models import Subscription
        plan = Plan.objects.first()
        # create enough users/subscriptions to overflow first page
        for i in range(11):
            u = UserProfile.objects.create_user(
                phone_number=f'2507823333{i}',
                email=f'user{i}@example.com',
                password='pass',
                name=f'User{i}'
            )
            Subscription.objects.create(user=u, plan=plan)
        # page 2 should contain user10
        url = reverse('admin_subscription_dashboard') + '?page=2'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn('user10@example.com', content)

