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
