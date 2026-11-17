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
        cleaned = super().clean()
        row, seat = cleaned.get('seat_row'), cleaned.get('seat_number')
        if self.session and row is not None and seat is not None:
            booking = Booking(session=self.session, seat_row=row, seat_number=seat)
            booking.clean()
            if Booking.objects.filter(session=self.session, seat_row=row, seat_number=seat,
                                      status__in=['pending', 'confirmed']).exists():
                raise forms.ValidationError('Это место уже занято.')
        return cleaned

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