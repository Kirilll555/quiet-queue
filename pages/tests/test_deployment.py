from unittest.mock import patch

from django.db import OperationalError
from django.contrib.auth import get_user_model
from django.test import TestCase
from pages.models import Institution, InstitutionRequest, QueueReport
from pages.services import submit_queue_report


class DeploymentTests(TestCase):
    def test_health_checks_database(self):
        response = self.client.get('/healthz/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok'})

    def test_health_returns_503_without_database(self):
        with patch('config.health.connection.cursor', side_effect=OperationalError):
            self.assertEqual(self.client.get('/healthz/').status_code, 503)

    def test_pages_render(self):
        for url in ['/', '/suggest/', '/ai-prediction/', '/accounts/login/', '/accounts/signup/']:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_rate_requires_login(self):
        response = self.client.get('/rate/')
        self.assertRedirects(response, '/accounts/login/?next=/rate/')

    def test_institution_is_visible_after_database_migrations(self):
        Institution.objects.create(name='Тестовая поликлиника', category='clinic')
        self.assertContains(self.client.get('/'), 'Тестовая поликлиника')

    def test_suggestion_is_persisted(self):
        response = self.client.post('/suggest/', {'name': 'Тестовое МФЦ', 'category': 'mfc'})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(InstitutionRequest.objects.filter(name='Тестовое МФЦ').exists())

    def test_queue_report_is_saved_and_repeat_is_blocked(self):
        user = get_user_model().objects.create_user(username='deployment-test', password='test-password')
        institution = Institution.objects.create(name='Тестовое МФЦ', category='mfc')
        report = dict(user=user, institution=institution, cabinet=None, queue_level='low')
        self.assertTrue(submit_queue_report(**report))
        self.assertFalse(submit_queue_report(**report))
        self.assertEqual(QueueReport.objects.count(), 1)
