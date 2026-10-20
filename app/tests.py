from django.test import TestCase
from django.test import RequestFactory
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from app.views import custom_server_error
from app.admin import TrafficLogAdmin

from app.models import (
    UserProfile,
    Plan,
    Subscription,
    PaymentMethodSetting,
    ExamType,
    Exam,
    ScheduledExam,
    TrafficLog,
)
from app.utils import auto_schedule_recent_exams
from dashboard.forms import ScheduledExamForm



# Create your tests here.

class UnverifiedSubscriptionTests(TestCase):
    def setUp(self):
        self.user = UserProfile.objects.create_user(
            phone_number='250780000001',
            email='tester@example.com',
            password='password123',
        )
        self.plan = Plan.objects.create(plan='Basic', price=500)
        self.client.force_login(self.user)

    def test_payment_page_uses_payment_method_settings(self):
        PaymentMethodSetting.objects.update_or_create(
            pk=1,
            defaults={
                "momo_merchant_code": "123456",
                "airtel_payee_phone": "0722000000",
                "momo_payment_phone": "0788000000",
                "recipient_name": "Test Recipient",
            },
        )

        response = self.client.get(reverse('payment'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "*182*8*1*123456*")
        self.assertContains(response, "0788000000")
        self.assertContains(response, "*182*1*1*0722000000*")
        self.assertContains(response, "Test Recipient")

    def test_context_and_endpoint_return_true(self):
        # initially no unverified subscription
        response = self.client.get(reverse('home'))
        self.assertFalse(response.context.get('unverified_subscription'))

        # create subscription and generate OTP (unverified)
        sub = Subscription.objects.create(user=self.user, plan=self.plan)
        sub.generate_otp()
        sub.save()

        # context processor should include the unverified subscription
        response = self.client.get(reverse('home'))
        self.assertTrue(response.context.get('unverified_subscription'))

        content = response.content.decode('utf-8')
        # our modification adds an extra script block when the context var is present
        # count both single- and double-quoted variants, which appear in the
        # context-driven and fetch-driven scripts respectively.
        occurrences = (
            content.count("new bootstrap.Modal(document.getElementById('unverifiedModal')).show()")
            + content.count('new bootstrap.Modal(document.getElementById("unverifiedModal")).show()')
        )
        self.assertGreaterEqual(occurrences, 2)

        # endpoint should also report unverified = True
        resp2 = self.client.get(reverse('check_unverified'))
        self.assertEqual(resp2.status_code, 200)
        self.assertTrue(resp2.json().get('unverified'))

    def test_endpoint_returns_false_when_verified(self):
        # create subscription and mark otp_verified
        sub = Subscription.objects.create(user=self.user, plan=self.plan)
        sub.generate_otp()
        sub.otp_verified = True
        sub.save()

        resp = self.client.get(reverse('check_unverified'))
        self.assertEqual(resp.json().get('unverified'), False)

    def test_websocket_script_handles_reconnect(self):
        """Script embedded in base.html should implement reconnect/backoff logic."""
        response = self.client.get(reverse('home'))
        content = response.content.decode('utf-8')

        # isolate the websocket block to avoid unrelated reloads elsewhere
        if 'real-time websocket connection for unverified subscription events' in content:
            ws_block = content.split('real-time websocket connection for unverified subscription events')[1]
        else:
            self.fail('Websocket comment not found in template')

        # websocket section should not reload the page on close
        self.assertNotIn('location.reload()', ws_block)

        # verify expected reconnect/backoff code exists
        self.assertIn('reconnectAttempts', ws_block)
        self.assertIn('scheduleReconnect', ws_block)
        self.assertRegex(ws_block, r'Math\.pow\(2, reconnectAttempts')

        # ensure we re-check via fetch when socket opens
        self.assertIn('checkUnverifiedSubscription()', ws_block)
        # also verify checks on error/close
        self.assertRegex(ws_block, r'socket\.on(error|close)')

        # show modal only if element exists (safeguard added)
        self.assertIn("modal element not found", ws_block)

        # check function now respects document.readyState
        self.assertIn('document.readyState', content)


    def test_activation_click_prevents_repeat(self):
        """The embedded JS should set a flag when the modal button is clicked
        and skip future checks until the unverified subscription disappears."""
        response = self.client.get(reverse('home'))
        content = response.content.decode('utf-8')

        # flag variable and early‑return should be present
        self.assertIn('activatingSubscription', content)
        self.assertIn('if (isActivating()', content)

        # event listener for the button that writes the flag
        self.assertRegex(content, r"querySelector\('#unverifiedModal a\.btn'\)")
        self.assertIn("sessionStorage.setItem('activatingSubscription'", content)

    def test_skip_on_activation_page(self):
        """The script should bail out early when the current pathname matches
        the activation view URL."""
        response = self.client.get(reverse('home'))
        content = response.content.decode('utf-8')
        # guard code compares window.location.pathname against the django URL
        self.assertIn('window.location.pathname', content)
        self.assertIn(reverse('activate_subscription'), content)

    def test_modal_not_rendered_during_activation(self):
        """Even the initial-context script must not appear when visiting the
        activation page; user shouldn’t see the popup at all on that view."""
        # create a subscription so context processor returns unverified
        sub = Subscription.objects.create(user=self.user, plan=self.plan)
        sub.generate_otp()
        sub.save()

        response = self.client.get(reverse('activate_subscription'))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode('utf-8')
        # the one-line script that immediately shows the modal should be absent
        # there shouldn't be the tiny inline script that immediately pops
        # the unverifiedModal; match the exact structure to avoid hitting other
        # bootstrap usages (e.g. login OTP, global loader, etc.)
        self.assertNotRegex(
            html,
            r"<script>\s*document.addEventListener\('DOMContentLoaded', function\(\) \{\s*new bootstrap\.Modal\(document.getElementById\('unverifiedModal'\)\)\.show\(\);\s*\}\);\s*</script>"
        )

class ServerErrorPageTests(TestCase):
    def test_staff_can_view_full_error_description(self):
        staff_user = UserProfile.objects.create_user(
            phone_number='250780000002',
            email='staff@example.com',
            password='password123',
            is_staff=True,
        )
        request = RequestFactory().get('/admin/app/trafficlog/')
        request.user = staff_user

        try:
            raise ValueError(
                'Database returned an invalid datetime value. '
                'Are time zone definitions for your database installed?'
            )
        except ValueError:
            response = custom_server_error(request)

        content = response.content.decode('utf-8')
        self.assertContains(response, 'View Full Error Description', status_code=500)
        self.assertIn(
            'Database returned an invalid datetime value. '
            'Are time zone definitions for your database installed?',
            content,
        )
        self.assertIn('Request Method', content)
        self.assertIn('/admin/app/trafficlog/', content)

    def test_public_visitor_cannot_view_error_description(self):
        from django.contrib.auth.models import AnonymousUser

        request = RequestFactory().get('/error')
        request.user = AnonymousUser()

        try:
            raise RuntimeError('Sensitive test error description')
        except RuntimeError:
            response = custom_server_error(request)

        content = response.content.decode('utf-8')
        self.assertEqual(response.status_code, 500)
        self.assertNotIn('id="viewErrorDetailsBtn"', content)
        self.assertNotIn('Sensitive test error description', content)


class TrafficLogAdminTests(TestCase):
    def test_changelist_loads_without_date_hierarchy(self):
        admin_user = UserProfile.objects.create_superuser(
            phone_number='250780000003',
            email='traffic-admin@example.com',
            password='password123',
        )
        TrafficLog.objects.create(
            user=admin_user,
            path='/admin/app/trafficlog/',
            status_code=200,
        )
        self.client.force_login(admin_user)

        response = self.client.get(reverse('admin:app_trafficlog_changelist'))

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(TrafficLogAdmin.date_hierarchy)
        self.assertContains(response, '/admin/app/trafficlog/')


class ExamsByTypeTabsTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()

        # create a user and log in
        self.user = UserProfile.objects.create_user(
            phone_number='250780000002',
            email='examtester@example.com',
            password='password123',
        )
        self.client.force_login(self.user)

        # create an exam type
        self.exam_type = ExamType.objects.create(name='ExampleType')

    def _make_exam(self, year):
        # create an exam and then force its created_at year
        exam = Exam.objects.create(
            exam_type=self.exam_type,
            for_scheduling=False  # bypass scheduling exclusion
        )
        # manually update created_at to the start of the given year
        # use standard library timezone for UTC
        from datetime import datetime, timezone as dt_tz
        dt = datetime(year, 1, 1, tzinfo=dt_tz.utc)
        Exam.objects.filter(id=exam.id).update(created_at=dt)
        # reload from db to ensure attribute reflects change
        exam.refresh_from_db()
        return exam

    def test_exams_grouped_by_year_tabs(self):
        # create exams in different years
        e2023a = self._make_exam(2023)
        e2023b = self._make_exam(2023)
        e2024 = self._make_exam(2024)

        url = reverse('exams', args=[self.exam_type.name])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # context should contain grouped exams and correct years
        exams_by_year = response.context.get('exams_by_year')
        self.assertIsNotNone(exams_by_year)
        # keys should include 2024 and 2023 in order
        self.assertEqual(list(exams_by_year.keys()), [2024, 2023])
        self.assertCountEqual(exams_by_year[2023], [e2023a, e2023b])
        self.assertEqual(exams_by_year[2024], [e2024])

        content = response.content.decode('utf-8')
        # tabs should render year labels
        self.assertIn('id="tab-2024"', content)
        self.assertIn('id="tab-2023"', content)

        # each exam card should appear within its year's pane
        self.assertIn(f'id="year-2024"', content)
        self.assertIn(f'id="year-2023"', content)

    def test_server_side_filters_return_expected_exams(self):
        # create two exams in 2024, one in March one in April
        e_march = self._make_exam(2024)
        from datetime import datetime, timezone as dt_tz
        Exam.objects.filter(id=e_march.id).update(
            created_at=datetime(2024, 3, 1, tzinfo=dt_tz.utc)
        )
        e_april = self._make_exam(2024)
        Exam.objects.filter(id=e_april.id).update(
            created_at=datetime(2024, 4, 1, tzinfo=dt_tz.utc)
        )
        # mark march exam completed; bypass subscription check by making user staff
        self.user.is_staff = True
        self.user.save()
        from app.models import UserExam
        UserExam.objects.create(user=self.user, exam=e_march, completed_at=timezone.now())

        url = reverse('exams', args=[self.exam_type.name])
        resp = self.client.get(url + '?filter_year=2024&filter_month=3&filter_completed=1')
        self.assertEqual(resp.status_code, 200)

        exams_by_year = resp.context.get('exams_by_year')
        self.assertIsNotNone(exams_by_year)
        # filtered_count should reflect only one exam (the filtered result)
        self.assertEqual(resp.context.get('filtered_count'), 1)
        # all years should still be in keys and have all exams (no server-side removal)
        self.assertIn(2024, exams_by_year.keys())
        # 2024 should have both exams (unfiltered at server, JS handles filtering)
        self.assertEqual(len(exams_by_year[2024]), 2)
        # But only one should be the march completed exam in the filtered result
        march_exams = [e for e in exams_by_year[2024] if e.id == e_march.id]
        self.assertEqual(len(march_exams), 1)
        # HTML should show per-year count element (JS will update to filtered count of 1 after applying filters)
        self.assertIn('class="exam-count-display" data-year="2024">2</strong>', resp.content.decode('utf-8'))

    def test_server_side_filter_returns_only_noncompleted_exams(self):
        completed_exam = self._make_exam(2024)
        noncompleted_exam = self._make_exam(2024)
        self._make_exam(2023)
        self.user.is_staff = True
        self.user.save()
        from app.models import UserExam
        UserExam.objects.create(
            user=self.user,
            exam=completed_exam,
            completed_at=timezone.now(),
        )

        url = reverse('exams', args=[self.exam_type.name])
        response = self.client.get(
            url + '?filter_year=2024&filter_completed=not_completed'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context.get('filtered_count'), 1)
        self.assertContains(response, '<option value="not_completed">Ibyo utarakora gusa</option>')

    def test_server_side_filters_show_no_results_message(self):
        # create a single exam but request a filter that matches none
        exam = self._make_exam(2024)
        url = reverse('exams', args=[self.exam_type.name])
        # choose a month where no exam exists
        resp = self.client.get(url + '?filter_year=2024&filter_month=5')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context.get('filtered_count'), 0)
        html = resp.content.decode('utf-8')
        # the alert placeholder should be present (button removed)
        self.assertIn('no-results-info', html)
        self.assertIn('Nta bizamini bihuye n\'ibyatoranyijwe', html)
        self.assertNotIn('onclick="resetFilters', html)


