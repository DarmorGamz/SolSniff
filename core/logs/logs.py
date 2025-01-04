from colorama import init, Fore, Style
import datetime
import os
import sys
import logging

###############################################################################
# Setup Logging to File + Console
###############################################################################
init(autoreset=True)

# Create logs directory if it doesn't exist
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# Generate a new logfile name for each program start
LOG_FILENAME = datetime.datetime.now().strftime('%Y%m%d-%H%M%S') + ".log"
LOG_PATH = os.path.join(LOG_DIR, LOG_FILENAME)

# Configure logging
logger = logging.getLogger()  # root logger
logger.setLevel(logging.DEBUG)

# File handler (writes debug and above to a file)
file_handler = logging.FileHandler(LOG_PATH, mode="w")
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter(
    fmt="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

# Console handler (info and above to console, can adjust if you want debug in console too)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter(
    fmt="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

def log_debug(msg):
    logger.debug(f"{Fore.WHITE}{msg}{Style.RESET_ALL}")

def log_info(msg):
    logger.info(f"{Fore.GREEN}{msg}{Style.RESET_ALL}")

def log_warning(msg):
    logger.warning(f"{Fore.YELLOW}{msg}{Style.RESET_ALL}")

def log_error(msg):
    logger.error(f"{Fore.RED}{msg}{Style.RESET_ALL}")