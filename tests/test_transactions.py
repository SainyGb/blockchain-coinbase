import unittest
import sys
import os
import time

# Add src to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from blockchain import Blockchain
from transaction import Transaction
from block import Block

class TestTransaction(unittest.TestCase):
    def setUp(self):
        self.blockchain = Blockchain()
        # Genesis block has no funds. Fund 'admin' manually for tests.
        # Create a mock block with a coinbase-like transaction
        fund_tx = Transaction("coinbase", "admin", 100)
        # We need a valid block structure but for get_balance iteration it just needs to be in chain
        # and contain the transaction.
        funding_block = Block(1, self.blockchain.get_latest_block().hash, [fund_tx], timestamp=time.time())
        funding_block.mine_block(self.blockchain.difficulty)
        self.blockchain.add_block(funding_block)

    def test_transaction_creation(self):
        """Test creating a valid transaction."""
        # 'admin' has 100
        tx = self.blockchain.create_new_transaction("admin", "user1", 10)
        self.assertIsNotNone(tx)
        self.assertEqual(len(self.blockchain.pending_transactions), 1)
        self.assertEqual(self.blockchain.get_balance("admin"), 90) # 100 - 10 pending

    def test_insufficient_balance(self):
        """Test creating a transaction with insufficient funds."""
        # 'user1' has 0
        tx = self.blockchain.create_new_transaction("user1", "user2", 10)
        self.assertIsNone(tx)
        self.assertEqual(len(self.blockchain.pending_transactions), 0)

    def test_negative_amount(self):
        """Test creating a transaction with negative amount."""
        tx = self.blockchain.create_new_transaction("admin", "user1", -10)
        self.assertIsNone(tx)
    
    def test_add_block_clears_pending(self):
        """Test that adding a block removes transactions from pending."""
        tx1 = self.blockchain.create_new_transaction("admin", "user1", 10)
        tx2 = self.blockchain.create_new_transaction("admin", "user2", 5)
        
        self.assertEqual(len(self.blockchain.pending_transactions), 2)
        
        # Mine block (simulate)
        prev_block = self.blockchain.get_latest_block()
        new_block = Block(1, prev_block.hash, [tx1, tx2])
        # Mine to satisfy difficulty
        new_block.mine_block(self.blockchain.difficulty)
        
        added = self.blockchain.add_block(new_block)
        self.assertTrue(added)
        
        self.assertEqual(len(self.blockchain.pending_transactions), 0)
        self.assertEqual(self.blockchain.get_balance("user1"), 10)
        self.assertEqual(self.blockchain.get_balance("user2"), 5)
        self.assertEqual(self.blockchain.get_balance("admin"), 85)

if __name__ == '__main__':
    unittest.main()
