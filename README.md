# Blockchain Coinbase

Implementation of a simplified distributed cryptocurrency/transaction system (Bitcoin-like).

## Requirements
- Python 3.8+

## Usage

### Start GUI
To start the graphical interface:

```bash
python3 src/gui.py
```
This allows configuring the node, viewing the blockchain, sending transactions, and mining interactively.
**Note:** You must start mining to earn coins (via Coinbase transactions) before you can send transactions.

## Running Tests
To run all tests:

```bash
python3 -m unittest discover tests
```

## Structure
- `src/node.py`: Core `Node` class handling networking and P2P logic.
- `src/blockchain.py`: Blockchain logic (chain, pending pool, validation).
- `src/block.py`: Block structure and hashing.
- `src/transaction.py`: Transaction structure and validation.
- `src/gui.py`: Tkinter GUI for interactive use.
- `src/main.py`: Entry point for the CLI.
- `tests/`: Unit and integration tests.