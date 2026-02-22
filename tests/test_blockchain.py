import unittest
import sys
import os
import time

# Add src to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from block import Block
from blockchain import Blockchain

class TestBlockchain(unittest.TestCase):
    def setUp(self):
        self.blockchain = Blockchain()

    def test_genesis_block(self):
        """Test if the genesis block is created correctly."""
        genesis_block = self.blockchain.chain[0]
        self.assertEqual(genesis_block.index, 0)
        self.assertEqual(genesis_block.previous_hash, "0"*64)
        self.assertEqual(len(genesis_block.transactions), 0)

    def test_add_block(self):
        """Test adding a new block to the chain."""
        initial_length = len(self.blockchain.chain)
        prev_block = self.blockchain.get_latest_block()
        new_block = Block(1, prev_block.hash, ["tx1"], timestamp=time.time())
        
        # Mine block to satisfy difficulty
        # Assuming difficulty is 3 (default)
        new_block.mine_block(self.blockchain.difficulty)
        
        success = self.blockchain.add_block(new_block)
        self.assertTrue(success)
        
        self.assertEqual(len(self.blockchain.chain), initial_length + 1)
        self.assertEqual(self.blockchain.chain[-1].previous_hash, self.blockchain.chain[-2].hash)

    def test_chain_validity(self):
        """Test the chain validity check."""
        new_block = Block(1, self.blockchain.get_latest_block().hash, ["tx1"], timestamp=time.time())
        new_block.mine_block(self.blockchain.difficulty)
        
        success = self.blockchain.add_block(new_block)
        self.assertTrue(success)
        
        self.assertTrue(self.blockchain.is_chain_valid())

        # Tamper with the chain content but keep the old hash
        self.blockchain.chain[1].transactions = ["tampered_tx"]
        # The stored hash is still valid for the *original* content, but recalculated hash will differ.
        self.assertFalse(self.blockchain.is_chain_valid())

if __name__ == '__main__':
    unittest.main()
