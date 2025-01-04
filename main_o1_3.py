import threading
import asyncio
import websockets
import json
import time
import logging
import requests
from collections import deque
from queue import Queue
from colorama import init, Fore, Style

###############################################################################
# Configuration & Logging
###############################################################################
init(autoreset=True)

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

# Replace with your RPC endpoints
RPC_WS_URL = "wss://api.mainnet-beta.solana.com"
RPC_HTTP_URL = "https://api.mainnet-beta.solana.com"

RATE_LIMIT = 5  # requests/sec
HEARTBEAT_INTERVAL = 60
RECONNECT_DELAY = 5

SPL_TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"


###############################################################################
# Rate Limiter
###############################################################################
class RateLimiter:
    def __init__(self, rate_limit):
        self.rate_limit = rate_limit
        self.timestamps = deque()

    def is_allowed(self):
        now = time.time()
        while self.timestamps and self.timestamps[0] < now - 1:
            self.timestamps.popleft()
        if len(self.timestamps) < self.rate_limit:
            self.timestamps.append(now)
            return True
        return False

rate_limiter = RateLimiter(RATE_LIMIT)

###############################################################################
# Extended Token Info Class
###############################################################################
class ExtendedTokenInfo:
    """
    Stores extended info about a token:
      - decimals
      - supply
      - is_mintable (if there's a mintAuthority)
      - token_name
      - dex_listings
    """
    def __init__(self, mint_address: str):
        self.mint_address = mint_address
        self.decimals = None
        self.supply = None
        self.is_mintable = None
        self.token_name = None
        self.dex_listings = []

    def fetch_on_chain_info(self):
        """Get decimals, supply, and mint authority presence from on-chain data."""
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getAccountInfo",
                "params": [
                    self.mint_address,
                    {"encoding": "jsonParsed"}
                ]
            }
            headers = {"Content-Type": "application/json"}
            response = requests.post(RPC_HTTP_URL, json=payload, headers=headers, timeout=10)
            result_json = response.json()

            account_info = result_json.get("result", {}).get("value")
            if not account_info:
                log_debug(f"No account info found for {self.mint_address}")
                return

            data = account_info.get("data", {})
            if not isinstance(data, dict):
                return

            parsed = data.get("parsed", {})
            if parsed.get("type") != "mint":
                return

            info = parsed.get("info", {})
            self.decimals = info.get("decimals")
            raw_supply = info.get("supply")  # string
            self.supply = float(raw_supply) if raw_supply else 0.0
            mint_authority = info.get("mintAuthority")
            self.is_mintable = (mint_authority is not None)
            self.token_name = info.get("name") or info.get("symbol") or "UnknownName"

        except Exception as e:
            log_error(f"Error fetching on-chain info for {self.mint_address}: {e}")

    def find_dex_listings(self):
        """
        For demonstration, only checks Raydium.
        You can add more DEX checks here in the future (Serum, Orca, etc.).
        """
        self.dex_listings.clear()

        try:
            # Example call to a hypothetical Raydium endpoint
            raydium_response = requests.get("https://api.raydium.io/v2/sdk/token/solana", timeout=10)
            if raydium_response.ok:
                tokens_list = raydium_response.json()
                # Hypothetical check
                if self.mint_address in tokens_list.get("official", []):
                    self.dex_listings.append("Raydium")
        except Exception as e:
            log_debug(f"Raydium check error: {e}")

    def log_info(self):
        """Log final details."""
        log_info(f"[Token Extended Info] MintAddress: {self.mint_address}")
        log_info(f"  Name: {self.token_name}")
        log_info(f"  Decimals: {self.decimals}")
        log_info(f"  Supply: {self.supply}")
        log_info(f"  Mintable?: {self.is_mintable}")
        if self.dex_listings:
            log_info(f"  Available on: {', '.join(self.dex_listings)}")
        else:
            log_info(f"  Not found on known DEXs")

###############################################################################
# Queues for Multi-Threaded Work
###############################################################################
new_mint_queue = Queue()  # Mint addresses from sniffer
info_queue = Queue()      # ExtendedTokenInfo objects ready for DEX checks

###############################################################################
# Keepalive / Heartbeat
###############################################################################
async def keepalive(websocket):
    while True:
        try:
            await websocket.ping()
            await asyncio.sleep(HEARTBEAT_INTERVAL)
        except Exception as e:
            log_warning(f"Heartbeat failed: {e}")
            break

###############################################################################
# 1) Sniffer (Token Creation) Thread
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
                asyncio.create_task(keepalive(websocket))

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

                while True:
                    response = await websocket.recv()
                    data = json.loads(response)

                    if data.get("method") == "logsNotification":
                        notification = data["params"]["result"]
                        slot = notification["context"]["slot"]
                        logs = notification["value"]["logs"]

                        for i, line in enumerate(logs):
                            if "Program log: Instruction: InitializeMint" in line:
                                log_info(f"[Token Creation] Found InitializeMint in slot {slot}")
                                mint_address = None
                                
                                # Option 1: If the Mint address is in the same line
                                if "Mint " in line:
                                    # e.g. "Program log: Instruction: InitializeMint: Mint <pubkey> Authority <pubkey>"
                                    try:
                                        parts = line.split("Mint")
                                        if len(parts) > 1:
                                            candidate = parts[1].strip().split()[0]
                                            if len(candidate) >= 32:
                                                mint_address = candidate
                                    except Exception as e:
                                        log_debug(f"Parse error from same line: {e}")

                                # Option 2: If the Mint address is on a subsequent line
                                if not mint_address:
                                    # Look ahead in the logs
                                    for j in range(i+1, len(logs)):
                                        if "Mint:" in logs[j]:
                                            # e.g. "Program log: Mint: <SomePublicKey>"
                                            parts = logs[j].split("Mint:")
                                            if len(parts) > 1:
                                                candidate = parts[1].strip().split()[0]
                                                if len(candidate) >= 32:
                                                    mint_address = candidate
                                                    break
                                
                                if mint_address:
                                    log_info(f"  Found mint address: {mint_address}")
                                    # Enqueue for further processing
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
# 2) On-Chain Info Worker Thread
###############################################################################
def on_chain_info_worker():
    """
    Fetch on-chain info for new mints.
    Takes mint addresses from new_mint_queue,
    builds ExtendedTokenInfo, then pushes to info_queue.
    """
    while True:
        mint_address = new_mint_queue.get()  # Block until available
        if mint_address is None:
            # A sentinel value could be used to signal exit if needed
            break
        log_info(f"on_chain_info_worker")

        token_info = ExtendedTokenInfo(mint_address)
        token_info.fetch_on_chain_info()
        info_queue.put(token_info)

        new_mint_queue.task_done()

###############################################################################
# 3) DEX Listing Worker Thread
###############################################################################
def dex_listing_worker():
    """
    Takes ExtendedTokenInfo objects from info_queue,
    checks Raydium (or others in the future),
    then logs the results.
    """
    while True:
        token_info = info_queue.get()  # Block until available
        if token_info is None:
            break
        log_info(f"dex_listing_worker")

        token_info.find_dex_listings()
        token_info.log_info()

        info_queue.task_done()

###############################################################################
# Main
###############################################################################
if __name__ == "__main__":
    # Start the sniffer thread
    sniffer_thread = start_sniffer_thread()

    # Start the on-chain info thread
    on_chain_thread = threading.Thread(target=on_chain_info_worker, daemon=True)
    on_chain_thread.start()

    # Start the DEX listing thread
    dex_thread = threading.Thread(target=dex_listing_worker, daemon=True)
    dex_thread.start()

    try:
        # Keep main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log_info("Exiting...")
