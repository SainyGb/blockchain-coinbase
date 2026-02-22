import hashlib
import json
import time

class Block:
    def __init__(self, index, previous_hash, transactions, nonce=0, timestamp=None):
        self.index = index
        self.previous_hash = previous_hash
        self.transactions = transactions
        self.nonce = nonce
        self.timestamp = timestamp if timestamp else time.time()
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        """Calculates the SHA-256 hash of the block content."""
        block_content = {
            "index": self.index,
            "previous_hash": self.previous_hash,
            "transactions": self.transactions,
            "nonce": self.nonce,
            "timestamp": self.timestamp
        }
        block_string = json.dumps(block_content, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    def to_dict(self):
        """Returns the block as a dictionary."""
        return {
            "index": self.index,
            "previous_hash": self.previous_hash,
            "transactions": self.transactions,
            "nonce": self.nonce,
            "timestamp": self.timestamp,
            "hash": self.hash
        }

    @staticmethod
    def from_dict(data):
        """Creates a Block instance from a dictionary."""
        block = Block(
            index=data["index"],
            previous_hash=data["previous_hash"],
            transactions=data["transactions"],
            nonce=data["nonce"],
            timestamp=data["timestamp"]
        )
        block.hash = data["hash"]
        return block
