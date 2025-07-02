import os
import json
import time
import asyncio
import logging
from typing import List, Dict, Any, Optional

import requests
from dotenv import load_dotenv
from web3 import Web3
from web3.exceptions import BlockNotFound
from web3.types import LogReceipt

# --- Basic Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('CrossChainBridgeListener')

# --- Constants ---
# A simplified ABI for a hypothetical bridge contract.
# In a real-world scenario, this would be loaded from a JSON file.
BRIDGE_CONTRACT_ABI = json.loads('''
[
    {
        "anonymous": false,
        "inputs": [
            {
                "indexed": true,
                "internalType": "address",
                "name": "sender",
                "type": "address"
            },
            {
                "indexed": true,
                "internalType": "address",
                "name": "recipient",
                "type": "address"
            },
            {
                "indexed": false,
                "internalType": "uint256",
                "name": "amount",
                "type": "uint256"
            },
            {
                "indexed": false,
                "internalType": "uint256",
                "name": "destinationChainId",
                "type": "uint256"
            },
            {
                "indexed": false,
                "internalType": "bytes32",
                "name": "transactionId",
                "type": "bytes32"
            }
        ],
        "name": "TokensLocked",
        "type": "event"
    }
]
''')

class Config:
    """
    Configuration manager for loading settings from environment variables.
    This class centralizes access to configuration parameters, making the application
    easier to manage and configure for different environments (dev, staging, prod).
    """
    def __init__(self):
        load_dotenv()
        self.source_rpc_url: str = self._get_env_var('SOURCE_CHAIN_RPC_URL')
        self.source_bridge_address: str = self._get_env_var('SOURCE_CHAIN_BRIDGE_ADDRESS')
        self.destination_rpc_url: str = self._get_env_var('DESTINATION_CHAIN_RPC_URL')
        self.destination_bridge_address: str = self._get_env_var('DESTINATION_CHAIN_BRIDGE_ADDRESS')
        self.validator_private_key: str = self._get_env_var('VALIDATOR_PRIVATE_KEY')
        self.start_block: int = int(self._get_env_var('START_BLOCK', '0'))
        self.scan_interval_seconds: int = int(self._get_env_var('SCAN_INTERVAL_SECONDS', '10'))
        self.block_scan_range: int = int(self._get_env_var('BLOCK_SCAN_RANGE', '100'))
        self.state_file_path: str = self._get_env_var('STATE_FILE_PATH', 'listener_state.json')

    def _get_env_var(self, key: str, default: Optional[str] = None) -> str:
        """Helper to fetch an environment variable and raise an error if not found."""
        value = os.getenv(key, default)
        if value is None:
            raise ValueError(f'Environment variable {key} is not set.')
        return value


class BlockchainConnector:
    """
    Manages the connection to a single blockchain node via Web3.py.
    It encapsulates the Web3 instance and contract objects, providing a clean
    interface for interacting with a specific chain.
    """
    def __init__(self, rpc_url: str, contract_address: str):
        self.rpc_url = rpc_url
        self.contract_address = Web3.to_checksum_address(contract_address)
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))

        if not self.w3.is_connected():
            raise ConnectionError(f'Failed to connect to blockchain node at {self.rpc_url}')

        self.contract = self.w3.eth.contract(
            address=self.contract_address,
            abi=BRIDGE_CONTRACT_ABI
        )
        logger.info(f'Successfully connected to {self.w3.eth.chain_id} and loaded contract at {self.contract_address}')

    def get_latest_block(self) -> int:
        """Fetches the latest block number from the connected node."""
        return self.w3.eth.block_number


