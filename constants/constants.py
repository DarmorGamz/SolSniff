from solders.pubkey import Pubkey


###############################################################################
# Configuration
###############################################################################
RPC_HTTP_URL = "https://api.mainnet-beta.solana.com"
RPC_WS_URL = "wss://api.mainnet-beta.solana.com"
SPL_TOKEN_PROGRAM_ID = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
RAYDIUM_AMM_PROGRAM_ID = Pubkey.from_string("RVKd61ztZW9bxemSZ6kBByTnGDRi4KzgPuAzJFnSsnR")
RAYDIUM_POOL_PROGRAM_ID = Pubkey.from_string("FRC8ebfT1Gp2xCD43zUvGfxjHaMj2rr6zjxxynFzpZpo")
HEARTBEAT_INTERVAL = 30
RECONNECT_DELAY = 5