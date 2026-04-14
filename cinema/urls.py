from django.urls import path
from . import views

urlpatterns = [
    # Главная - фильмы
    path('', views.movie_list, name='movie_list'),
    path('register/', views.register, name='register'),

    # Фильмы
    path('movies/<int:pk>/', views.movie_detail, name='movie_detail'),
    path('movies/create/', views.movie_create, name='movie_create'),
    path('movies/<int:pk>/edit/', views.movie_edit, name='movie_edit'),
    path('movies/<int:pk>/delete/', views.movie_delete, name='movie_delete'),

    # Отзывы
    path('movies/<int:movie_pk>/review/create/', views.review_create, name='review_create'),
    path('review/<int:pk>/edit/', views.review_edit, name='review_edit'),
    path('review/<int:pk>/delete/', views.review_delete, name='review_delete'),

    # Режиссёры
    path('directors/', views.director_list, name='director_list'),
    path('directors/<int:pk>/', views.director_detail, name='director_detail'),
    path('directors/create/', views.director_create, name='director_create'),
    path('directors/<int:pk>/edit/', views.director_edit, name='director_edit'),
    path('directors/<int:pk>/delete/', views.director_delete, name='director_delete'),

    # Сеансы
    path('sessions/', views.session_list, name='session_list'),
    path('sessions/<int:pk>/', views.session_detail, name='session_detail'),
    path('sessions/create/', views.session_create, name='session_create'),
    path('sessions/<int:pk>/edit/', views.session_edit, name='session_edit'),
    path('sessions/<int:pk>/delete/', views.session_delete, name='session_delete'),

    # Бронирования
    path('my-bookings/', views.my_bookings, name='my_bookings'),
    path('booking/<int:pk>/cancel/', views.cancel_booking, name='cancel_booking'),

    # Залы
    path('halls/', views.hall_list, name='hall_list'),
    path('halls/create/', views.hall_create, name='hall_create'),
    path('halls/<int:pk>/edit/', views.hall_edit, name='hall_edit'),
    path('halls/<int:pk>/delete/', views.hall_delete, name='hall_delete'),

    # Пользователи
    path('users/', views.user_list, name='user_list'),
]