class EventScanner:
    """
    Scans a given range of blocks for specific smart contract events.
    This class is responsible for the core logic of fetching and parsing event logs,
    handling potential RPC errors, and managing scanning ranges to avoid overloading the node.
    """
    def __init__(self, connector: BlockchainConnector, block_scan_range: int):
        self.connector = connector
        self.block_scan_range = block_scan_range

    async def scan_for_events(self, from_block: int, to_block: int) -> List[LogReceipt]:
        """
        Scans a block range for 'TokensLocked' events and returns a list of decoded logs.
        
        Args:
            from_block: The starting block number for the scan.
            to_block: The ending block number for the scan.

        Returns:
            A list of event logs, each parsed into a dictionary-like object.
        """
        logger.info(f'Scanning for events from block {from_block} to {to_block}')
        try:
            event_filter = self.connector.contract.events.TokensLocked.create_filter(
                fromBlock=from_block,
                toBlock=to_block
            )
            events = event_filter.get_all_entries()
            if events:
                logger.info(f'Found {len(events)} new TokensLocked events.')
            return events
        except BlockNotFound:
            logger.warning(f'Block range [{from_block}-{to_block}] not found. The node may not be fully synced.')
            return []
        except requests.exceptions.ReadTimeout:
            logger.error('RPC node request timed out. Will retry on the next cycle.')
            return []
        except Exception as e:
            logger.error(f'An unexpected error occurred during event scanning: {e}')
            return []


class EventHandler:
    """
    Processes events captured by the EventScanner.
    This class simulates the validation and transaction submission on the destination chain.
    In a real system, this would involve cryptographic signing, nonce management,
    and robust transaction submission logic with gas estimation.
    """
    def __init__(self, destination_connector: BlockchainConnector, validator_private_key: str):
        self.destination_connector = destination_connector
        self.validator_account = self.destination_connector.w3.eth.account.from_key(validator_private_key)
        logger.info(f'Event handler initialized for validator address: {self.validator_account.address}')

    async def process_event(self, event: LogReceipt) -> bool:
        """
        Processes a single 'TokensLocked' event.

        This is a simulation. It will:
        1. Log the event details.
        2. Simulate calling an external API for extra validation (e.g., risk scoring).
        3. Simulate building and signing a transaction for the destination chain.

        Args:
            event: The event log to process.

        Returns:
            True if processing was successful, False otherwise.
        """
        event_args = event['args']
        tx_hash = event['transactionHash'].hex()
        logger.info(f'Processing event from transaction {tx_hash}: {event_args}')

        # --- 1. External Validation Simulation ---
        # In a real bridge, you might call an oracle or a risk assessment API.
        try:
            # Mock API call
            validation_api_url = f'https://api.example.com/validate/{tx_hash}'
            # response = requests.get(validation_api_url, timeout=10) 
            # if response.status_code != 200 or not response.json().get('isValid'):
            #     logger.error(f'External validation failed for {tx_hash}. Skipping.')
            #     return False
            logger.info(f'Simulated external validation successful for {tx_hash}')
        except requests.exceptions.RequestException as e:
            logger.error(f'Failed to call validation API for {tx_hash}: {e}. Will retry later.')
            return False # Indicate failure to retry this event

        # --- 2. Destination Chain Transaction Simulation ---
        # Build and sign a transaction to mint tokens on the destination chain.
        # This part is a simulation and does not actually send a transaction.
        try:
            dest_contract = self.destination_connector.contract
            
            # In a real scenario, you'd call a 'mint' or 'unlock' function
            # Here we just log the intent
            logger.info(f'Preparing to mint {event_args.amount} tokens for {event_args.recipient} on chain {self.destination_connector.w3.eth.chain_id}')

            # nonce = self.destination_connector.w3.eth.get_transaction_count(self.validator_account.address)
            # tx_params = {
            #     'from': self.validator_account.address,
            #     'nonce': nonce,
            #     'gas': 200000, # This should be estimated
            #     'gasPrice': self.destination_connector.w3.eth.gas_price, # This should be dynamic
            # }
            # transaction = dest_contract.functions.mint(event_args.recipient, event_args.amount).build_transaction(tx_params)
            # signed_tx = self.destination_connector.w3.eth.account.sign_transaction(transaction, self.validator_private_key)
            # tx_receipt = self.destination_connector.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            # logger.info(f'Successfully submitted transaction to destination chain. Hash: {tx_receipt.hex()}')
            
            await asyncio.sleep(1) # Simulate network latency
            logger.info(f'[SIMULATION] Transaction for event {tx_hash} would have been signed and sent.')
            return True
        except Exception as e:
            logger.error(f'Failed to build or sign destination transaction for event {tx_hash}: {e}')
            return False


