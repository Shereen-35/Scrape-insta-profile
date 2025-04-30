# Instagram Profile Scraper 

This Flask application scrapes basic profile information from public Instagram profiles, utilizing multiple accounts to mitigate rate limiting. This README outlines considerations and steps for deploying this application in a production environment.


## 🔧 Features

- ✅ Scrapes follower, following, post count from profile URLs
- 🔄 Rotates Instagram accounts from Google Sheets after `n` uses
- 📂 Reuses session files for faster logins and lower detection risk
- 🕵️‍♂️ Custom user-agents and delays to mimic human-like behavior
- 🌐 Production-ready structure using `Waitress` and `PyInstaller` support
- ✅ Handles invalid profiles and login errors gracefully

---

## 🗂️ Project Structure

```
E:\instaloader\
│
.
├── s3.py
├── wsgi.py
├── requirements.txt
├── README.md
├── .gitignore
├── session/
│   └── .gitkeep
├── templates/
│   └── i2.html

```

---

## 🚀 Quick Start (Development)

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/insta-fake-detector.git
cd insta-fake-detector
```

### 2. Create and activate a virtual environment
```bash
python -m venv insta_venv
insta_venv\Scripts\activate  # For Windows
```

### 3. Install required packages
```bash
pip install -r requirements.txt
```

### 4. Run the Flask app
```bash
python s3.py
```

Visit [http://127.0.0.1:5000](http://127.0.0.1:5000) to access the app.

---

## 🏭 Production Deployment (Waitress)

### 1. Ensure `wsgi.py` exists:
```python
from waitress import serve
from s3 import app

if __name__ == "__main__":
    serve(app, host="0.0.0.0", port=5000)
```

### 2. Run in production:
```bash
python wsgi.py
```

---

## 📦 Building Executable with PyInstaller

```bash
pyinstaller --onefile s3.py
dist\s3.exe  # Output file for distribution
```

> Note: Make sure `session/` and `insta-scrape-prof-url-*.json` are included with the `.exe` for it to function properly.

---

## 📄 Creating `requirements.txt`

If you haven't already:

```bash
pip freeze > requirements.txt
```

---

## 📝 Notes

- Update `CREDENTIALS_FILE` and Google Sheet key/worksheet in `s3.py`.
- Your Google Sheet must have Instagram usernames and passwords in the first two columns.
- Only public profiles can be scraped unless the account has access to the private one.

---

## 🛡️ License

MIT License

---

## 🙋‍♂️ Author

Developed by [A.shereen](https://github.com/Shereen-35/)
