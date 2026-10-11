from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APITestCase

from credentials.models import Chapter, EmployeeCredential, Session, StaffProfile

User = get_user_model()
PASSWORD = 'ValidPass123!'


def make_staff(email, role, chapter=None, is_active=True, name='Staff'):
    user = User.objects.create_user(
        username=email,
        email=email,
        password=PASSWORD,
        is_active=is_active,
        is_staff=role == StaffProfile.ROLE_SUPERADMIN,
        is_superuser=role == StaffProfile.ROLE_SUPERADMIN,
    )
    return StaffProfile.objects.create(
        user=user,
        name=name,
        role=role,
        chapter=chapter,
    )


class ChapterAccessTests(APITestCase):
    def setUp(self):
        self.chapter_a = Chapter.objects.create(name='Alpha')
        self.chapter_b = Chapter.objects.create(name='Beta')
        self.admin_a = make_staff(
            'alpha@example.com',
            StaffProfile.ROLE_CHAPTER_ADMIN,
            chapter=self.chapter_a,
            name='Alpha Admin',
        )
        self.superadmin = make_staff(
            'root@example.com',
            StaffProfile.ROLE_SUPERADMIN,
            name='Root',
        )
        cache.clear()
        now = timezone.now()
        self.session_a = Session.objects.create(
            chapter=self.chapter_a,
            title='Alpha session',
            starts_at=now,
            ends_at=now + timedelta(hours=1),
        )
        self.session_b = Session.objects.create(
            chapter=self.chapter_b,
            title='Beta session',
            starts_at=now,
            ends_at=now + timedelta(hours=1),
        )
        self.member_a = EmployeeCredential.objects.create(
            name='Ada',
            membership_id='A-1',
            email='ada@example.com',
            chapter=self.chapter_a,
        )
        self.member_b = EmployeeCredential.objects.create(
            name='Bea',
            membership_id='B-1',
            email='bea@example.com',
            chapter=self.chapter_b,
        )

    def login(self, email):
        response = self.client.post(
            '/api/auth/login/',
            {'email': email, 'password': PASSWORD},
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        return response

    def test_health_is_public(self):
        response = self.client.get('/api/health/')
        self.assertEqual(response.status_code, 200)

    def test_portal_requires_login(self):
        response = self.client.get('/api/credentials/')
        self.assertEqual(response.status_code, 401)

    def test_inactive_user_cannot_login(self):
        make_staff(
            'gone@example.com',
            StaffProfile.ROLE_CHAPTER_ADMIN,
            chapter=self.chapter_a,
            is_active=False,
        )
        response = self.client.post(
            '/api/auth/login/',
            {'email': 'gone@example.com', 'password': PASSWORD},
            format='json',
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data['detail'], 'This account has been disabled.')

        wrong_password = self.client.post(
            '/api/auth/login/',
            {'email': 'gone@example.com', 'password': 'not-the-password'},
            format='json',
        )
        self.assertEqual(wrong_password.status_code, 401)

    def test_login_returns_chapter_for_admin(self):
        response = self.login('alpha@example.com')
        self.assertEqual(response.data['user']['role'], 'chapter_admin')
        self.assertEqual(response.data['user']['chapter'], self.chapter_a.pk)

    def test_chapter_admin_sees_only_own_chapter_data(self):
        self.login('alpha@example.com')

        chapters = self.client.get('/api/chapters/')
        self.assertEqual(chapters.status_code, 200)
        self.assertEqual([row['id'] for row in chapters.data], [self.chapter_a.pk])

        members = self.client.get('/api/credentials/')
        self.assertEqual(members.status_code, 200)
        self.assertEqual([row['id'] for row in members.data], [self.member_a.pk])

        sessions = self.client.get('/api/sessions/')
        self.assertEqual([row['id'] for row in sessions.data], [self.session_a.pk])

        other_member = self.client.get(f'/api/credentials/{self.member_b.pk}/')
        self.assertEqual(other_member.status_code, 404)

        other_session = self.client.get(f'/api/sessions/{self.session_b.pk}/')
        self.assertEqual(other_session.status_code, 404)

        other_chapter = self.client.get(f'/api/chapters/{self.chapter_b.pk}/')
        self.assertEqual(other_chapter.status_code, 404)

    def test_chapter_admin_cannot_write_another_chapter(self):
        self.login('alpha@example.com')

        created = self.client.post(
            '/api/credentials/',
            {
                'name': 'New',
                'membership_id': 'A-2',
                'email': 'new@example.com',
                'chapter': self.chapter_b.pk,
            },
            format='json',
        )
        self.assertEqual(created.status_code, 201, created.content)
        self.assertEqual(created.data['chapter'], self.chapter_a.pk)

        visitor = self.client.post(
            f'/api/sessions/{self.session_b.pk}/visitor-substitute/create/',
            {
                'type': 'visitor',
                'name': 'Guest',
                'email': 'guest@example.com',
                'member_id': self.member_a.pk,
            },
            format='json',
        )
        self.assertEqual(visitor.status_code, 404)

        scan = self.client.post(
            '/api/credentials/scan/',
            {'credential': self.member_b.credential, 'session_id': self.session_b.pk},
            format='json',
        )
        self.assertEqual(scan.status_code, 404)

        payment = self.client.get(f'/api/chapters/{self.chapter_b.pk}/payment-report/')
        self.assertEqual(payment.status_code, 404)

        mark_paid = self.client.post(f'/api/credentials/{self.member_b.pk}/mark-paid/')
        self.assertEqual(mark_paid.status_code, 404)

        new_chapter = self.client.post('/api/chapters/', {'name': 'Gamma'}, format='json')
        self.assertEqual(new_chapter.status_code, 403)

    def test_superadmin_sees_every_chapter(self):
        self.login('root@example.com')
        chapters = self.client.get('/api/chapters/')
        self.assertEqual(
            {row['id'] for row in chapters.data},
            {self.chapter_a.pk, self.chapter_b.pk},
        )
        members = self.client.get('/api/credentials/')
        self.assertEqual(len(members.data), 2)

    def test_only_superadmin_can_create_chapter_admins(self):
        self.login('alpha@example.com')
        denied = self.client.post(
            '/api/staff/',
            {
                'name': 'Beta Admin',
                'email': 'beta@example.com',
                'password': PASSWORD,
                'chapter': self.chapter_b.pk,
            },
            format='json',
        )
        self.assertEqual(denied.status_code, 403)

        self.login('root@example.com')
        created = self.client.post(
            '/api/staff/',
            {
                'name': 'Beta Admin',
                'email': 'beta@example.com',
                'password': PASSWORD,
                'chapter': self.chapter_b.pk,
            },
            format='json',
        )
        self.assertEqual(created.status_code, 201, created.content)
        self.assertEqual(created.data['role'], 'chapter_admin')
        self.assertEqual(created.data['chapter'], self.chapter_b.pk)

        self.login('beta@example.com')
        members = self.client.get('/api/credentials/')
        self.assertEqual([row['id'] for row in members.data], [self.member_b.pk])
