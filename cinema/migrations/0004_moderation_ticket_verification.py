import uuid
from django.db import migrations, models


def tokens(apps, schema_editor):
    Ticket = apps.get_model('cinema', 'Ticket')
    for ticket in Ticket.objects.using(schema_editor.connection.alias).all().iterator():
        ticket.verification_token = uuid.uuid4()
        ticket.save(using=schema_editor.connection.alias, update_fields=['verification_token'])


class Migration(migrations.Migration):
    dependencies = [('cinema', '0003_alter_booking_unique_together_and_more')]
    operations = [
        migrations.AddField(model_name='user', name='is_moderator', field=models.BooleanField(default=False, verbose_name='Модератор')),
        migrations.AddField(model_name='ticket', name='used_at', field=models.DateTimeField(null=True, blank=True, editable=False)),
        migrations.AddField(model_name='ticket', name='verification_token', field=models.UUIDField(null=True, editable=False)),
        migrations.RunPython(tokens, migrations.RunPython.noop),
        migrations.AlterField(model_name='ticket', name='verification_token', field=models.UUIDField(default=uuid.uuid4, unique=True, editable=False)),
    ]
