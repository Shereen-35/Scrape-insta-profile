from flask import Flask, request, render_template
from instaloader import Instaloader, Profile, exceptions
from urllib.parse import urlparse
import gspread
from google.oauth2.service_account import Credentials
import time
import random
import json
import os

# --- Path Configuration ---
BASE_DIR = os.path.dirname(os.path.abspath(_file_))
SESSION_DIRECTORY = os.path.join(BASE_DIR, "session")
SESSION_FILE_PREFIX = "session-"  # Instaloader's session file naming convention

# Ensure the session directory exists
if not os.path.exists(SESSION_DIRECTORY):
    os.makedirs(SESSION_DIRECTORY)

# --- Google Sheets Setup ---
scope = ['https://www.googleapis.com/auth/spreadsheets.readonly']
json_str = os.environ.get("GOOGLE_CREDENTIALS_JSON")
if json_str is None:
    raise Exception("GOOGLE_CREDENTIALS_JSON environment variable not set")
creds_info = json.loads(json_str)
creds = Credentials.from_service_account_info(creds_info, scopes=scope)
gc = gspread.authorize(creds)

app = Flask(_name_, template_folder='.')

SPREADSHEET_NAME = 'My Instagram Data'
CREDENTIALS_WORKSHEET = 'Account Credentials'
USERNAME_COL = 0
PASSWORD_COL = 1

# --- Constants ---
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:95.0) Gecko/20100101 Firefox/95.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:95.0) Gecko/20100101 Firefox/95.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15",
]

MAX_LOGIN_RETRIES = 3
urls_to_scrape = []
urls_processed_with_current_account = 0
urls_per_account_limit = 22
current_account_index = 0
scraping_in_progress = False
current_loader = None
current_username = None
scraped_data_queue = []

# --- Helpers ---
def get_credentials_from_sheet():
    try:
        spreadsheet = gc.open_by_key('1pEmMrAw_PuevwYNWLwUPANz_MdV9PZODKUkuIwGR7Jg')
        worksheet = spreadsheet.worksheet(CREDENTIALS_WORKSHEET)
        credentials_list = worksheet.get_all_values()
        print(f"[DEBUG] Retrieved credentials: {credentials_list}")
        return credentials_list[0:]
    except Exception as e:
        print(f"[ERROR] Failed to retrieve credentials: {e}")
        return None

def get_username_from_url(profile_url):
    parsed_url = urlparse(profile_url)
    segments = parsed_url.path.strip('/').split('/')
    return segments[0] if segments else None

def scrape_profile_data(loader, profile_url, username):
    try:
        username_to_scrape = get_username_from_url(profile_url)
        if not username_to_scrape:
            return {"account": username, "error": "Invalid Profile URL"}

        profile = Profile.from_username(loader.context, username_to_scrape)
        return {
            "username": profile.username,
            "followers": profile.followers,
            "following": profile.followees,
            "total_posts": profile.mediacount,
            "private": profile.is_private,
        }
    except exceptions.ProfileNotExistsException:
        return {"error": f"Profile '{username_to_scrape}' not found"}
    except Exception as e:
        return {"error": str(e)}

def attempt_login(loader, username, password):
    session_file = os.path.join(SESSION_DIRECTORY, f"{SESSION_FILE_PREFIX}{username}")
    try:
        print(f"[DEBUG] Checking for session file at: {session_file}")
        if os.path.exists(session_file):
            loader.load_session_from_file(username, session_file)
            print(f"[DEBUG] Loaded session for {username}")
            return True
        else:
            print(f"[DEBUG] No session found. Logging in fresh for {username}")
            loader.login(username, password)
            loader.save_session_to_file(session_file)
            print(f"[DEBUG] Logged in and saved session to: {session_file}")
            return True
    except exceptions.LoginRequiredException:
        print(f"[WARN] Login required for {username}, checkpoint might be required.")
        return False
    except Exception as e:
        print(f"[ERROR] Login failed for {username}: {e}")
        return False

def logout_account(username):
    session_file = os.path.join(SESSION_DIRECTORY, f"{SESSION_FILE_PREFIX}{username}")
    try:
        if os.path.exists(session_file):
            os.remove(session_file)
            print(f"[INFO] Removed session file for {username}")
        else:
            print(f"[DEBUG] No session file exists for {username}")
    except Exception as e:
        print(f"[ERROR] Error removing session for {username}: {e}")

# --- Routes ---
@app.route('/', methods=['GET'])
def index():
    return render_template('i2.html', scraped_data=None, message=None, error=None)

@app.route('/scrape', methods=['POST'])
def scrape_process():
    global current_account_index, scraping_in_progress, urls_to_scrape, urls_processed_with_current_account
    global current_loader, current_username, scraped_data_queue

    profile_url = request.form.get('profileUrl')
    if not profile_url:
        return render_template('i2.html', error="Please enter a profile URL.", scraped_data=None)

    urls_to_scrape.append(profile_url)
    credentials_list = get_credentials_from_sheet()
    if not credentials_list:
        return render_template('i2.html', error="Could not retrieve Instagram credentials.", scraped_data=None)

    if current_account_index < len(credentials_list):
        username, password = credentials_list[current_account_index]

        if not scraping_in_progress or current_username != username:
            scraping_in_progress = True
            current_username = username
            current_loader = Instaloader()
            current_loader.context._session.headers['User-Agent'] = random.choice(USER_AGENTS)
            current_loader.max_connection_attempts = 3

            logged_in = attempt_login(current_loader, username, password)
            if not logged_in:
                logout_account(username)
                current_account_index += 1
                scraping_in_progress = False
                return render_template('i2.html', error=f"Login failed for {username}, trying next account.")

        if urls_processed_with_current_account < urls_per_account_limit and urls_to_scrape:
            url_to_process = urls_to_scrape.pop(0)
            data = scrape_profile_data(current_loader, url_to_process, username)
            urls_processed_with_current_account += 1
            return render_template('i2.html', scraped_data=data)

        if urls_processed_with_current_account >= urls_per_account_limit or not urls_to_scrape:
            logout_account(username)
            current_account_index += 1
            urls_processed_with_current_account = 0
            scraping_in_progress = False
            return render_template('i2.html', message=f"Switched account from {username}.")

    else:
        # All accounts exhausted
        current_account_index = 0
        urls_processed_with_current_account = 0
        scraping_in_progress = False
        current_loader = None
        current_username = None
        return render_template('i2.html', message="All accounts used for current batch.")

if _name_ == '_main_':
    app.run(debug=True)

