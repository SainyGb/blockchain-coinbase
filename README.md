# Blockchain Coinbase

Implementation of a simplified distributed cryptocurrency/transaction system (Bitcoin-like) for the LSD 2025 course.

## Requirements
- Python 3.8+

## Usage

### Start a Node
To start a node, use the `src/main.py` script.

```bash
python3 src/main.py --port <PORT> [--bootstrap <HOST:PORT>]
```

Example:
```bash
# Start the first node (bootstrap node)
python3 src/main.py --port 5000

# Start a second node connecting to the first one
python3 src/main.py --port 5001 --bootstrap localhost:5000
```

## Running Tests
To run the communication tests:

```bash
python3 tests/test_communication.py
```

## Structure
- `src/node.py`: Core `Node` class handling networking.
- `src/main.py`: Entry point for the CLI.
- `tests/`: Unit and integration tests.
