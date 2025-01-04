import threading
import asyncio
import websockets
import json
import time
import logging
import requests
from collections import deque
from colorama import init, Fore, Style

init(autoreset=True)  # Initialize colorama so styles reset automatically

##################################################################
# Configuration
##################################################################
RPC_WS_URL = "wss://api.mainnet-beta.solana.com"
RPC_HTTP_URL = "https://api.mainnet-beta.solana.com"  # For follow-up getAccountInfo
RATE_LIMIT = 5  # Number of requests allowed per second
HEARTBEAT_INTERVAL = 30  # Seconds for sending a heartbeat
RECONNECT_DELAY = 5  # Seconds to wait before reconnecting after an error
SPL_TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"

##################################################################
# Logger Setup with Color
##################################################################
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def log_info(msg):
    logging.info(f"{Fore.GREEN}{msg}{Style.RESET_ALL}")

def log_warning(msg):
    logging.warning(f"{Fore.YELLOW}{msg}{Style.RESET_ALL}")

def log_error(msg):
    logging.error(f"{Fore.RED}{msg}{Style.RESET_ALL}")

def log_debug(msg):
    logging.debug(f"{Fore.WHITE}{msg}{Style.RESET_ALL}")

##################################################################
# Simple Rate Limiter
##################################################################
class RateLimiter:
    def __init__(self, rate_limit):
        self.rate_limit = rate_limit
        self.timestamps = deque()

    def is_allowed(self):
        """Return True if we can perform an action, False if rate-limited."""
        now = time.time()
        while self.timestamps and self.timestamps[0] < now - 1:
            self.timestamps.popleft()

        if len(self.timestamps) < self.rate_limit:
            self.timestamps.append(now)
            return True
        return False

rate_limiter = RateLimiter(RATE_LIMIT)

##################################################################
# Keepalive / Heartbeat
##################################################################
async def keepalive(websocket):
    """Send heartbeats to keep the WebSocket connection alive."""
    while True:
        try:
            await websocket.ping()
            await asyncio.sleep(HEARTBEAT_INTERVAL)
        except Exception as e:
            log_warning(f"Heartbeat failed: {e}")
            break

##################################################################
# Helper: Fetch Token Name
##################################################################
def get_token_name(mint_address: str) -> str:
    """
    Attempt to fetch a human-readable name (if available).
    This uses getAccountInfo with `jsonParsed` encoding.
    Not all tokens will have a 'name' field.
    """
    try:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getAccountInfo",
            "params": [
                mint_address,
                {"encoding": "jsonParsed"}
            ]
        }
        headers = {"Content-Type": "application/json"}
        response = requests.post(RPC_HTTP_URL, json=payload, headers=headers, timeout=10)
        res_json = response.json()

        # If the mint is found and is a parsed SPL token, check for a "name" or "symbol"
        value = res_json.get("result", {}).get("value")
        if value is None:
            return "UnknownName"

        data = value.get("data", {})
        if not isinstance(data, dict):
            return "UnknownName"

        parsed = data.get("parsed", {})
        if not isinstance(parsed, dict):
            return "UnknownName"

        # For SPL tokens, you might see something like:
        # {
        #   "parsed": {
        #       "info": {
        #           "decimals": 9,
        #           "name": "MyToken",  <-- sometimes present
        #           "symbol": "MTK",    <-- sometimes present
        #           ...
        #        },
        #       "type": "mint"
        #   },
        #   ...
        # }
        info = parsed.get("info", {})
        token_name = info.get("name") or info.get("symbol") or "UnknownName"
        return token_name

    except Exception as e:
        log_debug(f"Error fetching token name for {mint_address}: {e}")
        return "UnknownName"

##################################################################
# Main Sniffing Coroutine
##################################################################
async def sniff_solana():
    """Continuously listen for new token creation (InitializeMint) instructions."""
    while True:
        try:
            # Connect to Solana WebSocket
            async with websockets.connect(RPC_WS_URL, ping_interval=None) as websocket:
                log_info("Connected to Solana WebSocket endpoint.")

                # Start the keepalive coroutine
                asyncio.create_task(keepalive(websocket))

                # Subscribe to logs that mention the SPL Token program
                subscription_request = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "logsSubscribe",
                    "params": [
                        "all",
                        {"mentions": [SPL_TOKEN_PROGRAM_ID]}
                    ]
                }

                if rate_limiter.is_allowed():
                    await websocket.send(json.dumps(subscription_request))
                    log_info("Subscription request sent.")
                else:
                    log_warning("Rate limit exceeded. Skipping subscription request.")
                    await asyncio.sleep(1)

                # Listen forever for logs
                while True:
                    response = await websocket.recv()
                    data = json.loads(response)

                    # If it’s a logsNotification, parse it
                    if data.get("method") == "logsNotification":
                        # The logs are usually in data["params"]["result"]["value"]["logs"]
                        notification = data["params"]["result"]
                        slot = notification["context"]["slot"]
                        logs = notification["value"]["logs"]

                        # Look for the "InitializeMint" instruction
                        for line in logs:
                            if "Program log: Instruction: InitializeMint" in line:
                                # We found a newly initialized token mint
                                log_info(f"[Token Creation] Found InitializeMint in slot {slot}")

                                # Attempt to parse the mint address from logs
                                # Typically, you might see something like:
                                # "Program log: InitializeMint: Mint <Pubkey> Authority <Pubkey> ..."
                                mint_address = None
                                for l in logs:
                                    if "InitializeMint" in l and "Mint" in l:
                                        # A naive approach to parse out the mint key
                                        # Example line: "Program log: InitializeMint: Mint BpfProgram1111111111111111111111111111111111 ..."
                                        parts = l.split("Mint")
                                        if len(parts) > 1:
                                            # Grab whatever follows 'Mint '
                                            candidate = parts[1].strip().split()[0]
                                            # Validate that it's a base58-ish string
                                            if len(candidate) > 30:  # rough check
                                                mint_address = candidate
                                                break

                                if mint_address:
                                    # Fetch a possible token name (if any)
                                    token_name = get_token_name(mint_address)
                                    log_info(
                                        f"[Token Creation] Mint Address: {mint_address} | Name: {token_name}"
                                    )
                                else:
                                    log_warning("Could not parse the mint address from logs.")
                    
                    # Some other message (subscription confirmation, error, etc.)
                    elif "error" in data:
                        log_error(f"Received error from Solana: {data['error']}")
                    else:
                        log_debug(f"Message received: {data}")

        except websockets.exceptions.ConnectionClosed as e:
            log_warning(f"Connection closed: {e} Reconnecting in {RECONNECT_DELAY} seconds...")
            await asyncio.sleep(RECONNECT_DELAY)
        except Exception as e:
            log_error(f"Unexpected error: {e}. Reconnecting in {RECONNECT_DELAY} seconds...")
            await asyncio.sleep(RECONNECT_DELAY)

##################################################################
# Entry Point for the Sniffing Thread
##################################################################
def log_token_creations():
    """Runs the asyncio event loop to sniff the Solana blockchain logs."""
    asyncio.run(sniff_solana())

##################################################################
# Main Thread / Startup
##################################################################
if __name__ == "__main__":
    sniffer_thread = threading.Thread(target=log_token_creations, daemon=True)
    sniffer_thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log_info("Exiting...")
