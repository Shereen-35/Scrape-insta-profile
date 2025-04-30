from flask import Flask, render_template, request
from instaloader import Instaloader, Profile, exceptions
import os
import random
import json
import gspread
from google.oauth2.service_account import Credentials
from urllib.parse import urlparse
from your_first_login_module import first_time_login  # Import the first-time login function

# --- Path Configuration ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
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

app = Flask(__name__, template_folder='.')

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

# --- First-Time Login (Refactored into Function) ---
def first_time_login(username, password):
    session_file = os.path.join(SESSION_DIRECTORY, f"session-{username}")
    L = Instaloader()
    L.context._session.headers['User-Agent'] = random.choice(USER_AGENTS)

    try:
        print(f"[INFO] Logging in as {username}...")
        L.login(username, password)
        L.save_session_to_file(session_file)
        print(f"[SUCCESS] Session saved to {session_file}")
        return True
    except exceptions.BadCredentialsException:
        print("[ERROR] Invalid username or password.")
        return False
    except exceptions.TwoFactorAuthRequiredException:
        print("[ERROR] 2FA is enabled. This script does not yet support 2FA.")
        return False
    except exceptions.ConnectionException as e:
        print(f"[ERROR] Connection failed: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Login failed: {e}")
        return False

# --- Login and Session Check ---
def load_or_login(username, password):
    session_file = os.path.join(SESSION_DIRECTORY, f"session-{username}")
    if not os.path.exists(session_file):
        # Call the function to login for the first time and save the session
        if not first_time_login(username, password):
            return False  # Return failure if login fails
    return True  # Return success if session is loaded or login is successful

# --- Routes ---
@app.route('/', methods=['GET'])
def index():
    return render_template('i2.html', scraped_data=None, message=None, error=None)

@app.route('/scrape', methods=['POST'])
def scrape_process():
    # Get username, password from your credentials (e.g., Google Sheets or predefined)
    credentials_list = get_credentials_from_sheet()
    if not credentials_list:
        return render_template('i2.html', error="Could not retrieve Instagram credentials.", scraped_data=None)

    username, password = credentials_list[current_account_index]

    # Attempt to login or load the session
    if not load_or_login(username, password):
        return render_template('i2.html', error="Login failed. Please check credentials.", scraped_data=None)

    # Proceed with scraping logic
    profile_url = request.form.get('profileUrl')
    if not profile_url:
        return render_template('i2.html', error="Please enter a profile URL.", scraped_data=None)

    data = scrape_profile_data(current_loader, profile_url, username)
    return render_template('i2.html', scraped_data=data)

if __name__ == '__main__':
    app.run(debug=True)

