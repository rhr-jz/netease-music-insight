"""Internal container check; preserves the public Host validation."""
import json
import os
import urllib.request
from urllib.parse import urlsplit

origin = urlsplit(os.environ['MUSIC_INSIGHT_PUBLIC_URL'])
port = int(os.getenv('MUSIC_INSIGHT_PORT','8000'))
request = urllib.request.Request(f'http://127.0.0.1:{port}/health',headers={'Host':origin.netloc})
with urllib.request.urlopen(request,timeout=4) as response:
    data=json.load(response)
if data['status']!='ok' or data['netease_provider']!='ready' or data['qq_provider']!='ready':
    raise SystemExit(1)
