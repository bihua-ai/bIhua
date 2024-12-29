import logging
import logging.config
from logging.handlers import RotatingFileHandler
import os
import yaml
# config_manager will do load_dotenv() for us
from configuration_manager import config_manager, get_log_config_path 

# config_manager.get_config_loader().load_env() # load .env file, not really needed. Just for readability
log_path = os.getenv("STAR_LOG_PATH")
star_log_file_max_size = int(os.getenv("STAR_LOG_FILE_MAX_SIZE"))
star_log_file_backup_count = int(os.getenv("STAR_LOG_FILE_BACKUP_COUNT"))

LOG_DIR = os.path.dirname(log_path)
LOG_FILE = os.path.basename(log_path)

# Create the log directory if it doesn't exist
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

log_file_path = os.path.join(LOG_DIR, LOG_FILE)

# Try to load logging configuration from file
config_file_path = get_log_config_path()

if os.path.exists(config_file_path):
    with open(config_file_path, "r") as file:
        config = yaml.safe_load(file)
        # Replace the log file path in the configuration dynamically
        for handler in config.get("handlers", {}).values():
            if "filename" in handler:
                handler["filename"] = log_file_path
        logging.config.dictConfig(config)
        logger = logging.getLogger(__name__)
else:
    # print(f"{config_file_path} not found. Using default logging setup.")
    # Default logging setup (fallback)
    log_format = "%(asctime)s - %(levelname)s - %(message)s"
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    file_handler = RotatingFileHandler(
        log_file_path,
        maxBytes=star_log_file_max_size,
        backupCount=star_log_file_backup_count,
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(log_format))

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(logging.Formatter(log_format))

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)


def get_logger():
    """Returns the configured logger instance."""
    return logger

# Example usage:
# if __name__ == "__main__":
#     logger = get_logger()
#     logger.debug("This is a debug message.")
#     logger.info("This is an info message.")
#     logger.warning("This is a warning message.")
#     logger.error("This is an error message.")
#     logger.critical("This is a critical message.")
