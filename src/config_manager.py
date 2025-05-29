import os
import yaml
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class ConfigManager:
    """Manages loading and access to configuration settings."""
    def __init__(self, env_file=".env", config_file="config.yaml"):
        # Adjust env_file path if main.py is in root and .env is in root
        # For now, assume .env is found relative to the CWD where main.py is run.
        # If .env is in src/, this would be env_file="src/.env"
        # If .env is in root, and CWD is root, .env is fine.
        load_dotenv(dotenv_path=env_file) 
        self.config_data = self._load_yaml_config(config_file)

        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.slack_bot_token = os.getenv("SLACK_BOT_TOKEN")
        self.slack_app_token = os.getenv("SLACK_APP_TOKEN")
        self.slack_test_channel_id = os.getenv("SLACK_TEST_CHANNEL_ID")
        
        self._validate_critical_configs()

    def _load_yaml_config(self, config_file):
        # config.yaml is also assumed to be relative to CWD (project root)
        try:
            with open(config_file, 'r') as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            logger.error(f"Configuration file '{config_file}' not found at expected location.")
            raise
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML configuration file '{config_file}': {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error loading '{config_file}': {e}")
            raise

    def _validate_critical_configs(self):
        if not self.groq_api_key:
            logger.error("GROQ_API_KEY not found in environment or .env file.")
            raise ValueError("GROQ_API_KEY is not set.")
        if not self.slack_bot_token:
            logger.error("SLACK_BOT_TOKEN not found in environment or .env file.")
            raise ValueError("SLACK_BOT_TOKEN is not set.")
        if not self.slack_app_token:
            logger.error("SLACK_APP_TOKEN not found in environment or .env file.")
            raise ValueError("SLACK_APP_TOKEN is not set.")
        if not self.config_data or 'model' not in self.config_data or 'name' not in self.config_data['model']:
            logger.error("Model name not found in config.yaml or config.yaml is invalid.")
            raise ValueError("Model name configuration is missing or invalid.")

    @property
    def model_name(self):
        return self.config_data['model']['name'] 