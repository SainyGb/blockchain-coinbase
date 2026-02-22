import unittest
import sys
import os
import time

# Add src to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from node import Node
from block import Block

class TestNodeBlockchain(unittest.TestCase):
    def setUp(self):
        self.node = Node('localhost', 5002)

    def tearDown(self):
        self.node.stop()

    def test_node_has_blockchain(self):
        """Test if the node initializes with a blockchain containing the genesis block."""
        self.assertIsNotNone(self.node.blockchain)
        self.assertEqual(len(self.node.blockchain.chain), 1)
        self.assertEqual(self.node.blockchain.chain[0].index, 0)

    def test_node_add_block_locally(self):
        """Test adding a block to the node's blockchain directly."""
        # Create a valid block manually (mocking mining)
        prev_block = self.node.blockchain.get_latest_block()
        new_block = Block(1, prev_block.hash, ["tx1"])
        new_block.mine_block(self.node.blockchain.difficulty)
        
        self.node.blockchain.add_block(new_block)
        
        self.assertEqual(len(self.node.blockchain.chain), 2)
        self.assertTrue(self.node.blockchain.is_chain_valid())

if __name__ == '__main__':
    unittest.main()
