# Clawdia Monet Cloud Storage
#
# Author: Peter Jakubowski
# Date: 9/9/2025
# Description: Google Cloud Storage for Clawdia Monet
#
# First, you need to install the Google Cloud Storage client library:
# pip install google-cloud-storage Pillow numpy


import io
from google.cloud import storage
from google.cloud.exceptions import GoogleCloudError
from config import settings
from PIL import Image
import logging


def upload_pil_image_to_gcs_and_get_url(
        image_pil: Image.Image,
        bucket_name: str,
        destination_blob_name: str,
        project_id: str = None,
        image_format: str = 'PNG',
        content_type: str = 'image/png'
) -> str:
    """
    Uploads an in-memory PIL Image to a Google Cloud Storage bucket
    and makes it publicly accessible.

    Args:
        image_pil: The image data as a Pillow Image object.
        bucket_name: The name of your GCS bucket.
        destination_blob_name: The desired filename for the image in the bucket.
        project_id: Your Google Cloud project ID.
        image_format: The format to save the PIL image in (e.g., 'PNG', 'JPEG').
        content_type: The content type of the image for the GCS blob.

    Returns:
        The public URL of the uploaded image.

    Raises:
        StorageError: If there is an error during the upload process.
    """
    # --- 1. Save the PIL Image to an in-memory byte stream ---
    try:
        in_mem_file = io.BytesIO()
        image_pil.save(in_mem_file, format=image_format)
        in_mem_file.seek(0)  # Reset the stream's position to the beginning
    except Exception as e:
        logging.error(f"Error converting PIL Image to in-memory file: {e}")
        raise Exception(f"Error converting PIL Image to in-memory file: {e}")

    try:
        # --- 2. Initialize the Google Cloud Storage Client ---
        if settings.GOOGLE_APPLICATION_CREDENTIALS:
            storage_client = storage.Client.from_service_account_json(
                project=project_id,
                json_credentials_path=settings.GOOGLE_APPLICATION_CREDENTIALS
            )
        else:
            storage_client = storage.Client(project=project_id)

        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)

        # --- 3. Upload the in-memory file to GCS ---
        # print(f"Uploading {destination_blob_name} to bucket {bucket_name}...")
        blob.upload_from_file(in_mem_file, content_type=content_type)
        # print("Upload complete.")

        # --- 4. Make the blob publicly accessible ---
        # print("Making blob public...")
        blob.make_public()
        # print("Blob is now public.")

        # --- 5. Return the public URL ---
        return blob.public_url

    except GoogleCloudError as e:
        # Catch specific GCS errors
        logging.error(f"A Google Cloud Storage error occurred: {e}")
        raise GoogleCloudError(f"Failed to upload to GCS: {e}")
    except Exception as e:
        # Catch any other unexpected errors
        logging.error(f"An unexpected error occurred during GCS upload: {e}")
        raise Exception(f"An unexpected error occurred: {e}")
