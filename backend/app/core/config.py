from typing import List, Optional, Union
from pydantic import AnyHttpUrl, validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Research Assistant"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    
    # DATABASE
    # To be replaced with actual PostgreSQL URL in production
    SQLALCHEMY_DATABASE_URI: Optional[str] = "postgresql://postgres:postgres@localhost:5432/ai_researcher"
    
    # REDIS
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    
    # EXTERNAL APIS
    TAVILY_API_KEY: Optional[str] = None
    SERPAPI_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    
    # CORS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []

    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()
