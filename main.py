import asyncio

from core.logs.logs import log_info, log_debug, log_warning, log_error
from core.threads.pool_threads import SolanaSniffer
from constants.constants import RPC_WS_URL, SPL_TOKEN_PROGRAM_ID, RAYDIUM_AMM_PROGRAM_ID,RPC_HTTP_URL
from constants.constants import RECONNECT_DELAY

# Example usage with a proper asyncio event loop
async def main():
    sniffer = SolanaSniffer(rpc_ws_url=RPC_HTTP_URL, reconnect_delay=RECONNECT_DELAY)

    # Add sniffers for different program IDs
    sniffer.add_sniffer(SPL_TOKEN_PROGRAM_ID)
    sniffer.add_sniffer(RAYDIUM_AMM_PROGRAM_ID)

    # Run indefinitely or until you cancel it
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        # Stop all tasks gracefully when interrupted
        await sniffer.stop_all()

###############################################################################
# Main
###############################################################################
if __name__ == "__main__":
    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        log_info("Exiting...")
