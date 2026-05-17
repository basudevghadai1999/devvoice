"""
Run this once to authorize Dev to access your Google Calendar.
After it completes, token.json is saved and Dev will use it automatically.

Steps before running:
1. Go to https://console.cloud.google.com/
2. Create a project (or select existing)
3. Enable "Google Calendar API"
4. Go to APIs & Services → Credentials → Create Credentials → OAuth client ID
5. Application type: Desktop app
6. Download the JSON and save it as credentials.json in this folder
7. Then run:  python setup_google_calendar.py
"""

import os
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES           = ['https://www.googleapis.com/auth/calendar']
CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE       = 'token.json'

if not os.path.exists(CREDENTIALS_FILE):
    print("ERROR: credentials.json not found.")
    print(__doc__)
else:
    flow  = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
    creds = flow.run_local_server(port=0)
    with open(TOKEN_FILE, 'w') as f:
        f.write(creds.to_json())
    print(f"✓ Authorized. token.json saved. Dev can now access your Google Calendar.")
