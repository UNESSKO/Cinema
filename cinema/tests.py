from datetime import timedelta
from decimal import Decimal
from django.test import TestCase
from django.db import IntegrityError, transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import User, Movie, Hall, Session, Booking, Ticket

class BookingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='test', password='testpass')
        self.movie = Movie.objects.create(title='Test', description='Test', duration_min=90, release_year=2026)
        self.hall = Hall.objects.create(number=1, capacity=21, sound_system='Test')
        self.session = Session.objects.create(movie=self.movie, hall=self.hall,
            start_time=timezone.now()+timedelta(days=1), price=Decimal('100.00'))

    def book(self, **kwargs):
        return Booking.objects.create(user=self.user, session=self.session, seat_row=1, seat_number=1, **kwargs)

    def test_cancelled_seat_can_be_booked_again(self):
        old = self.book()
        old.status = 'cancelled'
        old.save()
        self.book()
        self.assertEqual(Booking.objects.count(), 2)

    def test_active_duplicate_rejected(self):
        self.book()
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.book()

    def test_invalid_seat_and_past_session_rejected(self):
        with self.assertRaises(ValidationError):
            Booking.objects.create(user=self.user, session=self.session, seat_row=2, seat_number=2)
        self.session.start_time = timezone.now()-timedelta(days=1)
        self.session.save()
        with self.assertRaises(ValidationError):
            self.book()

    def test_price_and_ticket_persist(self):
        booking = self.book(status='confirmed')
        booking.refresh_from_db()
        self.assertEqual(booking.price_at_booking, Decimal('100.00'))
        booking.save()
        self.assertEqual(Ticket.objects.filter(booking=booking).count(), 1)


class BlobStorageTests(TestCase):
    def test_upload_keeps_database_path_and_public_access(self):
        from unittest.mock import patch
        from types import SimpleNamespace
        from django.core.files.base import ContentFile
        from .storage import VercelBlobStorage
        with patch('cinema.storage.blob.put_blob', return_value=SimpleNamespace(pathname='posters/test.jpg')) as put:
            name = VercelBlobStorage()._save('posters/test.jpg', ContentFile(b'image'))
        self.assertEqual(name, 'posters/test.jpg')
        self.assertEqual(put.call_args.kwargs['access'], 'public')
        self.assertFalse(put.call_args.kwargs['allow_overwrite'])

    def test_missing_object_is_not_a_network_error(self):
        from unittest.mock import patch
        from .storage import VercelBlobStorage
        from vercel.blob.errors import BlobNotFoundError
        with patch('cinema.storage.blob.head_blob', side_effect=BlobNotFoundError('missing')):
            self.assertFalse(VercelBlobStorage().exists('missing.jpg'))
        with patch('cinema.storage.blob.head_blob', side_effect=ConnectionError('offline')):
            with self.assertRaises(ConnectionError):
                VercelBlobStorage().exists('missing.jpg')


class ModerationTicketTests(BookingTests):
    def test_moderator_can_confirm_but_not_manage_users(self):
        self.user.is_moderator = True
        self.user.save()
        self.client.force_login(self.user)
        booking = self.book()
        self.assertEqual(self.client.post(f'/admin-panel/booking/{booking.pk}/confirm/').status_code, 302)
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'confirmed')
        self.assertEqual(self.client.get('/admin-panel/users/').status_code, 302)
        self.assertEqual(self.client.get('/movies/create/').status_code, 302)

    def test_cancelled_ticket_cannot_be_used(self):
        booking = self.book(status='confirmed')
        ticket = booking.ticket
        booking.status = 'cancelled'
        booking.save()
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(f'/ticket/{ticket.pk}/qr/').status_code, 410)
        self.user.is_moderator = True
        self.user.save()
        self.client.post(f'/ticket/verify/{ticket.verification_token}/')
        ticket.refresh_from_db()
        self.assertIsNone(ticket.used_at)

    def test_ticket_can_be_used_once_and_qr_is_png(self):
        ticket = self.book(status='confirmed').ticket
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(f'/ticket/{ticket.pk}/qr/')['Content-Type'], 'image/png')
        self.user.is_moderator = True
        self.user.save()
        url = f'/ticket/verify/{ticket.verification_token}/'
        self.client.post(url)
        ticket.refresh_from_db()
        used = ticket.used_at
        self.assertIsNotNone(used)
        self.client.post(url)
        ticket.refresh_from_db()
        self.assertEqual(ticket.used_at, used)

    def test_filters(self):
        self.assertContains(self.client.get('/?q=Test'), 'Test')
        self.assertNotContains(self.client.get('/?q=Other'), '>Test<')
        self.assertEqual(self.client.get('/?date=wrong').status_code, 200)
