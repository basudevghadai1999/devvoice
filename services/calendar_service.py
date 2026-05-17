import os
from datetime import datetime, timedelta, timezone

CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), '..', 'credentials.json')
TOKEN_FILE       = os.path.join(os.path.dirname(__file__), '..', 'token.json')
SCOPES           = ['https://www.googleapis.com/auth/calendar']
IST              = timezone(timedelta(hours=5, minutes=30))


def is_configured() -> bool:
    return os.path.exists(CREDENTIALS_FILE)


def _get_service():
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as f:
            f.write(creds.to_json())
    return build('calendar', 'v3', credentials=creds)


def add_event(title: str, when_iso: str, duration_minutes: int = 60,
              description: str = "") -> str:
    service = _get_service()
    start = datetime.fromisoformat(when_iso).replace(tzinfo=IST)
    end   = start + timedelta(minutes=duration_minutes)
    body  = {
        'summary':     title,
        'description': description,
        'start': {'dateTime': start.isoformat(), 'timeZone': 'Asia/Kolkata'},
        'end':   {'dateTime': end.isoformat(),   'timeZone': 'Asia/Kolkata'},
        'reminders': {
            'useDefault': False,
            'overrides':  [{'method': 'popup', 'minutes': 10}],
        },
    }
    service.events().insert(calendarId='primary', body=body).execute()
    return f"Added to your calendar: {title} on {start.strftime('%B %d at %I:%M %p')}"


def list_events(timeframe: str = "today") -> str:
    service  = _get_service()
    now      = datetime.now(IST)

    if timeframe == "tomorrow":
        day_start = (now + timedelta(days=1)).replace(hour=0,  minute=0,  second=0,  microsecond=0)
        day_end   = (now + timedelta(days=1)).replace(hour=23, minute=59, second=59, microsecond=0)
    elif timeframe == "this week":
        day_start = now
        day_end   = now + timedelta(days=7)
    else:  # today
        day_start = now.replace(hour=0,  minute=0,  second=0,  microsecond=0)
        day_end   = now.replace(hour=23, minute=59, second=59, microsecond=0)

    result = service.events().list(
        calendarId   = 'primary',
        timeMin      = day_start.isoformat(),
        timeMax      = day_end.isoformat(),
        maxResults   = 10,
        singleEvents = True,
        orderBy      = 'startTime',
    ).execute()

    events = result.get('items', [])
    if not events:
        return f"No events {timeframe}."

    lines = []
    for ev in events:
        raw = ev['start'].get('dateTime', ev['start'].get('date', ''))
        try:
            dt = datetime.fromisoformat(raw)
            time_str = dt.strftime('%I:%M %p')
        except Exception:
            time_str = raw
        lines.append(f"{ev['summary']} at {time_str}")

    label = "today" if timeframe == "today" else timeframe
    return f"You have {len(lines)} event(s) {label}: " + ", ".join(lines)
