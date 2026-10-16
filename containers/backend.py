import os
from pathlib import Path

env = dict(os.environ)
env['SPRING_DATASOURCE_PASSWORD'] = Path('/run/foliolet-secrets/postgres-password').read_text().strip()
env['BLOCKCHAIN_PRIVATE_KEY'] = Path('/app/.local-data/development-relay.key').read_text().strip()
os.execvpe('java', ['java', '-Xmx768m', '-jar', '/app/service.jar',
                  '--spring.config.location=file:/app/containers/application.yaml'], env)
