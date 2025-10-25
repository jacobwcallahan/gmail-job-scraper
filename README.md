# Gmail Job Application Scraper
This project is a simple Gmail automation tool for tracking your job applications. Feedback and contributions are welcome!

## Usage
The script connects to Gmail via IMAP, uses OpenAI to classify incoming messages, and extracts job-related information such as company and position.

Scrapes gmail for job application confirmations and logs them in a csv file.
CSV file is formatted as:

`date | company | position | status | email`

- date: Date of job application
- company: Company applied to
- position: position applied to
- status: status of job application. Options: [`applied`, `interviewing`, `accepted`, `declined`]
- email: email used to apply to the job

The project uses OpenAI to classify the emails and pull the necessary information out of it. If it goes over a response from a company it will add a new entry then remove the duplicate from the csv file. 

Duplicates are removed by the same company, position, and email. 

Entries are appended to a persistent CSV log. When follow-up responses (e.g., interview invitations or rejections) are detected, the old entry is replaced with the updated one.

# Setup
## Packages
Have python installed and install requirements.txt.

```bash
pip install -r requirements.txt
```

run the `main.py` file and it should begin to work. 

## Environment Variables
These are the variables that must be edited for the program to run properly.

### settings.config: 
settings-TEMPLATE.config shows the basic template of the required settings file.
Rename it to settings.config once the variables are properly set.

The following variables must be set:

- `last_date`: This is the last date to check for job applications. Updated after the program is run.

    Format: MM-DD-YYYY
  
    Example: `last_date=08-01-2025`

- `emails`: List of emails to scrape the inboxes of. Must be separated by commas with no quotes.
  
    Example: `emails=email1@gmail.com, email2@gmail.com`

- `job_csv_dir`: Path to the csv file where the job applications are stored.
  
    Example: `job_csv_dir=/path/to/csv/job_apps.csv`

### .env

The .env file contains api-keys and passwords used to run the program. .env.template shows how these should be formatted

The following variables must be set:

- `EMAIL_PASSWORDS`: These are 'App Passwords' produced by google for a specific Email. They are used with imap technology. They are four strings of length 4 separated by spaces. These must be separated by commas. They *must* be in the same order as the corresponding emails in the 'emails' variable in the config file.
  
    Example: `EMAIL_PASSWORDS="aaaa bbbb cccc dddd, eeee ffff gggg hhhh"`

- `OPENAI_API_KEY`: This is the api key given by OpenAI. This will be used to classify the emails.
  
    Example: `OPENAI_API_KEY="openai_secret_key_should_go_here"`

# Notes

Classification errors can occur if the email lacks clear company or position information.

Ensure IMAP access is enabled for each Gmail account.

Run time depends on inbox size; older accounts may take several minutes.
