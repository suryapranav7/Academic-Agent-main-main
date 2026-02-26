"""
Configuration settings for the Student Agent System
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # OpenAI Configuration
    openai_api_key: str
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    
    # Database Configuration
    database_path: str = "data/student_records.db"
    vector_db_path: str = "data/vector_db"
    
    # System Configuration
    pass_threshold: int = 70
    max_questions_per_assessment: int = 10
    difficulty_adjustment_step: float = 0.15
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/system.log"
    
    # CrewAI Configuration
    crewai_verbose: bool = True
    
    @property
    def database_url(self) -> str:
        """Generate SQLAlchemy database URL"""
        db_path = Path(self.database_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{db_path}"
    
    @property
    def vector_db_directory(self) -> Path:
        """Get vector database directory path"""
        path = Path(self.vector_db_path)
        path.mkdir(parents=True, exist_ok=True)
        return path


# Global settings instance
settings = Settings()