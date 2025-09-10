# Clawdia Monet
#
# Author: Peter Jakubowski
# Date: 9/9/2025
# Description: Streamlit app logging setup for Clawdia Monet
#

import logging
import logging.config
import google.cloud.logging
import sys
import os


def setup_logging():
    """
    Sets up logging. If running in Google Cloud Run, it configures a
    structured JSON logger. Otherwise, it configures a basic logger that
    prints to the console.

    This function is safe to call multiple times.
    """
    # Only configure logging if no handlers are attached to the root logger.
    if len(logging.getLogger().handlers) > 0:
        return

    # Check if we are running in a Google Cloud Run environment.
    # The K_SERVICE environment variable is a reliable indicator.
    if "K_SERVICE" in os.environ:
        # --- We are in Google Cloud Run ---
        try:
            client = google.cloud.logging.Client()

            # This helper attaches the GCP handler to the root logger
            client.setup_logging(log_level=logging.INFO)
        except Exception as e:
            logging.error("Failed to setup Google Cloud logging.")
        else:
            logging.info("Successfully configured Google Cloud structured logging.")
    else:
        # --- We are in a local development environment ---
        # Configure a basic logger that prints to standard out
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[logging.StreamHandler(sys.stdout)]
        )
        logging.info("Configured basic console logging for local development.")
