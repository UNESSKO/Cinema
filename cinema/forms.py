from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Movie, Session, Hall, Director, Review, Booking, Promotion


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    birth_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))

    class Meta:
        model = User
        fields = ['username', 'email', 'birth_date', 'password1', 'password2']


class DirectorForm(forms.ModelForm):
    class Meta:
        model = Director
        fields = ['name', 'birth_date', 'birth_place', 'biography', 'photo']
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date'}),
            'biography': forms.Textarea(attrs={'rows': 5}),
        }


class MovieForm(forms.ModelForm):
    class Meta:
        model = Movie
        fields = ['title', 'description', 'duration_min', 'rating', 'release_year', 'poster', 'director', 'genres']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'genres': forms.SelectMultiple(attrs={'size': 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'poster' in self.fields:
            self.fields['poster'].widget.attrs.update({'accept': 'image/*'})


class SessionForm(forms.ModelForm):
    class Meta:
        model = Session
        fields = ['movie', 'hall', 'start_time', 'price']
        widgets = {
            'start_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }


class HallForm(forms.ModelForm):
    class Meta:
        model = Hall
        fields = ['number', 'capacity', 'sound_system']


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'comment': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Поделитесь впечатлениями о фильме...'}),
        }


class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ['seat_row', 'seat_number']

    def __init__(self, *args, **kwargs):
        self.session = kwargs.pop('session', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        seat_row = cleaned_data.get('seat_row')
        seat_number = cleaned_data.get('seat_number')

        if self.session and seat_row and seat_number:
            # Проверяем, не забронировано ли уже место
            if Booking.objects.filter(session=self.session, seat_row=seat_row, seat_number=seat_number,
                                      status='confirmed').exists():
                raise forms.ValidationError('Это место уже забронировано или куплено!')

            # Проверяем, существует ли такой ряд и место в зале
            if seat_row < 1 or seat_row > 10:  # Максимум 10 рядов
                raise forms.ValidationError('Неверный номер ряда (1-10)')
            if seat_number < 1 or seat_number > 15:  # Максимум 15 мест в ряду
                raise forms.ValidationError('Неверный номер места (1-15)')

        return cleaned_data

class PromotionForm(forms.ModelForm):
    class Meta:
        model = Promotion
        fields = ['name', 'description', 'discount_percent', 'start_date', 'end_date', 'movies', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'movies': forms.SelectMultiple(attrs={'size': 5}),
        }