class CrossChainBridgeListener:
    """
    The main orchestrator for the bridge event listener.
    It initializes all components, manages the main processing loop, and handles
    persistent state for the last scanned block.
    """
    def __init__(self, config: Config):
        self.config = config
        self.source_connector = BlockchainConnector(config.source_rpc_url, config.source_bridge_address)
        self.destination_connector = BlockchainConnector(config.destination_rpc_url, config.destination_bridge_address)
        self.event_scanner = EventScanner(self.source_connector, config.block_scan_range)
        self.event_handler = EventHandler(self.destination_connector, config.validator_private_key)
        self.last_scanned_block = self._load_state()

    def _load_state(self) -> int:
        """Loads the last scanned block number from a file."""
        try:
            with open(self.config.state_file_path, 'r') as f:
                state = json.load(f)
                last_block = int(state.get('last_scanned_block', self.config.start_block))
                logger.info(f'Loaded state: last scanned block is {last_block}')
                return last_block
        except (FileNotFoundError, json.JSONDecodeError):
            logger.warning('State file not found or invalid. Starting from configured start_block.')
            return self.config.start_block

    def _save_state(self):
        """Saves the last scanned block number to a file."""
        with open(self.config.state_file_path, 'w') as f:
            json.dump({'last_scanned_block': self.last_scanned_block}, f)

    async def run(self):
        """The main execution loop of the listener."""
        logger.info('Starting cross-chain bridge listener...')
        while True:
            try:
                latest_block = self.source_connector.get_latest_block()
                if self.last_scanned_block >= latest_block:
                    logger.info(f'No new blocks to scan. Current: {latest_block}. Sleeping...')
                    await asyncio.sleep(self.config.scan_interval_seconds)
                    continue

                # Define the range for the current scan iteration
                from_block = self.last_scanned_block + 1
                to_block = min(from_block + self.config.block_scan_range - 1, latest_block)

                events = await self.event_scanner.scan_for_events(from_block, to_block)

                for event in events:
                    success = await self.event_handler.process_event(event)
                    if not success:
                        logger.error(f'Failed to process event in tx {event.transactionHash.hex()}. Will retry from block {from_block}.')
                        # In a real scenario, you'd have more sophisticated retry logic,
                        # perhaps putting the failed event into a queue.
                        # For this simulation, we stop and retry the whole block range next time.
                        await asyncio.sleep(self.config.scan_interval_seconds)
                        break # Exit the event loop to retry the block range
                else: # This 'else' belongs to the 'for' loop, executes if the loop completed without a 'break'
                    # If all events in the range were processed successfully, update state
                    self.last_scanned_block = to_block
                    self._save_state()

                # If we are far behind the head of the chain, continue immediately
                if to_block < latest_block:
                    continue

            except ConnectionError as e:
                logger.critical(f'Connection error: {e}. Retrying in 60 seconds.')
                await asyncio.sleep(60)
            except Exception as e:
                logger.critical(f'An uncaught exception occurred in the main loop: {e}', exc_info=True)
                await asyncio.sleep(self.config.scan_interval_seconds)

            await asyncio.sleep(self.config.scan_interval_seconds)

async def main():
    """Main entry point of the script."""
    try:
        config = Config()
        listener = CrossChainBridgeListener(config)
        await listener.run()
    except ValueError as e:
        logger.critical(f'Configuration error: {e}')
    except Exception as e:
        logger.critical(f'Failed to initialize the listener: {e}', exc_info=True)

if __name__ == '__main__':
    asyncio.run(main())
