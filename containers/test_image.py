"""Execute in the built, uninitialized image with --network none; no vault needed."""
import os
from pathlib import Path
from zipfile import ZipFile

assert os.getuid()==1000,'Application image must run as its unprivileged user'
for file in ('/app/.local-data/django.key','/app/.local-data/vault.key',
             '/app/.local-data/development-relay.key','/run/foliolet-secrets/postgres-password',
             '/app/django-service/db.sqlite3','/app/spring-boot-service/uploaded-documents',
             '/app/spring-boot-service/document-backups','/app/.git'):
    assert not Path(file).exists(),'Developer/runtime state was baked into the image'
with ZipFile('/app/service.jar') as jar:
    for file in ('BOOT-INF/classes/application.properties','BOOT-INF/classes/application.yaml'):
        assert file not in jar.namelist(),'Ignored host configuration entered the packaged application'
print('PASS: unprivileged image has no initialized vault, database, ignored host configuration or Git state.',flush=True)