class ExamTypesDirectoryTests(TestCase):
    def setUp(self):
        self.user = UserProfile.objects.create_user(
            phone_number='250780000003',
            email='types@example.com',
            password='password123',
        )
        self.client.force_login(self.user)

    def test_directory_lists_all_types_with_counts_and_category_links(self):
        populated_type = ExamType.objects.create(name='Ibimenyetso', order=1)
        empty_type = ExamType.objects.create(name='Amategeko', order=2)
        mixed_type = ExamType.objects.create(name='Ibivanze', order=3, mixed_type=True)
        Exam.objects.create(exam_type=populated_type, for_scheduling=False)
        Exam.objects.create(exam_type=mixed_type, for_scheduling=False)

        response = self.client.get(reverse('exam_types'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [exam_type.name for exam_type in response.context['exam_types']],
            ['Ibimenyetso', 'Amategeko', 'Ibivanze'],
        )
        self.assertEqual(
            [exam_type.exam_count for exam_type in response.context['exam_types']],
            [1, 0, 1],
        )
        self.assertEqual(response.context['exam_type_count'], 2)
        self.assertEqual(response.context['total_exam_count'], 1)

        html = response.content.decode('utf-8')
        self.assertIn(reverse('exams', args=[populated_type.name]), html)
        self.assertIn(reverse('exams', args=[empty_type.name]), html)
        self.assertIn(reverse('exams', args=[mixed_type.name]), html)
        self.assertIn('href="{}"'.format(reverse('exam_types')), html)

    def test_directory_requires_login(self):
        self.client.logout()

        response = self.client.get(reverse('exam_types'))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('register'), response.url)


