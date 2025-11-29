from typing import Optional, ClassVar

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):   
    # Allow loading values from environment variables and an optional .env file.
    # Example: LOGFILE, MQTT_HOST, MQTT_PORT, etc. or put them in a `.env` file.
    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8'
    )
    
    DEBUG: bool = False
    LOGFILE: Optional[str] = None
    LOGLEVEL: int = 20

    # Publish incident pages to MQTT
    MQTT_ENABLE: bool = False

    # Publish Pagergate keepalives to MQTT
    MQTT_PUBLISH_KEEPALIVES: bool = True

    # MQTT TLS Configuration
    MQTT_CERTFILE: Optional[str] = None
    MQTT_KEYFILE: Optional[str] = None
    MQTT_CACERTS: Optional[str] = None

    MQTT_HOST: Optional[str] = None
    MQTT_PORT: int = 1883
    MQTT_USER: Optional[str] = None
    MQTT_PASS: Optional[str] = None

    # Save each page to a local file
    OUTPUT_FILE: Optional[str] = None

    ## Format to write the output lines. Currently only json is supported
    OUTPUT_FORMAT: str = "json"

    # Write Pagergate keepalives to file
    OUTPUT_FILE_KEEPALIVES: bool = False

    KEEPALIVE_INTERVAL: int = 120
    KEEPALIVE_MISSED: int = 3   
