import asyncio
from typing import Dict
from solana.rpc.async_api import AsyncClient

from solders.rpc.responses import LogsNotification
from solders.rpc.config import (
    RpcTransactionLogsFilterMentions
)
from core.logs.logs import log_info, log_debug, log_warning, log_error
from core.parser.parser import InstructionParser

class SolanaSniffer:
    def __init__(self, rpc_ws_url: str, reconnect_delay: int = 5):
        self.rpc_ws_url = rpc_ws_url
        self.reconnect_delay = reconnect_delay
        self.tasks: Dict[str, asyncio.Task] = {}
        self.parser = InstructionParser()

    async def _sniff_logs(self, program_id: str):
        """Continuously sniff logs for the given program ID."""
        client = None
        while True:
            try:
                async with AsyncClient(self.rpc_ws_url) as client:
                    log_info(f"Connected to Solana WebSocket endpoint for program {program_id}.")
                    res = await client.is_connected()
                    log_info(f"Connected: {res}")
                    client.prog

            except asyncio.CancelledError:
                log_info(f"Sniffer for program {program_id} was cancelled.")
                raise  # Re-raise the exception to propagate cancellation
            except Exception as e:
                log_error(f"Unexpected error for program {program_id}: {e}. Reconnecting in {self.reconnect_delay}s...")
                await asyncio.sleep(self.reconnect_delay)
            finally:
                if client and not client.closed:
                    await client.close()
                    log_info(f"WebSocket connection for program {program_id} closed.")

    def add_sniffer(self, program_id: str):
        """Add a new sniffer task for the given program ID."""
        if program_id in self.tasks:
            log_info(f"Sniffer for program {program_id} is already running.")
            return

        log_info(f"Starting sniffer for program {program_id}.")
        task = asyncio.create_task(self._sniff_logs(program_id))
        self.tasks[program_id] = task

    def remove_sniffer(self, program_id: str):
        """Remove the sniffer task for the given program ID."""
        if program_id not in self.tasks:
            log_info(f"No sniffer found for program {program_id}.")
            return

        log_info(f"Stopping sniffer for program {program_id}.")
        task = self.tasks.pop(program_id)
        task.cancel()

    async def stop_all(self):
        """Stop all running sniffer tasks."""
        log_info("Stopping all sniffer tasks.")
        for program_id, task in self.tasks.items():
            log_info(f"Stopping sniffer for program {program_id}.")
            task.cancel()
        self.tasks.clear()