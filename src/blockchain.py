import time
import logging
from block import Block
from transaction import Transaction

# Configure logging (will reuse root logger if configured)
logger = logging.getLogger(__name__)

class Blockchain:
    def __init__(self, difficulty=3):
        self.chain = [self.create_genesis_block()]
        self.pending_transactions = []
        self.difficulty = difficulty
        self.mining_reward = 10  # Simplified mining reward

    def create_genesis_block(self):
        """Creates the genesis block."""
        # Genesis transaction to give initial supply to 'admin' for testing
        genesis_tx = Transaction("0", "admin", 100, timestamp=0)
        return Block(0, "0", [genesis_tx], timestamp=0)

    def get_latest_block(self):
        """Returns the latest block in the chain."""
        return self.chain[-1]

    def add_block(self, new_block):
        """Adds a new block to the chain after validation."""
        # Validate block structure
        last_hash = self.get_latest_block().hash
        if new_block.previous_hash != last_hash:
            logger.warning(f"Invalid previous hash. Expected {last_hash[:8]}, got {new_block.previous_hash[:8]}")
            return False
        
        # Verify hash integrity
        calculated_hash = new_block.calculate_hash()
        if calculated_hash != new_block.hash:
             logger.warning(f"Invalid hash integrity. Calculated {calculated_hash[:8]}, got {new_block.hash[:8]}")
             return False

        # Validate difficulty
        if new_block.hash[:self.difficulty] != "0" * self.difficulty:
            logger.warning(f"Invalid difficulty. Hash {new_block.hash[:8]} does not start with {'0'*self.difficulty}")
            return False

        self.chain.append(new_block)
        
        # Remove mined transactions from pending
        # Compare by ID to ensure we remove the correct transactions
        new_tx_ids = set(tx.id for tx in new_block.transactions if isinstance(tx, Transaction))
        self.pending_transactions = [
            tx for tx in self.pending_transactions 
            if tx.id not in new_tx_ids
        ]
        return True

    def is_chain_valid(self, chain=None):
        """Checks if the blockchain (or a given chain) is valid."""
        target_chain = chain if chain else self.chain
        
        # Check Genesis (only if checking external chain)
        if chain and target_chain[0].hash != self.create_genesis_block().hash:
            return False

        for i in range(1, len(target_chain)):
            current_block = target_chain[i]
            previous_block = target_chain[i - 1]

            if current_block.hash != current_block.calculate_hash():
                return False

            if current_block.previous_hash != previous_block.hash:
                return False
            
            # Check difficulty
            if current_block.hash[:self.difficulty] != "0" * self.difficulty:
                return False

        return True

    def replace_chain(self, new_chain):
        """Replaces the local chain with a new one if it's valid and longer."""
        if len(new_chain) <= len(self.chain):
            return False
            
        if not self.is_chain_valid(new_chain):
            return False
            
        # Replace chain
        self.chain = new_chain
        
        # Update pending transactions by removing those now confirmed
        confirmed_tx_ids = set()
        for block in self.chain:
            for tx in block.transactions:
                if isinstance(tx, Transaction):
                    confirmed_tx_ids.add(tx.id)
                elif isinstance(tx, dict):
                    confirmed_tx_ids.add(tx.get('id'))
                    
        self.pending_transactions = [
            tx for tx in self.pending_transactions 
            if tx.id not in confirmed_tx_ids
        ]
        
        return True

    def create_new_transaction(self, sender, recipient, amount):
        """Creates a new transaction, validates it, and adds to pending."""
        transaction = Transaction(sender, recipient, amount)
        
        if not self.add_transaction(transaction):
            return None
            
        return transaction

    def add_transaction(self, transaction):
        """Adds a received transaction to pending if valid."""
        if not transaction.is_valid():
            return False
            
        # Check if already exists in pending
        for tx in self.pending_transactions:
            if tx.id == transaction.id:
                return False

        # Check balance (skip check for '0' sender - coinbase)
        if transaction.sender != "0":
            if self.get_balance(transaction.sender) < transaction.amount:
                print(f"Insufficient balance for {transaction.sender}, balance: {self.get_balance(transaction.sender)}")
                return False
            
        self.pending_transactions.append(transaction)
        return True

    def get_balance(self, address):
        """Calculates the balance of an address."""
        balance = 0
        # Iterate over all blocks
        for block in self.chain:
            for tx in block.transactions:
                if isinstance(tx, Transaction):
                    if tx.sender == address:
                        balance -= tx.amount
                    if tx.recipient == address:
                        balance += tx.amount
                elif isinstance(tx, dict):
                    # Handle dicts (if any remain)
                    if tx.get('sender') == address:
                        balance -= tx.get('amount', 0)
                    if tx.get('recipient') == address:
                        balance += tx.get('amount', 0)
        
        # Check pending transactions (only subtract spending)
        for tx in self.pending_transactions:
            if tx.sender == address:
                balance -= tx.amount
        
        return balance

