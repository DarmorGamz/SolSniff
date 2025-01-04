import os
import sys
import threading
import asyncio
import websockets
import json
import time
import logging
import datetime
from colorama import init, Fore, Style

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
    fmt='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

# Console handler (info and above to console, can adjust if you want debug in console too)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter(
    fmt='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
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
RPC_WS_URL = "wss://api.mainnet-beta.solana.com"
SPL_TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"

HEARTBEAT_INTERVAL = 30
RECONNECT_DELAY = 5

###############################################################################
# Keepalive / Heartbeat
###############################################################################
async def keepalive(websocket):
    """Send heartbeats periodically to keep the WebSocket alive."""
    while True:
        try:
            await websocket.ping()
            await asyncio.sleep(HEARTBEAT_INTERVAL)
        except Exception as e:
            log_warning(f"Heartbeat failed: {e}")
            break

###############################################################################
# Main Sniffing (Token Creation) Logic
###############################################################################
async def sniff_solana():
    """ Continuously sniff for new SPL token creation (InitializeMint). """
    while True:
        try:
            async with websockets.connect(
                RPC_WS_URL,
                ping_interval=None,
                close_timeout=10
            ) as websocket:
                log_info("Connected to Solana WebSocket endpoint (Sniffer).")

                # Start keepalive task
                asyncio.create_task(keepalive(websocket))

                # Subscribe to logs mentioning the token program
                subscription_request = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "logsSubscribe",
                    "params": [
                        "all",
                        {"mentions": [SPL_TOKEN_PROGRAM_ID]}
                    ]
                }
                await websocket.send(json.dumps(subscription_request))
                log_info("Subscription request sent.")

                while True:
                    response = await websocket.recv()
                    log_debug(f"< TEXT {response}")

                    data = json.loads(response)
                    if data.get("method") == "logsNotification":
                        notification = data["params"]["result"]
                        slot = notification["context"]["slot"]
                        logs = notification["value"]["logs"]

                        log_debug(f"Raw logs for slot={slot}:\n{json.dumps(logs, indent=2)}")

                        # Look for "Instruction: InitializeMint"
                        found_initialize = any(
                            "Program log: Instruction: InitializeMint" in ln
                            for ln in logs
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

                                # Check if the mint address is added to a Raydium pool
                                is_raydium_pool = any(
                                    "Program log: process_swap_base_in_with_user_account" in ln
                                    for ln in logs
                                )
                                if is_raydium_pool:
                                    log_info(f"  Mint address {mint_address} is part of a Raydium pool!")
                                    # Perform snipe logic here (e.g., submit a transaction to buy the token)
                            else:
                                log_warning("  Could not parse the mint address from logs.")

                    elif "error" in data:
                        log_error(f"Received error from Solana: {data['error']}")
                    else:
                        log_debug(f"Sniffer received message: {data}")

        except websockets.exceptions.ConnectionClosed as e:
            log_warning(f"(Sniffer) Connection closed: {e}. Reconnecting in {RECONNECT_DELAY}s...")
            await asyncio.sleep(RECONNECT_DELAY)
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
