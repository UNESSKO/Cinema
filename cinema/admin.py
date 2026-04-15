from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import User, Genre, Director, Movie, MovieGenre, Hall, Session, Booking, Ticket, Review, Promotion, \
    MoviePromotion


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'birth_date', 'is_staff')
    fieldsets = UserAdmin.fieldsets + (
        ('Дополнительная информация', {'fields': ('birth_date',)}),
    )


@admin.register(Director)
class DirectorAdmin(admin.ModelAdmin):
    list_display = ('name', 'birth_date', 'birth_place')
    search_fields = ('name',)


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'session', 'seat_row', 'seat_number', 'status', 'ticket_link', 'created_at')
    list_filter = ('status', 'session')
    search_fields = ('user__username',)
    list_editable = ('status',)

    def ticket_link(self, obj):
        if hasattr(obj, 'ticket'):
            return format_html('<a href="/admin/cinema/ticket/{}/change/">🎫 Билет #{}</a>', obj.ticket.id,
                               obj.ticket.id)
        return '—'

    ticket_link.short_description = 'Билет'

    actions = ['confirm_bookings']

    def confirm_bookings(self, request, queryset):
        for booking in queryset:
            booking.status = 'confirmed'
            booking.save()
        self.message_user(request, f'Подтверждено {queryset.count()} бронирований.')

    confirm_bookings.short_description = 'Подтвердить выбранные бронирования'


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('id', 'booking', 'qr_code', 'purchase_date')
    readonly_fields = ('qr_code', 'purchase_date')
    search_fields = ('qr_code', 'booking__user__username')


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('movie', 'user', 'rating', 'created_at')
    list_filter = ('rating', 'movie')


admin.site.register(Genre)
admin.site.register(Movie)
admin.site.register(MovieGenre)
admin.site.register(Hall)
admin.site.register(Session)
admin.site.register(Promotion)
admin.site.register(MoviePromotion)