"""Ensure configured server secrets never occur in generated browser assets."""
import os
from pathlib import Path

values = [os.environ.get(key, '') for key in ('INTERNAL_API_TOKEN', 'SESSION_SIGNING_SECRET', 'OPENAI_API_KEY')]
for name in ('backend/.env', 'frontend/.env.local'):
    path = Path(name)
    if path.exists():
        for line in path.read_text().splitlines():
            key, _, value = line.partition('=')
            if key in ('INTERNAL_API_TOKEN', 'SESSION_SIGNING_SECRET', 'OPENAI_API_KEY'):
                values.append(value.strip().strip('\"\''))
files = list(Path('frontend/.next/static').rglob('*.js'))
if not files:
    raise SystemExit('Build the frontend before checking browser assets.')
for path in files:
    content = path.read_bytes()
    if any(value.encode() in content for value in values if len(value) >= 24):
        raise SystemExit(f'Server secret present in browser asset: {path}')
print(f'No configured server secrets found in {len(files)} browser JavaScript assets.')
