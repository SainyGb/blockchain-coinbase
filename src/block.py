import hashlib
import json
import time
# transaction import might be missing if I replaced the top part badly. Let me check.
from transaction import Transaction

class Block:
    def __init__(self, index, previous_hash, transactions, nonce=0, timestamp=None):
        self.index = index
        self.previous_hash = previous_hash
        self.transactions = transactions
        self.nonce = nonce
        self.timestamp = timestamp if timestamp is not None else time.time()
        self.hash = self.calculate_hash()

    def mine_block(self, difficulty):
        """Mines the block by finding a nonce that results in a hash starting with 'difficulty' zeros."""
        target = "0" * difficulty
        while self.hash[:difficulty] != target:
            self.nonce += 1
            self.hash = self.calculate_hash()
            
    def calculate_hash(self):
        """Calculates the SHA-256 hash of the block content."""
        # Convert transactions to list of dicts for hashing consistency
        safe_txs = []
        for tx in self.transactions:
            if isinstance(tx, Transaction):
                safe_txs.append(tx.to_dict())
            elif hasattr(tx, 'to_dict'):
                safe_txs.append(tx.to_dict())
            else:
                safe_txs.append(tx) # Strings or dicts

        block_content = {
            "index": self.index,
            "previous_hash": self.previous_hash,
            "transactions": safe_txs,
            "nonce": self.nonce,
            "timestamp": self.timestamp
        }
        block_string = json.dumps(block_content, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    def to_dict(self):
        """Returns the block as a dictionary."""
        safe_txs = []
        for tx in self.transactions:
            if isinstance(tx, Transaction):
                safe_txs.append(tx.to_dict())
            else:
                safe_txs.append(tx)

        return {
            "index": self.index,
            "previous_hash": self.previous_hash,
            "transactions": safe_txs,
            "nonce": self.nonce,
            "timestamp": self.timestamp,
            "hash": self.hash
        }

    @staticmethod
    def from_dict(data):
        """Creates a Block instance from a dictionary."""
        transactions = []
        for tx_data in data["transactions"]:
            if isinstance(tx_data, dict):
                transactions.append(Transaction.from_dict(tx_data))
            else:
                transactions.append(tx_data)

        block = Block(
            index=data["index"],
            previous_hash=data["previous_hash"],
            transactions=transactions,
            nonce=data["nonce"],
            timestamp=data["timestamp"]
        )
        block.hash = data["hash"]
        return block
