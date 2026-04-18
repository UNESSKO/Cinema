#!/bin/bash

# Устанавливаем зависимости
pip install -r requirements.txt

# Выполняем миграции
python manage.py makemigrations
python manage.py migrate

# Собираем статические файлы
python manage.py collectstatic --noinput

# Запускаем сервер
gunicorn cinema_project.wsgi:application