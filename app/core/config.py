from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


# class Settings(BaseSettings):
#     model_config = SettingsConfigDict(env_file=".env", extra="ignore")

#     # Database
#     database_url: str
#     database_url_sync: str

#     # Auth
#     jwt_secret_key: str
#     jwt_algorithm: str = "HS256"
#     access_token_expire_minutes: int = 30
#     refresh_token_expire_days: int = 14

#     # Local AI
#     ollama_base_url: str = "http://localhost:11434"
#     ollama_model: str = "llama3.1:8b"
#     whisper_model_size: str = "base"
#     whisper_device: str = "cpu"
#     piper_binary_path: str = "/usr/local/bin/piper"
#     piper_voice_model_path: str = "/opt/piper/voices/en_US-lessac-medium.onnx"
#     audio_storage_dir: str = "./storage/audio"
#     resume_storage_dir: str = "./storage/resumes"

#     # App
#     cors_origins: str = "http://localhost:4200"
#     environment: str = "development"

#     @property
#     def cors_origin_list(self) -> list[str]:
#         return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


# @lru_cache
# def get_settings() -> Settings:
#     return Settings()




class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str
    database_url_sync: str

    # Auth
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 14

    # Local AI
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    whisper_model_size: str = "base"
    whisper_device: str = "cpu"
    piper_binary_path: str = "/usr/local/bin/piper"
    piper_voice_model_path: str = "/opt/piper/voices/en_US-lessac-medium.onnx"
    audio_storage_dir: str = "./storage/audio"
    resume_storage_dir: str = "./storage/resumes"

    # App
    cors_origins: str = "*"
    environment: str = "development"

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins == "*":
            return ["*"]
        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]

@lru_cache
def get_settings() -> Settings:
    return Settings()