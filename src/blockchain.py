import time
from block import Block

class Blockchain:
    def __init__(self):
        self.chain = [self.create_genesis_block()]
        self.pending_transactions = []

    def create_genesis_block(self):
        """Creates the genesis block."""
        return Block(0, "0", [], timestamp=0)

    def get_latest_block(self):
        """Returns the latest block in the chain."""
        return self.chain[-1]

    def add_block(self, new_block):
        """Adds a new block to the chain after validation."""
        new_block.previous_hash = self.get_latest_block().hash
        new_block.hash = new_block.calculate_hash()
        self.chain.append(new_block)

    def is_chain_valid(self):
        """Checks if the blockchain is valid."""
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i - 1]

            # Recalculate hash to verify integrity
            if current_block.hash != current_block.calculate_hash():
                return False

            # Check if previous hash reference is correct
            if current_block.previous_hash != previous_block.hash:
                return False

        return True

    def create_new_transaction(self, sender, recipient, amount):
        """Creates a new transaction to go into the next mined block."""
        transaction = {
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
            'timestamp': time.time()
        }
        self.pending_transactions.append(transaction)
        return self.get_latest_block().index + 1
