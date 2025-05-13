from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    rapidapi_key: str

    # Scraper settings
    use_mock_data: bool = False
    headless_browser: bool = True

    # API settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    model_config = {
        "env_file": ".env",
        "extra": "allow"
    }

settings = Settings()