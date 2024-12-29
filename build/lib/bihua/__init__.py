# bihua/__init__.py

# Package version
__version__ = "0.0.1"

# Import submodules or classes to make them available directly at the package level
# from .messenger_resident import admin_login # function
# from .messenger_resident import Resident # Class
# from .hello import hello_world # function
from .bihua_logging import get_logger
from .bihua_one_star import Star
from .new_bihua_star_hub import Hub
from .new_bihua_agentservice import BihuaAgentService


# Optionally, define package-wide variables or constants
# CONSTANT_VALUE = 42

# Package initialization code (this runs when the package is imported)
print("Initializing bihua package!")
