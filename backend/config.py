"""
Configuration management for BoxCostPro backend.
Uses Pydantic Settings for type-safe environment variable management.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application configuration settings."""
    
    # Application
    app_url: str = "http://localhost:8000"
    environment: str = "development"
    port: int = 8000
    
    # Database
    database_url: str
    
    # Session
    session_secret: str
    
    # Clerk Authentication
    clerk_secret_key: str
    
    # Admin
    admin_session_timeout: int = 1800  # 30 minutes
    
    # Email
    from_email: Optional[str] = "noreply@boxcostpro.com"
    from_name: Optional[str] = "BoxCostPro"
    
    # Google OAuth
    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None
    
    # Razorpay
    razorpay_key_id: Optional[str] = None
    razorpay_key_secret: Optional[str] = None
    razorpay_webhook_secret: Optional[str] = None
    
    # Stripe
    stripe_api_key: Optional[str] = None
    stripe_webhook_secret: Optional[str] = None
    
    # SMTP Email
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    
    # AWS SES
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: str = "ap-south-1"
    
    # Redis
    redis_url: Optional[str] = None
    
    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:5173"
    
    # File Upload
    max_upload_size: int = 5242880  # 5MB
    
    # Logging
    log_level: str = "INFO"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    @property
    def cors_origins_list(self) -> list[str]:
        """Return CORS origins as a list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment.lower() == "development"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment.lower() == "production"


# Global settings instance
settings = Settings()