class ScheduledExamGuardTests(TestCase):
    def setUp(self):
        self.staff = UserProfile.objects.create_user(
            phone_number='250780000010',
            email='staff@example.com',
            password='staffpass',
            is_staff=True,
        )
        self.exam_type = ExamType.objects.create(name='GuardTestType')
        self.scheduled_exam = Exam.objects.create(
            exam_type=self.exam_type,
            schedule_hour=timezone.now().time().replace(minute=0, second=0, microsecond=0),
            for_scheduling=True,
            is_active=False,
        )
        self.unscheduled_exam = Exam.objects.create(
            exam_type=self.exam_type,
            schedule_hour=timezone.now().time().replace(minute=0, second=0, microsecond=0),
            for_scheduling=True,
            is_active=False,
        )
        ScheduledExam.objects.create(
            exam=self.scheduled_exam,
            scheduled_datetime=timezone.now() + timedelta(days=1)
        )

    def test_scheduled_exam_form_rejects_previously_scheduled_exam(self):
        data = {
            'exam': self.scheduled_exam.id,
            'scheduled_datetime': (timezone.now() + timedelta(days=2)).strftime('%Y-%m-%dT%H:%M'),
        }
        form = ScheduledExamForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('exam', form.errors)
        self.assertEqual(form.errors['exam'], ['This exam is already scheduled.'])

    def test_auto_schedule_recent_exams_skips_already_scheduled_exams(self):
        count, message = auto_schedule_recent_exams()
        self.assertEqual(count, 1)
        self.assertIn('scheduled successfully', message)
