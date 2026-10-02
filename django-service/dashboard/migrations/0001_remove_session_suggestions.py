from django.db import migrations
from django.contrib.sessions.backends.db import SessionStore


def purge_suggestions(apps, schema_editor):
    Session = apps.get_model('sessions', 'Session')
    codec = SessionStore()
    # Includes expired rows: signing/compression never made old values confidential.
    for row in Session.objects.using(schema_editor.connection.alias).all().iterator():
        data = codec.decode(row.session_data)
        if 'claim_suggestions' in data:
            del data['claim_suggestions']
            row.session_data = codec.encode(data)
            row.save(update_fields=['session_data'], using=schema_editor.connection.alias)


class Migration(migrations.Migration):
    dependencies = [('sessions', '0001_initial')]
    operations = [migrations.RunPython(purge_suggestions, migrations.RunPython.noop)]
