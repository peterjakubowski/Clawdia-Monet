from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings and secrets.
    """

    GOOGLE_API_KEY: str = "Missing"
    GOOGLE_APPLICATION_CREDENTIALS: str = None
    GEMINI_MODEL_FLASH: str = "models/gemini-2.5-flash"
    GEMINI_MODEL_LITE: str = "models/gemini-2.5-flash-lite"
    GEMINI_MODEL_PRO: str = "models/gemini-2.5-pro"
    GEMINI_MODEL_EXP_IMG_GEN: str = "models/gemini-2.0-flash-preview-image-generation"
    GEMINI_MODEL_PREVIEW_IMG_GEN: str = "models/gemini-2.5-flash-image-preview"
    FIRESTORE_LOG_COLLECTION: str = "default_log"
    GCS_BUCKET_NAME: str = "Missing"
    GCP_PROJECT_ID: str = "Missing"

    model_config = SettingsConfigDict(env_file='.env', extra='ignore')


# Create a single instance of the Settings class
settings = Settings()
