import unittest
import sys
import os
import time
import json
import threading

# Add src to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from node import Node
from transaction import Transaction
from block import Block

class TestMining(unittest.TestCase):
    def setUp(self):
        self.host = 'localhost'
        self.node_a = Node(self.host, 5020)
        self.node_b = Node(self.host, 5021)
        self.node_a.peers.add(('localhost', 5021))
        self.node_b.peers.add(('localhost', 5020))

    def tearDown(self):
        self.node_a.stop()
        self.node_b.stop()

    def test_mining_and_propagation(self):
        """Test that Node A mines a block and Node B receives it."""
        self.node_a.start()
        self.node_b.start()
        time.sleep(1)

        # Create a transaction on A so it has something to mine
        tx = Transaction("admin", "user1", 10)
        self.node_a.blockchain.add_transaction(tx)
        
        # Start mining on A
        self.node_a.start_mining()
        
        # Wait for block to be mined (difficulty 3 is fast)
        # Check Node A chain length
        start_time = time.time()
        while len(self.node_a.blockchain.chain) == 1:
            if time.time() - start_time > 10:
                self.fail("Timed out waiting for block mining")
            time.sleep(0.5)
            
        self.assertEqual(len(self.node_a.blockchain.chain), 2)
        
        # Wait for propagation to B
        time.sleep(2)
        self.assertEqual(len(self.node_b.blockchain.chain), 2, "Node B did not receive the block")
        
        # Verify transaction is in the block on B
        latest_block_b = self.node_b.blockchain.get_latest_block()
        # Transaction might be in dict form or object form depending on deserialization.
        # Check ID.
        tx_found = False
        for t in latest_block_b.transactions:
            t_id = t.id if isinstance(t, Transaction) else t['id']
            if t_id == tx.id:
                tx_found = True
                break
        self.assertTrue(tx_found, "Transaction not found in propagated block")

if __name__ == '__main__':
    unittest.main()
