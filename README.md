# Cross-Chain Bridge Event Listener

This repository, `common-lib`, contains a simulation of a crucial component for a decentralized cross-chain bridge: an event listener. This Python script is designed to monitor a smart contract on a source blockchain (e.g., Ethereum), detect specific events (`TokensLocked`), and simulate the process of triggering a corresponding action on a destination blockchain (e.g., Polygon).

## Concept

A cross-chain bridge allows users to transfer assets or data from one blockchain to another. A common pattern is the "lock-and-mint" mechanism:

1.  **Lock**: A user locks their tokens in a bridge contract on the source chain.
2.  **Event Emission**: The bridge contract emits an event (e.g., `TokensLocked`) containing details of the deposit (sender, recipient, amount, destination chain).
3.  **Validation**: A network of validators listens for this event. They verify its legitimacy.
4.  **Mint**: Upon successful validation, the validators collectively sign a message authorizing a corresponding bridge contract on the destination chain to mint an equivalent amount of "wrapped" tokens for the recipient.

This script plays the role of a **validator node's listening component**. It is responsible for Step 3 and the initiation of Step 4.

## Code Architecture

The script is designed with a clear separation of concerns, using several classes to handle different aspects of the process. This makes the system modular, testable, and easier to maintain.

-   `Config`: Manages all configuration loaded from a `.env` file. This includes RPC endpoints, contract addresses, private keys, and operational parameters. It centralizes configuration and prevents hardcoding sensitive information.

-   `BlockchainConnector`: A wrapper around the `web3.py` library that handles the connection to a specific blockchain node. It initializes the `Web3` instance and the contract object, providing a clean interface for interaction.

-   `EventScanner`: The core logic for monitoring the blockchain. It uses a `BlockchainConnector` instance to scan ranges of blocks for the target event (`TokensLocked`). It's designed to handle RPC node limitations by scanning in manageable chunks (`BLOCK_SCAN_RANGE`).

-   `EventHandler`: Responsible for processing the events found by the `EventScanner`. In this simulation, it logs event details, simulates a call to an external validation API (e.g., for risk analysis), and prepares the corresponding transaction that would be sent to the destination chain. This class encapsulates the "business logic" of the bridge.

-   `CrossChainBridgeListener`: The main orchestrator class. It initializes all the other components, manages the main execution loop, and handles state persistence (i.e., saving and loading the last block number it successfully scanned) to ensure events are not missed or processed twice upon restart.

### Data Flow

1.  `CrossChainBridgeListener` starts its main loop.
2.  It determines the block range to scan based on its saved state (`last_scanned_block`) and the latest block on the source chain.
3.  It calls `EventScanner.scan_for_events()` with this range.
4.  `EventScanner` queries the source chain's RPC node for `TokensLocked` event logs.
5.  If events are found, `CrossChainBridgeListener` iterates through them, passing each one to `EventHandler.process_event()`.
6.  `EventHandler` simulates validation and the creation of a minting transaction for the destination chain.
7.  If all events in the block range are processed successfully, `CrossChainBridgeListener` updates `last_scanned_block` and saves the new state to a file.
8.  The loop waits for a configured interval and repeats.

## How it Works

### State Management

To ensure resilience, the listener needs to remember where it left off. It achieves this by storing the block number of the last successfully processed block in a JSON file (`listener_state.json` by default). When the script starts, it reads this file to determine where to resume scanning. This prevents processing the same event multiple times after a restart and ensures no events are missed during downtime.

### Event Scanning

Instead of querying for events on every new block, the listener operates in cycles. In each cycle, it gets the latest block number from the node and scans a range of blocks from its last known position up to the latest block. To avoid overwhelming the RPC node with requests for a huge number of blocks (if the listener has been offline for a while), it processes the backlog in smaller, configurable chunks (`BLOCK_SCAN_RANGE`).

### Error Handling

-   **Connection Errors**: The script is wrapped in `try...except` blocks to catch RPC connection errors. If a connection fails, it will log the error and retry after a delay.
-   **Configuration Errors**: The script will fail on startup with a clear message if any required environment variables are missing.
-   **Event Processing Failures**: If the `EventHandler` fails to process an event (e.g., the simulated validation API call fails), it returns `False`. The main loop detects this, stops processing further events in the current batch, and does *not* update the `last_scanned_block`. This ensures that the entire block range containing the failed event will be retried in the next cycle.

## Usage Example

### 1. Prerequisites

-   Python 3.8+
-   Access to RPC URLs for two EVM-compatible blockchains (e.g., from Infura, Alchemy, or a local node). For testing, you can use public testnets like Sepolia and Mumbai.

### 2. Setup

Clone the repository and install the required dependencies.

```bash
# It is recommended to use a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`

pip install -r requirements.txt
```

### 3. Configuration

Create a `.env` file in the root directory of the project and populate it with your specific details. Use the following template:

```env
# --- Source Chain (e.g., Ethereum Sepolia) ---
SOURCE_CHAIN_RPC_URL="https://sepolia.infura.io/v3/YOUR_INFURA_PROJECT_ID"
SOURCE_CHAIN_BRIDGE_ADDRESS="0x..."

# --- Destination Chain (e.g., Polygon Mumbai) ---
DESTINATION_CHAIN_RPC_URL="https://polygon-mumbai.infura.io/v3/YOUR_INFURA_PROJECT_ID"
DESTINATION_CHAIN_BRIDGE_ADDRESS="0x..."

# --- Validator Wallet ---
# IMPORTANT: Use a key for a test wallet with no real funds for this simulation.
VALIDATOR_PRIVATE_KEY="0x..."

# --- Operational Settings ---
# The block to start scanning from if no state file is found.
START_BLOCK="0"
# How often (in seconds) to check for new blocks.
SCAN_INTERVAL_SECONDS="15"
# Max number of blocks to scan in a single RPC call.
BLOCK_SCAN_RANGE="500"
# File path to store the last scanned block number.
STATE_FILE_PATH="listener_state.json"
```

**Note**: You will need to replace `YOUR_INFURA_PROJECT_ID` and the `0x...` addresses and private key with actual values.

### 4. Running the Listener

Once the `requirements.txt` are installed and the `.env` file is configured, you can run the script:

```bash
python script.py
```

You will see log output in your terminal as the listener connects to the chains, scans for blocks, and processes events.

```
2023-10-27 14:30:00 - INFO - CrossChainBridgeListener - Loaded state: last scanned block is 123456
2023-10-27 14:30:01 - INFO - CrossChainBridgeListener - Starting cross-chain bridge listener...
2023-10-27 14:30:02 - INFO - EventScanner - Scanning for events from block 123457 to 123556
...
```
