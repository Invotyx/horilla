from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import RequestFactory, TestCase
from django.urls import reverse

from error_logging.models import ErrorLog


class ErrorLogRecordTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = get_user_model().objects.create_user(
            username="tester", password="password"
        )

    def test_record_persists_request_context(self):
        request = self.factory.get("/example/path/?foo=bar")
        request.user = self.user

        ErrorLog.record(request=request, message="Boom", status_code=500)

        log = ErrorLog.objects.get()
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.path, "/example/path/")
        self.assertEqual(log.status_code, 500)
        self.assertFalse(log.resolved)


class ToggleErrorResolutionViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="resolver", password="password"
        )
        change_permission = Permission.objects.get(
            codename="change_errorlog", content_type__app_label="error_logging"
        )
        view_permission = Permission.objects.get(
            codename="view_errorlog", content_type__app_label="error_logging"
        )
        self.user.user_permissions.add(change_permission, view_permission)
        self.client.force_login(self.user)
        self.log = ErrorLog.objects.create(
            user=self.user,
            status_code=500,
            module="tests.view",
            path="/tests/",
            method="GET",
            message="Initial",
        )

    def test_toggle_to_resolved(self):
        response = self.client.post(
            reverse("error_logging:error-log-toggle", args=[self.log.pk]),
            data={"action": "resolve"},
            follow=True,
        )
        self.log.refresh_from_db()
        self.assertTrue(self.log.resolved)
        self.assertEqual(response.status_code, 200)

    def test_toggle_to_unresolved(self):
        self.log.mark_resolved(user=self.user)

        response = self.client.post(
            reverse("error_logging:error-log-toggle", args=[self.log.pk]),
            data={"action": "unresolve"},
            follow=True,
        )
        self.log.refresh_from_db()
        self.assertFalse(self.log.resolved)
        self.assertEqual(response.status_code, 200)
