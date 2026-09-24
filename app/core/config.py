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
    
    LIVEKIT_URL:str = os.getenv("LIVEKIT_URL", "wss://ai-call-center-11vcgwxx.livekit.cloud")
    LIVEKIT_API_KEY:str = os.getenv("LIVEKIT_API_KEY")
    LIVEKIT_API_SECRET:str = os.getenv("LIVEKIT_API_SECRET")

settings = Settings()