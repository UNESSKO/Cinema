from django.db import models
from django.contrib.auth.models import AbstractUser
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.utils import timezone

class User(AbstractUser):
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
            raise ValidationError(f'Нельзя удалить режиссёра "{self.name}", так как у него есть {self.movies.count()} фильм(ов). Сначала удалите все фильмы режиссёра.')
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
    director = models.ForeignKey(Director, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Режиссёр', related_name='movies')
    genres = models.ManyToManyField(Genre, through='MovieGenre', verbose_name='Жанры')

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('movie_detail', args=[self.pk])

    def delete(self, *args, **kwargs):
        if self.session_set.count() > 0:
            raise ValidationError(f'Нельзя удалить фильм "{self.title}", так как у него есть {self.session_set.count()} сеанс(ов). Сначала удалите все сеансы фильма.')
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
        """Возвращает количество рядов в зале (в одном ряду 20 мест)"""
        return self.capacity // 10

    def get_seats_per_row(self):
        """Возвращает количество мест в ряду (всегда 20)"""
        return 10

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
        booked = self.bookings.filter(status='confirmed').count()
        return self.hall.capacity - booked

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
    #expires_at = models.DateTimeField('Действительно до', null=True, blank=True)

    def __str__(self):
        return f'Бронь {self.id}: {self.user.username} - {self.session.movie.title} (ряд {self.seat_row}, место {self.seat_number})'

    # def save(self, *args, **kwargs):
    #     # Если бронь новая, устанавливаем время истечения (15 минут)
    #     if not self.pk and not self.expires_at:
    #         self.expires_at = timezone.now() + timezone.timedelta(minutes=15)
    #     super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Бронирование'
        verbose_name_plural = 'Бронирования'
        unique_together = ('session', 'seat_row', 'seat_number')


class Ticket(models.Model):
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, verbose_name='Бронирование', related_name='ticket')
    purchase_date = models.DateTimeField('Дата покупки', auto_now_add=True)
    qr_code = models.CharField('QR-код', max_length=255, blank=True, null=True)

    def __str__(self):
        return f'Билет {self.id}: {self.booking.user.username} - {self.booking.session.movie.title}'

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
        unique_together = ('movie', 'user')  # Один пользователь - один отзыв на фильм


class Promotion(models.Model):
    name = models.CharField('Название акции', max_length=200)
    description = models.TextField('Описание')
    discount_percent = models.IntegerField('Скидка %')
    start_date = models.DateField('Дата начала')
    end_date = models.DateField('Дата окончания')
    movies = models.ManyToManyField(Movie, through='MoviePromotion', verbose_name='Фильмы')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Акция'
        verbose_name_plural = 'Акции'


class MoviePromotion(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    promotion = models.ForeignKey(Promotion, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('movie', 'promotion')