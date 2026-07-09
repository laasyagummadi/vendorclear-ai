import sys
sys.path.insert(0, '/sessions/charming-vigilant-sagan/mnt/outputs/backend')

from main import app
from app.database import get_db
from app.models.base import Base

import types
g = dict(globals())
# Show what 'app' is at this point
print(f"\n=== PROBE: app is {type(g.get('app')).__name__} ===")
for k, v in sorted(g.items()):
    if not k.startswith('__') and isinstance(v, types.ModuleType):
        print(f"  {k} = module({v.__name__})")
