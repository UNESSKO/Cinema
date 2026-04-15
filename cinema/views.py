from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Movie, Session, Hall, User, Director, Booking, Review, Ticket
from .forms import RegisterForm, MovieForm, SessionForm, HallForm, DirectorForm, ReviewForm, BookingForm
import json


def is_admin(user):
    return user.is_staff or user.is_superuser


def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('movie_list')
    else:
        form = RegisterForm()
    return render(request, 'cinema/register.html', {'form': form})


# ==================== ФИЛЬМЫ ====================

def movie_list(request):
    movies = Movie.objects.select_related('director').all()
    return render(request, 'cinema/movie_list.html', {'movies': movies})


def movie_detail(request, pk):
    movie = get_object_or_404(Movie, pk=pk)
    sessions = Session.objects.filter(movie=movie, start_time__gt=timezone.now())
    reviews = Review.objects.filter(movie=movie).select_related('user')
    user_review = None
    if request.user.is_authenticated:
        user_review = Review.objects.filter(movie=movie, user=request.user).first()
    return render(request, 'cinema/movie_detail.html', {
        'movie': movie,
        'sessions': sessions,
        'reviews': reviews,
        'user_review': user_review
    })


@login_required
@user_passes_test(is_admin)
def movie_create(request):
    if request.method == 'POST':
        form = MovieForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('movie_list')
    else:
        form = MovieForm()
    return render(request, 'cinema/movie_form.html', {'form': form, 'title': 'Добавить фильм'})


@login_required
@user_passes_test(is_admin)
def movie_edit(request, pk):
    movie = get_object_or_404(Movie, pk=pk)
    if request.method == 'POST':
        form = MovieForm(request.POST, request.FILES, instance=movie)
        if form.is_valid():
            form.save()
            return redirect('movie_detail', pk=movie.pk)
    else:
        form = MovieForm(instance=movie)
    return render(request, 'cinema/movie_form.html', {'form': form, 'title': 'Редактировать фильм'})


@login_required
@user_passes_test(is_admin)
def movie_delete(request, pk):
    movie = get_object_or_404(Movie, pk=pk)

    if request.method == 'POST':
        try:
            movie.delete()
            messages.success(request, f'Фильм "{movie.title}" успешно удалён.')
            return redirect('movie_list')
        except ValidationError as e:
            messages.error(request, str(e))
            return redirect('movie_detail', pk=movie.pk)

    can_delete = movie.sessions.count() == 0
    return render(request, 'cinema/confirm_delete.html', {
        'object': movie,
        'type_name': 'фильм',
        'cancel_url': 'movie_detail',
        'cancel_id': movie.pk,
        'can_delete': can_delete,
        'block_reason': f'У этого фильма есть {movie.sessions.count()} сеанс(ов). Сначала удалите все сеансы.' if not can_delete else None
    })


# ==================== ОТЗЫВЫ ====================

@login_required
def review_create(request, movie_pk):
    movie = get_object_or_404(Movie, pk=movie_pk)

    # Проверяем, есть ли уже отзыв от этого пользователя
    existing_review = Review.objects.filter(movie=movie, user=request.user).first()
    if existing_review:
        messages.error(request, 'Вы уже оставили отзыв на этот фильм. Вы можете отредактировать его ниже.')
        return redirect('movie_detail', pk=movie_pk)

    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.movie = movie
            review.user = request.user
            review.save()
            messages.success(request, 'Спасибо за ваш отзыв!')
            return redirect('movie_detail', pk=movie_pk)
    else:
        form = ReviewForm()

    return render(request, 'cinema/review_form.html', {'form': form, 'movie': movie, 'title': 'Оставить отзыв'})


@login_required
def review_edit(request, pk):
    review = get_object_or_404(Review, pk=pk)

    # Проверяем, что отзыв принадлежит текущему пользователю
    if review.user != request.user and not request.user.is_staff:
        messages.error(request, 'Вы можете редактировать только свои отзывы.')
        return redirect('movie_detail', pk=review.movie.pk)

    if request.method == 'POST':
        form = ReviewForm(request.POST, instance=review)
        if form.is_valid():
            form.save()
            messages.success(request, 'Отзыв обновлён!')
            return redirect('movie_detail', pk=review.movie.pk)
    else:
        form = ReviewForm(instance=review)

    return render(request, 'cinema/review_form.html',
                  {'form': form, 'movie': review.movie, 'title': 'Редактировать отзыв'})


