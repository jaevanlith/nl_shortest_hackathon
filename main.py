import logging
import yaml
from src.config_manager import ConfigManager
from src.groq_service import GroqChatService
from src.slack_bot import SlackBot

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Main function to initialize and run the SlackBot."""
    try:
        logger.info("Application starting (from root main.py, using src modules)...")
        config_manager = ConfigManager()
        
        logger.info("Initializing GroqChatService...")
        groq_service = GroqChatService(
            api_key=config_manager.groq_api_key,
            model_name=config_manager.model_name
        )
        logger.info("GroqChatService initialized.")
        
        logger.info("Initializing SlackBot...")
        slack_bot = SlackBot(config=config_manager, chat_service=groq_service)
        logger.info("SlackBot initialized.")
        
        slack_bot.start()
        
    except ValueError as ve: # For configuration specific errors from ConfigManager or services
        logger.critical(f"Configuration or Value error during startup: {ve}. Application cannot start.", exc_info=True)
        exit(1)
    except FileNotFoundError as fnfe:
        logger.critical(f"A required file was not found during startup: {fnfe}. Application cannot start.", exc_info=True)
        exit(1)
    except yaml.YAMLError as ye:
        logger.critical(f"YAML parsing error likely from config.yaml: {ye}. Application cannot start.", exc_info=True)
        exit(1)
    except ImportError as ie:
        logger.critical(f"Import error, please check if 'src' is a package (contains __init__.py) and all modules are correctly placed: {ie}. Application cannot start.", exc_info=True)
        exit(1)
    except Exception as e:
        logger.critical(f"An unexpected critical error occurred during startup: {e}", exc_info=True)
        exit(1)

if __name__ == "__main__":
    main()
