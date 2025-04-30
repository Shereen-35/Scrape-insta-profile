import instaloader
import os

# Your IG login credentials
USERNAME = 'your_username_here'
PASSWORD = 'your_password_here'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SESSION_DIRECTORY = os.path.join(BASE_DIR, "session")
SESSION_FILE = os.path.join(SESSION_DIRECTORY, f"session-{USERNAME}")

# Ensure session directory exists
os.makedirs(SESSION_DIRECTORY, exist_ok=True)

# Setup Instaloader
L = instaloader.Instaloader()
L.context._session.headers['User-Agent'] = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
)

try:
    print(f"[INFO] Logging in as {USERNAME}...")
    L.login(USERNAME, PASSWORD)
    L.save_session_to_file(SESSION_FILE)
    print(f"[SUCCESS] Session saved to {SESSION_FILE}")
except instaloader.exceptions.BadCredentialsException:
    print("[ERROR] Invalid username or password.")
except instaloader.exceptions.TwoFactorAuthRequiredException:
    print("[ERROR] 2FA is enabled. This script does not yet support 2FA.")
except instaloader.exceptions.ConnectionException as e:
    print(f"[ERROR] Connection failed: {e}")
except Exception as e:
    print(f"[ERROR] Login failed: {e}")