@login_required
def review_delete(request, pk):
    review = get_object_or_404(Review, pk=pk)
    movie_pk = review.movie.pk

    if review.user != request.user and not request.user.is_staff:
        messages.error(request, 'Вы можете удалять только свои отзывы.')
        return redirect('movie_detail', pk=movie_pk)

    if request.method == 'POST':
        review.delete()
        messages.success(request, 'Отзыв удалён.')
        return redirect('movie_detail', pk=movie_pk)

    return render(request, 'cinema/confirm_delete.html', {
        'object': review,
        'type_name': 'отзыв',
        'cancel_url': 'movie_detail',
        'cancel_id': movie_pk,
        'can_delete': True
    })


# ==================== БРОНИРОВАНИЕ МЕСТ ====================

@login_required
def session_detail(request, pk):
    session = get_object_or_404(Session, pk=pk)

    # Получаем все бронирования
    confirmed_bookings = Booking.objects.filter(session=session, status='confirmed')
    pending_bookings = Booking.objects.filter(session=session, status='pending')

    # Для отображения занятых мест
    occupied_seats = [f"{b.seat_row}_{b.seat_number}" for b in confirmed_bookings]
    pending_seats = [f"{b.seat_row}_{b.seat_number}" for b in pending_bookings]

    seats_per_row = 15
    rows_count = session.hall.capacity // seats_per_row
    rows_range = list(range(1, rows_count + 1))
    seats_range = list(range(1, seats_per_row + 1))

    # ОТЛАДКА В КОНСОЛЬ
    print(f"\n=== session_detail ===")
    print(f"Session ID: {pk}")
    print(f"confirmed (красные): {occupied_seats}")
    print(f"pending (оранжевые): {pending_seats}")
    print(f"rows_range: {rows_range}")
    print(f"seats_range: {seats_range}")
    print(f"rows_count: {rows_count}, seats_per_row: {seats_per_row}")
    print("=====================\n")

    if request.method == 'POST':
        selected_seats_str = request.POST.get('selected_seats', '')

        if selected_seats_str:
            selected_seats = selected_seats_str.split(',')
            booked_count = 0
            errors = []

            for seat_key in selected_seats:
                try:
                    row, seat = seat_key.split('_')
                    row = int(row)
                    seat = int(seat)

                    # Проверяем, не заблокировано ли место
                    if seat_key in occupied_seats or seat_key in pending_seats:
                        errors.append(f"Место {row}-{seat} уже занято или ожидает подтверждения")
                        continue

                    # Создаём бронирование
                    booking = Booking.objects.create(
                        session=session,
                        user=request.user,
                        seat_row=row,
                        seat_number=seat,
                        status='pending'
                    )
                    booked_count += 1
                    pending_seats.append(seat_key)

                except (ValueError, IndexError):
                    errors.append(f"Некорректные данные места: {seat_key}")

            if booked_count > 0:
                messages.success(request,
                                 f'✅ {booked_count} место(а) забронировано! Ожидайте подтверждения администратора.')
            if errors:
                for error in errors:
                    messages.error(request, f'❌ {error}')

            if booked_count > 0:
                return redirect('my_bookings')
        else:
            messages.error(request, '❌ Не выбрано ни одного места')

    occupied_seats_json = json.dumps(occupied_seats)
    pending_seats_json = json.dumps(pending_seats)

    return render(request, 'cinema/session_detail.html', {
        'session': session,
        'occupied_seats': occupied_seats,
        'pending_seats': pending_seats,
        'occupied_seats_json': occupied_seats_json,
        'pending_seats_json': pending_seats_json,
        'hall': session.hall,
        'rows_range': rows_range,
        'seats_range': seats_range,
        'rows_count': rows_count,
        'seats_per_row': seats_per_row,
    })

@login_required
def ticket_detail(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)

    # Проверяем, что билет принадлежит текущему пользователю
    if ticket.booking.user != request.user and not request.user.is_staff:
        messages.error(request, 'У вас нет доступа к этому билету')
        return redirect('my_bookings')

    return render(request, 'cinema/ticket_detail.html', {'ticket': ticket})


@login_required
def my_bookings(request):
    # Получаем ВСЕ бронирования пользователя (включая pending)
    bookings = Booking.objects.filter(user=request.user).select_related('session', 'session__movie', 'session__hall')
    return render(request, 'cinema/my_bookings.html', {'bookings': bookings})


@login_required
def cancel_booking(request, pk):
    booking = get_object_or_404(Booking, pk=pk)

    if booking.user != request.user and not request.user.is_staff:
        messages.error(request, 'Вы можете отменять только свои бронирования.')
        return redirect('my_bookings')

    if request.method == 'POST':
        booking.status = 'cancelled'
        booking.save()
        messages.success(request, 'Бронирование отменено.')
        return redirect('my_bookings')

    return render(request, 'cinema/confirm_delete.html', {
        'object': booking,
        'type_name': 'бронирование',
        'cancel_url': 'my_bookings',
        'cancel_id': None,
        'can_delete': True
    })


# ==================== РЕЖИССЁРЫ ====================

