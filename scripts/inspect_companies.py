import os
import django
from collections import Counter

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'skilltraining.settings')
django.setup()

from accounts.models import Company

rows = list(Company.objects.values('id', 'name', 'domain'))
print('Total companies:', len(rows))

domains = [r['domain'] or '' for r in rows]
counts = Counter(domains)
print('Duplicate domains (count>1):', {k: v for k, v in counts.items() if v > 1})
print('\nAll companies:')
for r in rows:
    print(r)
