import os
import base64
from email.mime.text import MIMEText

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request


SCOPES = ['https://www.googleapis.com/auth/gmail.modify']


# ---------------------------
# 🔐 AUTH
# ---------------------------
def get_gmail_service():
    creds = None

    if os.path.exists('token.json'):
        try:
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        except:
            creds = None

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())

    if not creds:
        print("🔐 First-time authorization required...")

        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json', SCOPES
        )

        creds = flow.run_local_server(
            port=8080,
            access_type='offline',
            prompt='consent'
        )

        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return build('gmail', 'v1', credentials=creds)


# ---------------------------
# 📩 GET UNREAD EMAILS
# ---------------------------
def get_unread_emails():
    service = get_gmail_service()

    results = service.users().messages().list(
        userId='me',
        q="is:unread newer_than:1d",
        maxResults=5
    ).execute()

    messages = results.get('messages', [])

    emails = []

    for msg_data in messages:
        msg = service.users().messages().get(
            userId='me',
            id=msg_data['id']
        ).execute()

        headers = msg['payload']['headers']

        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), "")
        sender = next((h['value'] for h in headers if h['name'] == 'From'), "")

        body = ""

        if 'parts' in msg['payload']:
            for part in msg['payload']['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body'].get('data')
                    if data:
                        body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                        break
        else:
            data = msg['payload']['body'].get('data')
            if data:
                body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')

        emails.append({
            "id": msg_data['id'],
            "subject": subject,
            "from": sender,
            "body": body[:3000]
        })

    return emails


# ---------------------------
# ✅ MARK AS READ
# ---------------------------
def mark_as_read(message_id):
    service = get_gmail_service()

    service.users().messages().modify(
        userId='me',
        id=message_id,
        body={'removeLabelIds': ['UNREAD']}
    ).execute()


# ---------------------------
# 📤 SEND / REPLY EMAIL
# ---------------------------
def send_reply(to_email, subject, body):
    service = get_gmail_service()

    message = MIMEText(body)
    message['to'] = to_email
    message['subject'] = "Re: " + subject

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

    service.users().messages().send(
        userId='me',
        body={'raw': raw}
    ).execute()

    return True