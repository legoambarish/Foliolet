"""Give an operator-invoked tunnel CLI the same generated app environment."""
import os
import runpy
from runtime import environment, ROOT

os.environ.update(environment(os.environ))
runpy.run_path(str(ROOT / 'tools/share-tunnel.py'), run_name='__main__')
