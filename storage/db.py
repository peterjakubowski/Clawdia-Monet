# Clawdia Monet Database
#
# Author: Peter Jakubowski
# Date: 9/9/2025
# Description: Firestore database for Clawdia Monet
#
import logging

import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timezone
from config import settings

# Load environment variables
FIRESTORE_LOG_COLLECTION = settings.FIRESTORE_LOG_COLLECTION


# --- Configure DB ---
@st.cache_resource(show_spinner=False, ttl=3600)
def firebase_app(name: str):
    """Sets up the Firebase admin app"""

    try:
        # Check if the app is already initialized
        app = firebase_admin.get_app(name=name)
        return app
    except ValueError:
        pass
    try:
        if settings.GOOGLE_APPLICATION_CREDENTIALS not in ("Missing"):
            cred = credentials.Certificate(settings.GOOGLE_APPLICATION_CREDENTIALS)
        else:
            cred = credentials.ApplicationDefault()
        # Initialize firebase app
        app = firebase_admin.initialize_app(credential=cred, name=name)
        return app
    except ValueError as ve:
        logging.error("Value error")
        st.error(f"Value error: {ve}")
    except Exception:
        logging.error("An unexpected error occurred")
        st.error("An unexpected error occurred")

    return st.stop()


# Initialize firebase app
default_app = firebase_app(name='app')


# Create a new document in the db
def create_new_document(collection: str, data: dict) -> None:
    """Creates a new document in a collection in firestore db"""

    try:
        # Initialize db client
        db = firestore.client(app=default_app)
        # Create a reference to the Google post.
        doc_ref = db.collection(collection)
        # Then get the data at that reference.
        doc_ref.add(document_data=data)
    except ValueError:
        logging.warning("Value error")
        st.warning("Value error")
    except TypeError:
        logging.warning("Type error")
        st.warning("Type error")
    except Exception:
        logging.warning("An unknown error occurred creating new firestore document")
        st.warning("An unknown error occurred")

    return None


def submit_log(workflow_status: str):
    """"Submits user log to firestore db"""

    log_data = {
        "timestamp": datetime.now(timezone.utc),
        "locale": st.context.locale,
        "timezone": st.context.timezone,
        "artwork_image_url": st.session_state.get("artwork_image_url"),
        "workflow_status": workflow_status
    }

    create_new_document(collection=FIRESTORE_LOG_COLLECTION, data=log_data)

    return
