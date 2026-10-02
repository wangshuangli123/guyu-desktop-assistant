"""Restore the exact reviewed npm lock; never runs downloaded code."""
from pathlib import Path
import gzip, hashlib, json, sys
ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / 'vendor/desktop-commander/package-lock.json'
EXPECTED = '150ea4382540f3233bab79ab770288c3c62e86dc94ebe518bfd7e2978027656b'
data = gzip.decompress(TARGET.with_suffix('.json.gz').read_bytes())
if len(data) > 1000000 or hashlib.sha256(data).hexdigest() != EXPECTED:
    raise SystemExit('Dependency lock integrity check failed.')
lock = json.loads(data)
if lock.get('lockfileVersion') != 3:
    raise SystemExit('Unexpected npm lock format.')
if TARGET.exists():
    if TARGET.read_bytes() != data:
        raise SystemExit('An existing different lock was found; review it instead of overwriting.')
else:
    with TARGET.open('xb') as stream:
        stream.write(data)
print('Exact dependency lock verified.')
