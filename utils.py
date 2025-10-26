from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from bs4 import BeautifulSoup

def update_value(file_path, key, new_value):
    """
    Update a value in a config file.

    Args:
        file_path: The path to the config file.
        key: The key to update.
        new_value: The new value to set.
    """
    lines = []
    found = False

    with open(file_path, "r") as f:
        for line in f:
            if line.strip().startswith(f"{key}="):
                lines.append(f"{key}={new_value}\n")
                found = True
            else:
                lines.append(line)
    
    if not found:
        lines.append(f"{key}={new_value}\n")

    with open(file_path, "w") as f:
        f.writelines(lines)


def get_email_data(msg):
    """
    Extracts metadata and readable text (plain or HTML) from an email message.

    Args:
        msg: email.message.Message object
    """

    content = ""

    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            cdisp = str(part.get("Content-Disposition") or "").lower()

            if "attachment" in cdisp:
                continue

            payload = part.get_payload(decode=True)
            if not payload:
                continue

            charset = part.get_content_charset() or "utf-8"
            text = payload.decode(charset, errors="replace")

            if ctype == "text/plain":
                content += text
            elif ctype == "text/html" and not content:
                soup = BeautifulSoup(text, "html.parser")
                content = soup.get_text(separator="\n", strip=True)
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            text = payload.decode(charset, errors="replace")
            if msg.get_content_type() == "text/html":
                soup = BeautifulSoup(text, "html.parser")
                content = soup.get_text(separator="\n", strip=True)
            else:
                content = text

    date = datetime.fromtimestamp(parsedate_to_datetime(msg["Date"]).timestamp()).astimezone(timezone.utc)


    return date, msg["Subject"], msg["From"], content