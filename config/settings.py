from pathlib import Path
from typing import Dict, Any
import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    """Central configuration management using Pydantic Settings."""
    
    # API & External Keys
    ENTSOE_API_KEY: str = Field(default="", description="ENTSO-E Transparency API Token")
    SLACK_WEBHOOK_URL: str = Field(default="", description="Slack/Webhook URL for alerts")
    
    # Storage Paths
    DATA_DIR: Path = Field(default=BASE_DIR / "data" / "lakehouse")
    
    # Application Parameters
    LOG_LEVEL: str = Field(default="INFO")
    DEBUG: bool = Field(default=False)
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def load_zone_config(self) -> Dict[str, Any]:
        """Loads bidding zone configurations from config/zones.yaml."""
        config_path = BASE_DIR / "config" / "zones.yaml"
        if not config_path.exists():
            raise FileNotFoundError(f"Zone config file not found at {config_path}")
            
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

# Global Settings Instance
settings = Settings()