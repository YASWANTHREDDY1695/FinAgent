import os
import firebase_admin
from firebase_admin import credentials, firestore, auth
from dotenv import load_dotenv

load_dotenv()

# Initialize Firebase App
def init_firebase():
    if not firebase_admin._apps:
        cred_path = os.getenv("FIREBASE_CREDENTIALS", "serviceAccountKey.json")
        try:
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            print("Firebase initialized successfully.")
        except Exception as e:
            print(f"Failed to initialize Firebase: {e}")
            # If creds are missing in a dev environment, you might use application default credentials.
            # But here we explicitly depend on the Certificate for the admin SDK.

# Initialize right away when imported
init_firebase()

def get_firestore_client():
    return firestore.client()

def get_auth_client():
    return auth
