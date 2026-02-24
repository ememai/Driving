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
