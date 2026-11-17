from django.db import models, transaction
from decimal import Decimal
from django.contrib.auth.models import AbstractUser
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.utils import timezone
import uuid


class User(AbstractUser):
    is_moderator = models.BooleanField('Модератор', default=False)

    @property
    def can_moderate(self):
        return self.is_active and (self.is_moderator or self.is_staff or self.is_superuser)

    birth_date = models.DateField('Дата рождения', null=True, blank=True)

    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name='cinema_user_set',
        related_query_name='cinema_user',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='cinema_user_set',
        related_query_name='cinema_user',
    )

    def __str__(self):
        return self.username

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        swappable = 'AUTH_USER_MODEL'


class Genre(models.Model):
    name = models.CharField('Название', max_length=100)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Жанр'
        verbose_name_plural = 'Жанры'


class Director(models.Model):
    name = models.CharField('Имя', max_length=200)
    birth_date = models.DateField('Дата рождения', null=True, blank=True)
    birth_place = models.CharField('Место рождения', max_length=200, blank=True)
    biography = models.TextField('Биография', blank=True)
    photo = models.ImageField('Фото', upload_to='directors/', blank=True, null=True)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('director_detail', args=[self.pk])

    def delete(self, *args, **kwargs):
        if self.movies.count() > 0:
            raise ValidationError(
                f'Нельзя удалить режиссёра "{self.name}", так как у него есть {self.movies.count()} фильм(ов). Сначала удалите все фильмы режиссёра.')
        super().delete(*args, **kwargs)

    class Meta:
        verbose_name = 'Режиссёр'
        verbose_name_plural = 'Режиссёры'


class Movie(models.Model):
    title = models.CharField('Название', max_length=200)
    description = models.TextField('Описание')
    duration_min = models.IntegerField('Длительность (мин)')
    rating = models.FloatField('Рейтинг', default=0.0)
    poster = models.ImageField('Постер', upload_to='posters/', blank=True, null=True)
    release_year = models.IntegerField('Год выпуска')
    director = models.ForeignKey(Director, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Режиссёр',
                                 related_name='movies')
    genres = models.ManyToManyField(Genre, through='MovieGenre', verbose_name='Жанры')

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('movie_detail', args=[self.pk])

    def delete(self, *args, **kwargs):
        if self.sessions.count() > 0:
            raise ValidationError(
                f'Нельзя удалить фильм "{self.title}", так как у него есть {self.sessions.count()} сеанс(ов). Сначала удалите все сеансы фильма.')
        super().delete(*args, **kwargs)

    def average_rating(self):
        reviews = self.reviews.all()
        if reviews:
            return sum(r.rating for r in reviews) / reviews.count()
        return self.rating

    class Meta:
        verbose_name = 'Фильм'
        verbose_name_plural = 'Фильмы'


