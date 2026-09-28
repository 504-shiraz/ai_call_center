import os

from dotenv import load_dotenv

load_dotenv()

class Settings:
    
    """
        Settings class to manage application configuration.
    """
    APP_NAME: str = os.getenv("APP_NAME", "AI Call Center")
    APP_ENV: str = os.getenv("APP_ENV", "development")

    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434/v1")
    OLLAMA_TIMEOUT_SECONDS: float = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "120"))
    OLLAMA_MAX_COMPLETION_TOKENS: int = int(os.getenv("OLLAMA_MAX_COMPLETION_TOKENS", "256"))
    
    LIVEKIT_URL:str = os.getenv("LIVEKIT_URL", "wss://ai-call-center-11vcgwxx.livekit.cloud")
    LIVEKIT_API_KEY:str = os.getenv("LIVEKIT_API_KEY")
    LIVEKIT_API_SECRET:str = os.getenv("LIVEKIT_API_SECRET")

    EMAIL_ENABLED: bool = os.getenv("EMAIL_ENABLED", "false").lower() == "true"
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "")
    SMTP_USE_TLS: bool = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

settings = Settings()