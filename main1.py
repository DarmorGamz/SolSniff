import os
import sys
import threading
import asyncio
import json
import time
import logging
import datetime
from colorama import init, Fore, Style
from solana.rpc.async_api import AsyncClient
from solana.rpc.websocket_api import connect
from solders.pubkey import Pubkey

from solders.rpc.config import (
    RpcTransactionLogsFilter,
)

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


###############################################################################
# Configuration
###############################################################################
RPC_HTTP_URL = "https://api.mainnet-beta.solana.com"
RPC_WS_URL = "wss://api.mainnet-beta.solana.com"
SPL_TOKEN_PROGRAM_ID = Pubkey("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")

HEARTBEAT_INTERVAL = 30
RECONNECT_DELAY = 5


###############################################################################
# Main Sniffing (Token Creation) Logic
###############################################################################
async def sniff_solana():
    """ Continuously sniff for new SPL token creation (InitializeMint). """
    while True:
        try:
            async with connect(RPC_WS_URL) as websocket:
                log_info("Connected to Solana WebSocket endpoint (Sniffer).")

                # Subscribe to logs mentioning the token program
                subscription_id = await websocket.logs_subscribe(
                    filter=RpcTransactionLogsFilter(SPL_TOKEN_PROGRAM_ID)
                )
                log_info(f"Subscription request sent. ID: {subscription_id}")

                async for msg in websocket:
                    log_debug(f"< TEXT {msg}")

                    if msg.get("method") == "logsNotification":
                        notification = msg["params"]["result"]
                        slot = notification["context"]["slot"]
                        logs = notification["value"]["logs"]

                        log_debug(f"Raw logs for slot={slot}:\n{json.dumps(logs, indent=2)}")

                        # Look for "Instruction: InitializeMint"
                        found_initialize = any(
                            "Instruction: InitializeMint" in ln for ln in logs
                        )
                        if found_initialize:
                            log_info(f"[Token Creation] Found InitializeMint in slot {slot}")
                            mint_address = None

                            # Improved mint address parsing
                            for ln in logs:
                                if "InitializeMint" in ln and "Mint" in ln:
                                    mint_address = ln.split("Mint")[-1].strip().split()[0]
                                    break

                                if "Program log: Mint:" in ln:
                                    mint_address = ln.split("Mint:")[-1].strip().split()[0]
                                    break

                            if mint_address:
                                log_info(f"  Found mint address: {mint_address}")
                            else:
                                log_warning("  Could not parse the mint address from logs.")

                    elif "error" in msg:
                        log_error(f"Received error from Solana: {msg['error']}")
                    else:
                        log_debug(f"Sniffer received message: {msg}")

        except Exception as e:
            log_error(f"(Sniffer) Unexpected error: {e}. Reconnecting in {RECONNECT_DELAY}s...")
            await asyncio.sleep(RECONNECT_DELAY)


def start_sniffer_thread():
    """Starts the asyncio sniffer in a dedicated thread."""
    def run_loop():
        asyncio.run(sniff_solana())

    t = threading.Thread(target=run_loop, daemon=True)
    t.start()
    return t


###############################################################################
# Main
###############################################################################
if __name__ == "__main__":
    # Start the sniffer thread
    sniffer_thread = start_sniffer_thread()

    log_info(f"Logging to file: {LOG_PATH}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log_info("Exiting...")