class MovieGenre(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    genre = models.ForeignKey(Genre, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('movie', 'genre')


class Hall(models.Model):
    number = models.IntegerField('Номер зала', unique=True)
    capacity = models.IntegerField('Вместимость')
    sound_system = models.CharField('Звуковая система', max_length=100)

    def __str__(self):
        return f'Зал {self.number}'

    def get_rows_count(self):
        return (self.capacity + 19) // 20

    def get_seats_per_row(self):
        return 20

    class Meta:
        verbose_name = 'Кинозал'
        verbose_name_plural = 'Кинозалы'


class Session(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, verbose_name='Фильм', related_name='sessions')
    hall = models.ForeignKey(Hall, on_delete=models.CASCADE, verbose_name='Зал', related_name='sessions')
    start_time = models.DateTimeField('Время начала')
    price = models.DecimalField('Цена', max_digits=8, decimal_places=2)

    def __str__(self):
        return f'{self.movie.title} - {self.start_time}'

    def get_absolute_url(self):
        return reverse('session_detail', args=[self.pk])

    def available_seats(self):
        # Учитываем и подтверждённые, и ожидающие бронирования
        occupied = self.bookings.filter(status__in=['confirmed', 'pending']).count()
        return self.hall.capacity - occupied

    def pending_bookings_count(self):
        return self.bookings.filter(status='pending').count()

    def get_active_promotion(self):
        """Возвращает активную акцию для фильма, если есть"""
        from django.utils import timezone
        today = timezone.now().date()
        promotions = self.movie.promotion_set.filter(
            is_active=True,
            start_date__lte=today,
            end_date__gte=today
        )
        return promotions.first() if promotions.exists() else None

    def get_discounted_price(self):
        """Возвращает цену со скидкой, если есть активная акция"""
        promotion = self.get_active_promotion()
        if promotion:
            discount = promotion.discount_percent
            return (self.price * (Decimal(100) - Decimal(discount)) / Decimal(100)).quantize(Decimal('0.01'))
        return self.price

    def delete(self, *args, **kwargs):
        # Отменяем все активные бронирования перед удалением
        bookings = self.bookings.filter(status__in=['pending', 'confirmed'])
        for booking in bookings:
            booking.status = 'cancelled'
            booking.save()
        super().delete(*args, **kwargs)

    class Meta:
        verbose_name = 'Сеанс'
        verbose_name_plural = 'Сеансы'


class Booking(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Ожидает подтверждения'),
        ('confirmed', 'Подтверждено'),
        ('cancelled', 'Отменено'),
    ]

    session = models.ForeignKey(Session, on_delete=models.CASCADE, verbose_name='Сеанс', related_name='bookings')
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Пользователь', related_name='bookings')
    seat_row = models.IntegerField('Ряд')
    seat_number = models.IntegerField('Место')
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField('Дата бронирования', auto_now_add=True)

    def __str__(self):
        return f'Бронь {self.id}: {self.user.username} - {self.session.movie.title} (ряд {self.seat_row}, место {self.seat_number}) - {self.get_status_display()}'

    price_at_booking = models.DecimalField(max_digits=8, decimal_places=2, null=True, editable=False)
    discount_applied = models.IntegerField(default=0, editable=False)

    def clean(self):
        super().clean()
        if self.session_id:
            capacity = self.session.hall.capacity
            if self.seat_row < 1 or not 1 <= self.seat_number <= 20 or (self.seat_row - 1) * 20 + self.seat_number > capacity:
                raise ValidationError('Несуществующее место в зале.')
            if self._state.adding and self.session.start_time <= timezone.now():
                raise ValidationError('Бронирование прошедшего сеанса невозможно.')

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if self._state.adding:
                self.clean()
                self.price_at_booking = self.session.get_discounted_price()
                promotion = self.session.get_active_promotion()
                self.discount_applied = promotion.discount_percent if promotion else 0
            super().save(*args, **kwargs)
            if self.status == 'confirmed':
                Ticket.objects.get_or_create(booking=self)

    class Meta:
        verbose_name = 'Бронирование'
        verbose_name_plural = 'Бронирования'
        constraints = [models.UniqueConstraint(
            fields=['session', 'seat_row', 'seat_number'],
            condition=models.Q(status__in=['pending', 'confirmed']),
            name='unique_active_booking_seat',
        )]


class Ticket(models.Model):
    verification_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    used_at = models.DateTimeField(null=True, blank=True, editable=False)

    @property
    def is_valid(self):
        return self.booking.status == "confirmed" and self.used_at is None

    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, verbose_name='Бронирование', related_name='ticket')
    qr_code = models.CharField('QR-код', max_length=255, blank=True, null=True)  # Пока оставляем nullable
    purchase_date = models.DateTimeField('Дата покупки', auto_now_add=True)

    def __str__(self):
        return f'Билет #{self.id}: {self.booking.user.username} - {self.booking.session.movie.title} ({self.booking.seat_row} ряд, {self.booking.seat_number} место)'

    def save(self, *args, **kwargs):
        if not self.qr_code:
            self.qr_code = str(uuid.uuid4())[:8].upper()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Билет'
        verbose_name_plural = 'Билеты'


class Review(models.Model):
    RATING_CHOICES = [(i, str(i)) for i in range(1, 6)]

    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, verbose_name='Фильм', related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Пользователь', related_name='reviews')
    rating = models.IntegerField('Оценка', choices=RATING_CHOICES)
    comment = models.TextField('Комментарий', max_length=1000)
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)

    def __str__(self):
        return f'Отзыв {self.user.username} на {self.movie.title}: {self.rating}/5'

    class Meta:
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'
        unique_together = ('movie', 'user')


class Promotion(models.Model):
    name = models.CharField('Название акции', max_length=200)
    description = models.TextField('Описание')
    discount_percent = models.IntegerField('Скидка %')
    start_date = models.DateField('Дата начала')
    end_date = models.DateField('Дата окончания')
    movies = models.ManyToManyField(Movie, through='MoviePromotion', verbose_name='Фильмы', blank=True)
    is_active = models.BooleanField('Активна', default=True)

    def __str__(self):
        return f'{self.name} (-{self.discount_percent}%)'

    def is_currently_active(self):
        """Проверяет, активна ли акция сейчас"""
        from django.utils import timezone
        today = timezone.now().date()
        return self.is_active and self.start_date <= today <= self.end_date

    class Meta:
        verbose_name = 'Акция'
        verbose_name_plural = 'Акции'


class MoviePromotion(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, verbose_name='Фильм')
    promotion = models.ForeignKey(Promotion, on_delete=models.CASCADE, verbose_name='Акция')

    class Meta:
        verbose_name = 'Акция фильма'
        verbose_name_plural = 'Акции фильмов'
        unique_together = ('movie', 'promotion')

