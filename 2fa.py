import imaplib
import email
import re
import os
from dotenv import load_dotenv
from bs4 import BeautifulSoup  # pip install beautifulsoup4

def robust_decode(payload, charset):
    """Try to decode bytes payload with charset and common fallbacks."""
    for enc in [charset, 'utf-8', 'latin-1', 'windows-1252']:
        if not enc:
            continue
        try:
            return payload.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return payload.decode('utf-8', errors='replace')

def extract_body(email_message):
    """Extract and decode the email body, preferring plain text but falling back to HTML."""
    if email_message.is_multipart():
        for part in email_message.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))
            if "attachment" in content_disposition:
                continue
            payload = part.get_payload(decode=True)
            charset = part.get_content_charset()
            if content_type == "text/plain":
                return robust_decode(payload, charset)
            elif content_type == "text/html":
                html = robust_decode(payload, charset)
                return BeautifulSoup(html, "html.parser").get_text()
    else:
        payload = email_message.get_payload(decode=True)
        charset = email_message.get_content_charset()
        return robust_decode(payload, charset)
    return ""



def main():
        
    load_dotenv()
    GMAIL_USERNAME = os.getenv('GMAIL_USERNAME')
    GMAIL_APP_PASSWORD = os.getenv('GMAIL_APP_PASSWORD')
    IMAP_SERVER = 'imap.gmail.com'
    IMAP_PORT = 993

    mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
    mail.login(GMAIL_USERNAME, GMAIL_APP_PASSWORD)
    mail.select('inbox')

    status, messages = mail.search(None, '(FROM "no-reply@groceries.albertsons.com")')
    if status != 'OK' or not messages[0].strip():
        print("No emails found from that sender.")
        mail.logout()
        exit()

    latest_email_id = messages[0].split()[-1]
    status, msg_data = mail.fetch(latest_email_id, '(RFC822)')
    if status != 'OK':
        print("Failed to fetch email.")
        mail.logout()
        exit()

    raw_email = msg_data[0][1]
    email_message = email.message_from_bytes(raw_email)
    body = extract_body(email_message)

    match = re.search(r'Please enter the following code for verification: \b\d{4,8}\b', body)
    if match:
        code = match.group().split(':')[1].strip()
        code = int(code)
        print(f"Extracted code: {code}")
    else:
        print("No code found in the email.")

    mail.logout()
    if code:
        return code
