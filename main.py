import pandas as pd
from imaplib import IMAP4_SSL
from email import message_from_bytes
from email.utils import parsedate_to_datetime
from datetime import datetime
from dotenv import dotenv_values
from openai import OpenAI
from utils import update_value
import json
import sys
import time
from datetime import timezone
import configparser

config = configparser.ConfigParser()
config.read("settings.config")

last_date = datetime.strptime(config["general"]["last_date"], "%m-%d-%Y").astimezone(timezone.utc)
emails = [e.strip() for e in config["general"]["emails"].split(",")]
job_csv = config["general"]["job_csv_dir"]


env = dotenv_values(".env")

EMAIL_PASSWORDS = [e.strip() for e in env['EMAIL_PASSWORDS'].split(",")]
OPENAI_API_KEY = env["OPENAI_API_KEY"]

client = OpenAI(api_key=OPENAI_API_KEY)

def classify_email(subject, content, sender, date):
    prompt = f"""
You are an email classifier. 
Determine if the email below is a confirmation or acknowledgement for a job application. 
If it seems like a job application confimation email, extract the company name, position title, and status of the application(it will be either "applied", "interviewing", "rejected", or "accepted").

If it's a follow up email, give the company name, position title, and the status of the application(it will be either "applied", "interviewing", "rejected", or "accepted").
Otherwise, return False for is_job_application.

Respond ONLY with a valid JSON object in the following format:

{{
  "is_job_application": true/false,
  "company": "Company name or 'None'",
  "position": "Position title or 'None'",
  "status": "Status of the application or 'None'"}}

Email:
Subject: {subject}
Sender: {sender}
Content: {content}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        messages=[
            {"role": "system", "content": "You are a precise JSON-only classifier with no commentary."},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"},
    )


    raw = response.choices[0].message.content.strip()

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        print(f"Error parsing JSON: {raw}")
        result = {
            "is_job_application": False,
            "company": None,
            "position": None,
            "status": None,
        }

    return result

def get_emails(email, password):
    imap = IMAP4_SSL("imap.gmail.com")
    imap.login(email, password)
    imap.select("inbox")
    status, messages = imap.search(None, 'ALL')
    ids = messages[0].split()

    entries = pd.DataFrame(columns=["date", "company", "position", "status"])
    count = 0
    total_emails = len(ids)
    print(f"Processing {total_emails} emails")
    ids = ids[::-1]
    for msg_id in ids:  # check recent 300 emails
        print(f"Processing email: {count} of {total_emails}", end="\r") 
        #sys.stdout.flush()
        count += 1
        time.sleep(.1)
        status, data = imap.fetch(msg_id, "(RFC822)")
        msg = message_from_bytes(data[0][1])
        subj = msg["Subject"] or ""
        sender = msg["From"] or ""
        date = parsedate_to_datetime(msg["Date"])
        content = msg.get_payload()

        if date <= last_date:
            break

        classification = classify_email(subj, content, sender, date)

        # if the email is a job application confirmation email, add it to the entries
        if classification["is_job_application"] and not (classification['company'] is None and classification['position'] is None):

            # if the status is not applied, we want to add it to the entries without dropping duplicates
            if classification['status'] == 'applied' or classification['status'] is None:
                entries = pd.concat([entries, pd.DataFrame([{
                    "date": date.strftime("%m-%d-%Y"),
                        "company": classification['company'],
                        "position": classification['position'],
                        "status": "applied",
                        "email": email,
                    }])], ignore_index=True)

            else:
                # if the status is not applied, we want to add it to the entries without dropping duplicates
                entries = entries.drop_duplicates(subset=['company', 'position'])
                entries = pd.concat([entries, pd.DataFrame([{
                    "date": date.strftime("%m-%d-%Y"),
                        "company": classification['company'],
                        "position": classification['position'],
                        "status": classification['status'],
                        "email": email,
                    }])], ignore_index=True)


    if entries.empty:
        return pd.DataFrame(columns=["date", "company", "position"])

    sorted_entries = entries.sort_values(by='date', ascending=False)
    imap.logout()
    return sorted_entries
        

if __name__ == "__main__":
    old_entries = pd.read_csv(job_csv)

    for i in range(len(emails)):
        entries = get_emails(emails[i], EMAIL_PASSWORDS[i])
        old_entries = pd.concat([old_entries, entries])
        sys.stdout.flush()
    
    old_entries = old_entries.drop_duplicates(subset=['company', 'position', "email"])
    old_entries = old_entries.sort_values(by='date', ascending=True)
    old_entries.to_csv(job_csv, index=False)

    update_value("settings.config", "last_date", datetime.today().strftime("%m-%d-%Y"))

    