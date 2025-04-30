from s3 import app  # Correct import based on your file name

from waitress import serve

if __name__ == "__main__":
    serve(app, host="0.0.0.0", port=5000)