def director_list(request):
    directors = Director.objects.all()
    return render(request, 'cinema/director_list.html', {'directors': directors})


def director_detail(request, pk):
    director = get_object_or_404(Director, pk=pk)
    movies = director.movies.all()
    return render(request, 'cinema/director_detail.html', {'director': director, 'movies': movies})


@login_required
@user_passes_test(is_admin)
def director_create(request):
    if request.method == 'POST':
        form = DirectorForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('director_list')
    else:
        form = DirectorForm()
    return render(request, 'cinema/director_form.html', {'form': form, 'title': 'Добавить режиссёра'})


@login_required
@user_passes_test(is_admin)
def director_edit(request, pk):
    director = get_object_or_404(Director, pk=pk)
    if request.method == 'POST':
        form = DirectorForm(request.POST, request.FILES, instance=director)
        if form.is_valid():
            form.save()
            return redirect('director_detail', pk=director.pk)
    else:
        form = DirectorForm(instance=director)
    return render(request, 'cinema/director_form.html', {'form': form, 'title': 'Редактировать режиссёра'})


@login_required
@user_passes_test(is_admin)
def director_delete(request, pk):
    director = get_object_or_404(Director, pk=pk)

    if request.method == 'POST':
        try:
            director.delete()
            messages.success(request, f'Режиссёр "{director.name}" успешно удалён.')
            return redirect('director_list')
        except ValidationError as e:
            messages.error(request, str(e))
            return redirect('director_detail', pk=director.pk)

    can_delete = director.movies.count() == 0
    return render(request, 'cinema/confirm_delete.html', {
        'object': director,
        'type_name': 'режиссёра',
        'cancel_url': 'director_detail',
        'cancel_id': director.pk,
        'can_delete': can_delete,
        'block_reason': f'У этого режиссёра есть {director.movies.count()} фильм(ов). Сначала удалите все фильмы режиссёра.' if not can_delete else None
    })


# ==================== СЕАНСЫ ====================

def session_list(request):
    sessions = Session.objects.select_related('movie', 'hall').filter(start_time__gt=timezone.now())
    return render(request, 'cinema/session_list.html', {'sessions': sessions})


@login_required
@user_passes_test(is_admin)
def session_create(request):
    if request.method == 'POST':
        form = SessionForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('session_list')
    else:
        form = SessionForm()
    return render(request, 'cinema/session_form.html', {'form': form, 'title': 'Добавить сеанс'})


@login_required
@user_passes_test(is_admin)
def session_edit(request, pk):
    session = get_object_or_404(Session, pk=pk)
    if request.method == 'POST':
        form = SessionForm(request.POST, instance=session)
        if form.is_valid():
            form.save()
            return redirect('session_list')
    else:
        form = SessionForm(instance=session)
    return render(request, 'cinema/session_form.html', {'form': form, 'title': 'Редактировать сеанс'})


@login_required
@user_passes_test(is_admin)
def session_delete(request, pk):
    session = get_object_or_404(Session, pk=pk)
    if request.method == 'POST':
        session.delete()
        return redirect('session_list')
    return render(request, 'cinema/confirm_delete.html', {
        'object': session,
        'type_name': 'сеанс',
        'cancel_url': 'session_list',
        'cancel_id': None,
        'can_delete': True
    })


# ==================== ЗАЛЫ ====================

def hall_list(request):
    halls = Hall.objects.all()
    return render(request, 'cinema/hall_list.html', {'halls': halls})


@login_required
@user_passes_test(is_admin)
def hall_create(request):
    if request.method == 'POST':
        form = HallForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('hall_list')
    else:
        form = HallForm()
    return render(request, 'cinema/hall_form.html', {'form': form, 'title': 'Добавить зал'})


@login_required
@user_passes_test(is_admin)
def hall_edit(request, pk):
    hall = get_object_or_404(Hall, pk=pk)
    if request.method == 'POST':
        form = HallForm(request.POST, instance=hall)
        if form.is_valid():
            form.save()
            return redirect('hall_list')
    else:
        form = HallForm(instance=hall)
    return render(request, 'cinema/hall_form.html', {'form': form, 'title': 'Редактировать зал'})


@login_required
@user_passes_test(is_admin)
def hall_delete(request, pk):
    hall = get_object_or_404(Hall, pk=pk)
    if request.method == 'POST':
        hall.delete()
        return redirect('hall_list')
    return render(request, 'cinema/confirm_delete.html', {
        'object': hall,
        'type_name': 'зал',
        'cancel_url': 'hall_list',
        'cancel_id': None,
        'can_delete': True
    })


# ==================== ПОЛЬЗОВАТЕЛИ ====================

@login_required
@user_passes_test(is_admin)
def user_list(request):
    users = User.objects.all()
    return render(request, 'cinema/user_list.html', {'users': users})