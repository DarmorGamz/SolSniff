from core.logs.logs import log_info, log_debug, log_warning, log_error
import re

class InstructionParser:
    def __init__(self):
        """
        Initializes the InstructionParser class.
        Add any required initialization logic here.
        """
        self.handlers = {
            # Mints
            "InitializeMint2": self.handle_initialize_mint2,
            "InitializeMint": self.handle_initialize_mint,

            # Accounts & Multisig
            "InitializeAccount3": self.handle_initialize_account3,
            "InitializeAccount2": self.handle_initialize_account2,
            "InitializeAccount": self.handle_initialize_account,
            "InitializeMultisig2": self.handle_initialize_multisig2,
            "InitializeMultisig": self.handle_initialize_multisig,

            # Transfers
            "TransferChecked": self.handle_transfer_checked,
            "Transfer": self.handle_transfer,

            # Approve / Revoke
            "ApproveChecked": self.handle_approve_checked,
            "Approve": self.handle_approve,
            "Revoke": self.handle_revoke,

            # Authorities
            "SetAuthority": self.handle_set_authority,

            # Minting / Burning
            "MintToChecked": self.handle_mint_to_checked,
            "MintTo": self.handle_mint_to,
            "BurnChecked": self.handle_burn_checked,
            "Burn": self.handle_burn,

            # Closing & Freezing
            "CloseAccount": self.handle_close_account,
            "FreezeAccount": self.handle_freeze_account,
            "ThawAccount": self.handle_thaw_account,

            # Native
            "SyncNative": self.handle_sync_native,
        }

    def parse_instruction(self, log: str) -> None:
        """
        Parses the log string and dispatches it to the appropriate handler.

        :param log: Log string containing instruction information.
        """
        for instruction, handler in self.handlers.items():
            if instruction in log:
                # log_info(f"Detected {instruction} instruction.")
                handler(log)
                return

        if "Instruction" in log:
            log_info(log)
        else:
            pass
            # log_info(f"Unhandled log detected: {log}")

    # Instruction Handlers
    def _extract_detail(self, log: str, detail_name: str) -> str:
        """
        Helper function to extract specific details from the log string.

        :param log: Log string to parse.
        :param detail_name: The name of the detail to extract.
        :return: Extracted detail as a string.
        """
        # Example logic to extract detail (adjust pattern as needed)
        
        # pattern = fr"{detail_name}: ([a-zA-Z0-9]+)"
        # match = re.search(pattern, log)
        # return match.group(1) if match else "Unknown"
        return "Unknown"

    def handle_initialize_mint(self, log: str) -> None:
        log_info("Handling InitializeMint logic...")
        return
        # Extract mint authority and decimals
        # mint_authority = self._extract_detail(log, "MintAuthority")
        # decimals = self._extract_detail(log, "Decimals")
        # log_info(f"Mint initialized with authority {mint_authority} and {decimals} decimals")

    def handle_initialize_mint2(self, log: str) -> None:
        return
        log_info("Handling InitializeMint2 logic...")
        # TODO: Add your custom logic here

    def handle_initialize_account(self, log: str) -> None:
        return
        log_info("Handling InitializeAccount logic...")
        # TODO: Add your custom logic here

    def handle_initialize_account2(self, log: str) -> None:
        return
        log_info("Handling InitializeAccount2 logic...")
        # TODO: Add your custom logic here

    def handle_initialize_account3(self, log: str) -> None:
        return
        log_info("Handling InitializeAccount3 logic...")
        # TODO: Add your custom logic here

    def handle_initialize_multisig(self, log: str) -> None:
        return
        log_info("Handling InitializeMultisig logic...")
        # TODO: Add your custom logic here

    def handle_initialize_multisig2(self, log: str) -> None:
        return
        log_info("Handling InitializeMultisig2 logic...")
        # TODO: Add your custom logic here

    def handle_transfer(self, log: str) -> None:
        return
        log_info("Handling Transfer logic...")
        # TODO: Add your custom logic here

    def handle_transfer_checked(self, log: str) -> None:
        return
        log_info("Handling TransferChecked logic...")
        # TODO: Add your custom logic here

    def handle_approve(self, log: str) -> None:
        return
        log_info("Handling Approve logic...")
        # TODO: Add your custom logic here

    def handle_approve_checked(self, log: str) -> None:
        return
        log_info("Handling ApproveChecked logic...")
        # TODO: Add your custom logic here

    def handle_revoke(self, log: str) -> None:
        return
        log_info("Handling Revoke logic...")
        # TODO: Add your custom logic here

    def handle_set_authority(self, log: str) -> None:
        return
        log_info("Handling SetAuthority logic...")
        # TODO: Add your custom logic here

    def handle_mint_to(self, log: str) -> None:
        return
        log_info("Handling MintTo logic...")
        # TODO: Add your custom logic here

    def handle_mint_to_checked(self, log: str) -> None:
        return
        log_info("Handling MintToChecked logic...")
        # TODO: Add your custom logic here

    def handle_burn(self, log: str) -> None:
        return
        log_info("Handling Burn logic...")
        # TODO: Add your custom logic here

    def handle_burn_checked(self, log: str) -> None:
        return
        log_info("Handling BurnChecked logic...")
        # TODO: Add your custom logic here

    def handle_close_account(self, log: str) -> None:
        return
        log_info("Handling CloseAccount logic...")
        # TODO: Add your custom logic here

    def handle_freeze_account(self, log: str) -> None:
        return
        log_info("Handling FreezeAccount logic...")
        # TODO: Add your custom logic here

    def handle_thaw_account(self, log: str) -> None:
        return
        log_info("Handling ThawAccount logic...")
        # TODO: Add your custom logic here

    def handle_sync_native(self, log: str) -> None:
        return
        log_info("Handling SyncNative logic...")
        # TODO: Add your custom logic here