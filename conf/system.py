import os
import json5
from conf.path import CONF_ROOT
from pydantic import BaseModel, ValidationError, field_validator, model_validator


class SystemConfig(BaseModel):
    """
    Configuration for the system.
    """

    # plan_enabled: bool = True  # Flag to enable or disable planning features
    executor_replan_enabled: bool = True  # Flag to enable or disable execution features
    llm_model: str
    orchestrator_llm_model: str
    critic_llm_model: str
    plan_critic_iter_num: int
    html_gen_llm_model: str
    code_gen_llm_model: str
    executor_llm_model: str
    article_llm_model: str
    science_llm_model: str
    solution_llm_model: str
    openai_reasoning_effort: str | None = "low"
    gemini_thinking_level: str = "LOW"
    gemini_thinking_budget: int | None = None
    api_port: int
    app_name: str
    user_id_default: str
    session_id_default_prefix: str
    max_iterations_orchestrator: int
    max_search_count: int
    log_level: str
    log_file: str
    retention: str
    rotation: str
    # password: dict
    secret_key: str
    base_dir: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    session_database_dir: str = os.path.join(base_dir, 'database', 'session_database')
    os.makedirs(session_database_dir, exist_ok=True)
    DEBUG_USERS: list
    # DEBUG_USER_1: str
    email_config: dict  # Email configuration, including sender_email and sender_password
    google_oauth_config: dict  # Google OAuth configuration, including client_id, client_secret, redirect_uri
    stripe_config: dict  # Stripe configuration, including secret_key and subscription prices

    @field_validator("openai_reasoning_effort", mode="before")
    @classmethod
    def normalize_openai_reasoning_effort(cls, value: str | None) -> str | None:
        """Normalize OpenAI reasoning effort so config is case-insensitive."""
        if value is None:
            return None
        normalized_value = value.strip().lower()
        return normalized_value or None

    @field_validator("gemini_thinking_level", mode="before")
    @classmethod
    def normalize_gemini_thinking_level(cls, value: str) -> str:
        """Normalize Gemini thinking level so config is case-insensitive."""
        return value.strip().upper()

def load_system_config(config_file_path: str) -> SystemConfig:
    """
    Load the system configuration from a file.

    Args:
        config_file_path (str): Path to the configuration file.

    Returns:
        SystemConfig: An instance of SystemConfig with loaded settings.
    """
    try:
        with open(config_file_path, "r") as file:
            config_data = json5.load(file)
            return SystemConfig(**config_data)
    except (FileNotFoundError, json5.JSONDecodeError, ValidationError) as e:
        print(
            f"FATAL: Could not load system configuration from {config_file_path}. Reason: {e}"
        )
        raise


SYS_CONFIG: SystemConfig = load_system_config(
os.path.join(CONF_ROOT, "jsons/system.json")
)
