from django.test import TestCase
from django.urls import reverse
from app.models import UserProfile, Plan, Subscription



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

