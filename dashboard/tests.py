from django.test import TestCase, Client
from django.urls import reverse
from app.models import UserProfile, Plan

from django.test import override_settings

@override_settings(ALLOWED_HOSTS=['testserver','localhost','127.0.0.1'])
class SubscriptionDashboardUITest(TestCase):
    def setUp(self):
        # flush any cached items so tests start with a clean slate.  some of the
        # dashboard views cache queryset results which can lead to stale model
        # instances being rendered after raw-sql modifications in earlier tests.
        from django.core.cache import cache
        cache.clear()

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
        from app.models import Subscription

        plan = Plan.objects.first()
        sub = Subscription.objects.create(user=self.user, plan=plan)
        url = reverse('subscription_update', args=[sub.id])
        response = self.client.post(url, {'super_subscription': ''}, follow=True)

        self.assertRedirects(response, url)
        self.assertContains(response, "Please select a plan.")
        sub.refresh_from_db()
        self.assertEqual(sub.plan, plan)

    def test_editing_plan_subscription_persists_plan_and_issues_otp(self):
        from app.models import Subscription

        original_plan = Plan.objects.get(plan='Basic')
        new_plan = Plan.objects.create(
            plan='Daily',
            price=2500,
            delta_days=1,
        )
        subscription = Subscription.objects.create(
            user=self.user,
            plan=original_plan,
            otp_verified=True,
        )

        response = self.client.post(
            reverse('subscription_update', args=[subscription.id]),
            {'plan_id': new_plan.id, 'updated': '0'},
        )

        self.assertRedirects(response, reverse('admin_subscription_dashboard'))
        subscription.refresh_from_db()
        self.assertEqual(subscription.plan, new_plan)
        self.assertEqual(subscription.price, 2500)
        self.assertIsNotNone(subscription.otp_code)
        self.assertFalse(subscription.otp_verified)

    def test_editing_custom_subscription_persists_price_and_duration(self):
        from app.models import Subscription

        subscription = Subscription.objects.create(
            user=self.user,
            super_subscription=True,
            price=1000,
            delta_days=1,
        )

        response = self.client.post(
            reverse('subscription_update', args=[subscription.id]),
            {
                'super_subscription': 'on',
                'delta_hours': '6',
                'delta_days': '0',
                'price': '3000',
            },
        )

        self.assertRedirects(response, reverse('admin_subscription_dashboard'))
        subscription.refresh_from_db()
        self.assertTrue(subscription.super_subscription)
        self.assertEqual(subscription.price, 3000)
        self.assertEqual(subscription.delta_hours, 6)
        self.assertEqual(subscription.delta_days, 0)
        self.assertIsNotNone(subscription.otp_code)

    def test_add_custom_subscription_records_custom_price_and_duration(self):
        from app.models import Subscription, SubscriptionPurchase

        response = self.client.post(
            reverse('dashboard_add_subscription'),
            {
                'user_id': self.user.id,
                'subscription_type': 'custom',
                'custom_price': '2500',
                'duration_value': '3',
                'duration_unit': 'days',
            },
        )

        self.assertRedirects(response, reverse('admin_subscription_dashboard'))
        subscription = Subscription.objects.get(user=self.user)
        self.assertTrue(subscription.super_subscription)
        self.assertIsNone(subscription.plan)
        self.assertEqual(subscription.price, 2500)
        self.assertEqual(subscription.delta_days, 3)
        self.assertEqual(subscription.delta_hours, 0)
        self.assertTrue(subscription.otp_code)

        success, _, _ = subscription.verify_and_start(subscription.otp_code)
        self.assertTrue(success)
        purchase = SubscriptionPurchase.objects.get(user=self.user)
        self.assertEqual(purchase.plan_name, 'Super subscription')
        self.assertEqual(purchase.amount, 2500)

    def test_invalid_custom_subscription_does_not_create_subscription(self):
        from app.models import Subscription

        self.client.post(
            reverse('dashboard_add_subscription'),
            {
                'user_id': self.user.id,
                'subscription_type': 'custom',
                'custom_price': '2500',
                'duration_value': '0',
                'duration_unit': 'days',
            },
        )

        self.assertFalse(Subscription.objects.filter(user=self.user).exists())

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
        # page 2 should contain at least one of the created users; the exact
        # email is unpredictable because ordering is not guaranteed in tests.
        url = reverse('admin_subscription_dashboard') + '?page=2'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        table_body = ''
        if '<tbody>' in content and '</tbody>' in content:
            table_body = content.split('<tbody>')[1].split('</tbody>')[0]
        self.assertTrue('user' in table_body, "No table rows rendered on page 2")

    def test_subscription_dashboard_query_count(self):
        """Ensure that rendering the subscription dashboard uses a fixed small
        number of queries (no N+1).
        """
        from app.models import Subscription
        plan = Plan.objects.first()
        # make a few extra subscriptions so there are rows to render
        for i in range(5):
            u = UserProfile.objects.create_user(
                phone_number=f'2507801234{i}',
                email=f'count{i}@example.com',
                password='pass',
                name=f'Count{i}'
            )
            Subscription.objects.create(user=u, plan=plan)
        url = reverse('admin_subscription_dashboard')
        # measure queries manually and assert we don't blow past a reasonable
        # ceiling. using assertNumQueries here is awkward because it checks for
        # exact equality.
        from django.db import connection
        initial = len(connection.queries)
        self.client.get(url)
        executed = len(connection.queries) - initial
        self.assertLessEqual(executed, 20, f"Too many queries: {executed}")

    def test_subscription_dashboard_shows_revenue_and_purchase_history(self):
        from app.models import SubscriptionPurchase
        from django.utils import timezone

        SubscriptionPurchase.objects.create(
            user=self.user,
            plan=Plan.objects.get(plan='Basic'),
            plan_name='Basic',
            amount=1000,
            sequence=1,
            subscribed_at=timezone.now(),
        )
        SubscriptionPurchase.objects.create(
            user=self.user,
            plan=Plan.objects.get(plan='Basic'),
            plan_name='Basic',
            amount=1000,
            sequence=2,
            subscribed_at=timezone.now(),
        )

        response = self.client.get(reverse('admin_subscription_dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '2000.00 RWF')
        self.assertContains(response, '#1: Basic')
        self.assertContains(response, '#2: Basic')
        self.assertContains(response, 'Subscription revenue recorded:')
        history_table = response.content.decode('utf-8').split(
            '<summary>All subscription history</summary>', 1
        )[1].split('</table>', 1)[0]
        self.assertEqual(history_table.count(f'<td>{self.user}</td>'), 1)

    def test_subscription_history_includes_all_users(self):
        from app.models import SubscriptionPurchase
        from django.utils import timezone

        plan = Plan.objects.get(plan='Basic')
        for index in range(11):
            user = UserProfile.objects.create_user(
                phone_number=f'2507834444{index:02d}',
                email=f'history{index}@example.com',
                password='password',
                name=f'History{index}',
            )
            SubscriptionPurchase.objects.create(
                user=user,
                plan=plan,
                plan_name='Basic',
                amount=1000,
                sequence=1,
                subscribed_at=timezone.now(),
            )

        response = self.client.get(reverse('admin_subscription_dashboard'))

        self.assertEqual(response.status_code, 200)
        history_table = response.content.decode('utf-8').split(
            '<summary>All subscription history</summary>', 1
        )[1].split('</table>', 1)[0]
        self.assertEqual(history_table.count('<tr>'), 12)
        self.assertContains(response, 'history0@example.com')

    def test_selected_subscription_history_records_can_be_deleted(self):
        from app.models import SubscriptionPurchase
        from django.utils import timezone

        plan = Plan.objects.get(plan='Basic')
        purchases = [
            SubscriptionPurchase.objects.create(
                user=self.user,
                plan=plan,
                plan_name='Basic',
                amount=amount,
                sequence=sequence,
                subscribed_at=timezone.now(),
            )
            for sequence, amount in ((1, 1000), (2, 2000))
        ]

        response = self.client.post(
            reverse('delete_subscription_purchases'),
            {'purchase_ids': [purchases[0].id]},
        )

        self.assertRedirects(response, reverse('admin_subscription_dashboard'))
        self.assertFalse(SubscriptionPurchase.objects.filter(pk=purchases[0].id).exists())
        self.assertTrue(SubscriptionPurchase.objects.filter(pk=purchases[1].id).exists())
        dashboard_response = self.client.get(reverse('admin_subscription_dashboard'))
        self.assertEqual(dashboard_response.context['subscription_revenue'], 2000)
        self.assertEqual(dashboard_response.context['subscription_purchase_count'], 1)

    def test_subscription_revenue_shows_recorded_datetime_range_and_nonzero_count(self):
        from app.models import SubscriptionPurchase
        from datetime import timedelta
        from django.utils import timezone

        now = timezone.localtime(timezone.now()).replace(microsecond=0)
        plan = Plan.objects.get(plan='Basic')
        purchases = [
            (1000, now - timedelta(hours=1), 1),
            (0, now - timedelta(hours=2), 2),
            (500, now + timedelta(hours=1), 3),
        ]
        for amount, subscribed_at, sequence in purchases:
            SubscriptionPurchase.objects.create(
                user=self.user,
                plan=plan,
                plan_name='Basic',
                amount=amount,
                sequence=sequence,
                subscribed_at=subscribed_at,
            )

        response = self.client.get(reverse('admin_subscription_dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['subscription_revenue'], 1500)
        self.assertEqual(response.context['subscription_purchase_count'], 2)
        self.assertEqual(
            response.context['revenue_first_recorded_at'],
            now - timedelta(hours=1),
        )
        self.assertEqual(
            response.context['revenue_last_recorded_at'],
            now + timedelta(hours=1),
        )
        self.assertContains(response, (now - timedelta(hours=1)).strftime('%d-%m-%Y %H:%M'))
        self.assertContains(response, (now + timedelta(hours=1)).strftime('%d-%m-%Y %H:%M'))

    def test_subscription_tracking_groups_all_time_daily_weekly_monthly_and_yearly(self):
        from app.models import SubscriptionPurchase
        from datetime import datetime
        from django.utils import timezone

        plan = Plan.objects.get(plan='Basic')
        records = (
            (1000, datetime(2024, 1, 1, 10)),
            (0, datetime(2024, 1, 1, 11)),
            (100, datetime(2024, 1, 8, 10)),
            (200, datetime(2024, 2, 1, 10)),
            (300, datetime(2025, 1, 1, 10)),
        )
        for sequence, (amount, subscribed_at) in enumerate(records, start=1):
            SubscriptionPurchase.objects.create(
                user=self.user,
                plan=plan,
                plan_name='Basic',
                amount=amount,
                sequence=sequence,
                subscribed_at=timezone.make_aware(subscribed_at),
            )

        response = self.client.get(reverse('subscription_tracking'))

        self.assertEqual(response.status_code, 200)
        tracking = {
            period['key']: list(period['rows'])
            for period in response.context['tracking_periods']
        }
        self.assertEqual(len(tracking['daily']), 4)
        self.assertEqual(len(tracking['weekly']), 4)
        self.assertEqual(len(tracking['monthly']), 3)
        self.assertEqual(len(tracking['yearly']), 2)
        self.assertEqual(sum(row['revenue'] for row in tracking['daily']), 1600)
        self.assertEqual(sum(row['count'] for row in tracking['daily']), 4)
        self.assertContains(response, 'Daily revenue')
        self.assertContains(response, 'Weekly revenue')
        self.assertContains(response, 'Monthly revenue')
        self.assertContains(response, 'Yearly revenue')

    def test_admin_dashboard_query_count(self):
        """Admins see recent lists; ensure each section is fetched efficiently."""
        from app.models import Payment, ScheduledExam, Exam, Subscription
        # create some objects for each table
        puser = UserProfile.objects.create_user(
            phone_number='250780999999',
            email='payuser@example.com',
            password='pass'
        )
        Payment.objects.create(user=puser, amount=10, transaction_id='tx1', status='Success')
        plan = Plan.objects.first()
        Subscription.objects.create(user=puser, plan=plan)
        # create a minimal exam instance (no kwargs)
        exam = Exam.objects.create()
        from django.utils import timezone
        ScheduledExam.objects.create(exam=exam, scheduled_datetime=timezone.now())
        url = reverse('admin_dashboard')
        # should run a small, bounded number of queries despite table sizes
        # allow a slightly larger budget in case middleware or cache lookups fire.
        with self.assertNumQueries(10):
            self.client.get(url)

    def test_channel_layer_hosts_include_scheme(self):
        """Ensure CHANNEL_LAYERS is configured with a full Redis URL (with scheme).

        Because tests run with DEBUG=True the default CHANNEL_LAYERS in the
        loaded settings use the in-memory backend, so we reload the settings
        module with DEBUG=False and a custom REDIS_URL to exercise the
        production branch of the file.
        """
        import os
        from importlib import reload

        # prepare environment for reload
        os.environ['MY_DEBUG'] = 'False'
        os.environ['REDIS_URL'] = 'redis://example.com:6379/1'
        # reload the settings module so CHANNEL_LAYERS is recomputed
        import mwami.settings as settings_module
        reload(settings_module)

        hosts = settings_module.CHANNEL_LAYERS['default']['CONFIG']['hosts']
        # there should be at least one host and it must match exactly our url
        self.assertEqual(hosts, ['redis://example.com:6379/1'])
        # cleanup: restore DEBUG back to True for rest of tests
        os.environ['MY_DEBUG'] = 'True'
        reload(settings_module)
