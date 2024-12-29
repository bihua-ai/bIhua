import os
from dotenv import load_dotenv

class ConfigLoader:
    def __init__(self, config_dir, env_file_name=".env", log_config_file_name="log.config"):
        """
        Initialize the ConfigLoader. It will set the config directory.
        If no directory is provided, it will use the `CONFIG_DIR` environment variable
        or default to './configs'.
        """
        self.config_dir = config_dir
        self.env_file_name = env_file_name
        self.log_config_file_name = log_config_file_name
        
        if not self.config_dir:
            raise ValueError("No config directory provided, either through argument or environment variable.")
        
        if not os.path.exists(self.config_dir):
            raise FileNotFoundError(f"Config directory '{self.config_dir}' not found.")
        
        # Ensure environment and log config files exist
        self.env_path = os.path.join(self.config_dir, self.env_file_name)
        if not os.path.exists(self.env_path):
            raise FileNotFoundError(f"Environment file '{self.env_file_name}' not found in config directory.")
        
        self.log_config_path = os.path.join(self.config_dir, self.log_config_file_name)
        if not os.path.exists(self.log_config_path):
            raise FileNotFoundError(f"Log configuration file '{self.log_config_file_name}' not found in config directory.")
        
        # Load .env file to manage environment variables
        self.load_env()

    def load_env(self):
        """Load the .env file to set environment variables."""
        if os.path.exists(self.env_path):
            load_dotenv(self.env_path)
        else:
            raise FileNotFoundError(".env file not found in config directory.")
    
    def get_log_config_path(self):
        """Return the absolute path of the log configuration file."""
        return os.path.abspath(self.log_config_path)

class ConfigManager:
    def __init__(self, config_dir, env_file_name=".env", log_config_file_name="log.config"):
        """Initialize ConfigManager, and create an instance of ConfigLoader."""
        self.config_loader = ConfigLoader(config_dir, env_file_name=env_file_name, log_config_file_name=log_config_file_name)

    def get_config_loader(self):
        """Return the instance of ConfigLoader."""
        return self.config_loader

# A singleton-like global reference to the config manager instance
config_manager = None

def initialize_config_manager(config_dir, env_file_name=".env", log_config_file_name="log.config"):
    """Initialize the config manager with the provided directory path."""
    global config_manager
    if config_manager is None:
        config_manager = ConfigManager(config_dir, env_file_name=env_file_name, log_config_file_name=log_config_file_name)

def get_log_config_path():
    """Get the absolute path of the log configuration file."""
    global config_manager
    if config_manager is not None:
        return config_manager.get_config_loader().get_log_config_path()
    else:
        raise RuntimeError("ConfigManager not initialized.")

# Automatically initialize the config manager when this module is imported
config_dir = os.getenv("BIHUA_CONFIG_DIR", "./configs")  # Default to './configs' if the environment variable is not set
initialize_config_manager(config_dir)

# Set the Environment Variable: You can set the CONFIG_DIR environment variable in your environment before running the script. For example:

# In Linux/macOS cli: export BIHUA_CONFIG_DIR="/opt/bihua/data/configs"
# In Windows: set BIHUA_CONFIG_DIR=C:\path\to\your\configs
# Then, when you import the configuration_manager, it will automatically use the path set in CONFIG_DIR.