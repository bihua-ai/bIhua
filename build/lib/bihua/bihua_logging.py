import logging
from logging.handlers import RotatingFileHandler
import os
from dotenv import load_dotenv

# Log file directory and name
load_dotenv()
log_path = os.getenv("STAR_LOG_PATH")
star_log_file_max_size = int(os.getenv("STAR_LOG_FILE_MAX_SIZE"))
star_log_file_backup_count = int(os.getenv("STAR_LOG_FILE_BACKUP_COUNT"))


LOG_DIR = os.path.dirname(log_path)
LOG_FILE = os.path.basename(log_path)

# _star =Star()
# LOG_DIR = os.path.dirname(_star.star_log_path)
# LOG_FILE = os.path.basename(_star.star_log_path)

# Create the log directory if it doesn't exist
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# Define log file path
log_file_path = os.path.join(LOG_DIR, LOG_FILE)

# Define logging format
log_format = "%(asctime)s - %(levelname)s - %(message)s"

# Set up the logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# File handler with size-based rotation (max size: 10MB, keep 3 backup files)

file_handler = RotatingFileHandler(log_file_path, maxBytes=star_log_file_max_size, backupCount=star_log_file_backup_count)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter(log_format))

# Stream handler (logs to console)
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)  # Default to INFO level for console output
stream_handler.setFormatter(logging.Formatter(log_format))

# Add handlers to the logger
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

def get_logger():
    """Returns the configured logger instance."""
    return logger

# Example usage:
# if __name__ == "__main__":
#     logger.debug("This is a debug message.")
#     logger.info("This is an info message.")
#     logger.warning("This is a warning message.")
#     logger.error("This is an error message.")
#     logger.critical("This is a critical message.")



