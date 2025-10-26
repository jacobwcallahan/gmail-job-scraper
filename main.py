import pandas as pd
from imaplib import IMAP4_SSL
from email import message_from_bytes
from email.utils import parsedate_to_datetime
from datetime import datetime
from dotenv import dotenv_values
from openai import OpenAI
from utils import update_value, get_email_data
import json
import sys
import time
from datetime import timezone
import configparser
import os
import yaml

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

config = configparser.ConfigParser()
config.read(os.path.join(BASE_DIR, "settings.config"))

# Get the last date and emails from the config file
last_date = datetime.strptime(config["general"]["last_date"], "%m-%d-%Y").astimezone(timezone.utc)

# Get the emails from the config file
emails = [e.strip() for e in config["general"]["emails"].split(",")]

# Get the job csv directory from the config file
job_csv = config["general"]["job_csv_dir"]

# Get the email passwords and openai api key from the env file
env = dotenv_values(os.path.join(BASE_DIR, ".env"))

# Get the email passwords and openai api key from the env file
# email passwords must be in the same order as the emails list
EMAIL_PASSWORDS = [e.strip() for e in env['EMAIL_PASSWORDS'].split(",")]
OPENAI_API_KEY = env["OPENAI_API_KEY"]

client = OpenAI(api_key=OPENAI_API_KEY)

def classify_subject(subject):
    """
    Classify the subject of the email as a job application confirmation or follow up email.
    """
    with open(os.path.join(BASE_DIR, "prompts.yaml"), "r") as f:
        data = yaml.safe_load(f)

    prompt = data["email_subject_classifier_prompt"]

    prompt = prompt.format(subject=subject)

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
            "is_job_application": True,
        }

    return result["is_job_application"]

def classify_email(subject, content, sender, date):
    """
    Classify an email as a job application confirmation or follow up email.
    
    Args:
        subject: The subject of the email.
        content: The content of the email.
        sender: The sender of the email.
        date: The date of the email.

    Returns:
        A dictionary with the following keys:
        - is_job_application: True if the email is a job application confirmation or follow up email, False otherwise.
        - company: The company name or 'None' if the email is not a job application confirmation or follow up email.
        - position: The position title or 'None' if the email is not a job application confirmation or follow up email.
        - status: The status of the application or 'None' if the email is not a job application confirmation or follow up email.
    """

    # Load the YAML file
    with open(os.path.join(BASE_DIR, "prompts.yaml"), "r") as f:
        data = yaml.safe_load(f)

    prompt = data["email_job_classifier_prompt"]

    prompt = prompt.format(subject=subject, content=content, sender=sender)

    response = client.chat.completions.create(
        model="gpt-4o",
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
    """
    Get the emails from the inbox.
    Args:
        email: The email address to get the emails from.
        password: The app password for the email address.

    Returns:
        A pandas DataFrame with the following columns:
        - date: The date of the email.
        - company: The company name.
        - position: The position title.
        - status: The status of the application.
    """
    imap = IMAP4_SSL("imap.gmail.com")
    imap.login(email, password)
    imap.select("inbox")
    status, messages = imap.search(None, 'ALL')
    ids = messages[0].split()

    entries = pd.DataFrame(columns=["date", "company", "position", "status"])
    count = 0
    total_emails = len(ids)
    print(f"Processing {total_emails} emails")

    # process the emails in reverse order (Most to least recent)
    ids = ids[::-1]
    for msg_id in ids:  
        print(f"Processing email: {count} of {total_emails}", end="\r") 
        count += 1
        time.sleep(.1)
        status, data = imap.fetch(msg_id, "(RFC822)")
        msg = message_from_bytes(data[0][1])
        date, subj, sender, content = get_email_data(msg)


        if date <= last_date:
            break

        if not classify_subject(subj):
            continue

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
    # get the old entries from the csv file
    try:
        old_entries = pd.read_csv(job_csv)
    except:
        print(f"No Previous CSV File Found, Creating New One")
        old_entries = pd.DataFrame(columns=["date", "company", "position", "status", "email"])

    for i in range(len(emails)):
        print(f"Processing email: {emails[i]}")
        # get the emails from the inbox
        entries = get_emails(emails[i], EMAIL_PASSWORDS[i])
        old_entries = pd.concat([old_entries, entries])
        sys.stdout.flush()
        print("\n")
    
    # drop duplicates
    old_entries = old_entries.drop_duplicates(subset=['company', 'position', "email"])
    # sort by date (oldest to newest)
    old_entries = old_entries.sort_values(by='date', ascending=True)
    # save the old entries to the csv file
    old_entries.to_csv(job_csv, index=False)

    # update the last date in the config file
    update_value(os.path.join(BASE_DIR, "settings.config"), "last_date", datetime.today().strftime("%m-%d-%Y"))

    # print success message
    print("Successfully processed emails and saved to csv file")