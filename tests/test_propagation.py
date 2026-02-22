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

class TestTransactionPropagation(unittest.TestCase):
    def setUp(self):
        self.host = 'localhost'
        self.node_a = Node(self.host, 5010)
        self.node_b = Node(self.host, 5011)
        self.node_c = Node(self.host, 5012)
        
        # Configure topology: A -> B -> C
        self.node_a.peers.add(('localhost', 5011))
        self.node_b.peers.add(('localhost', 5012))

    def tearDown(self):
        self.node_a.stop()
        self.node_b.stop()
        self.node_c.stop()

    def test_propagation(self):
        """Test that a transaction created on Node A reaches Node C via Node B."""
        # Start nodes in reverse order to ensure listeners are ready
        self.node_c.start()
        time.sleep(0.5)
        self.node_b.start()
        time.sleep(0.5)
        self.node_a.start()
        time.sleep(1)
        
        # Create transaction from 'coinbase' (bypass balance check for test)
        tx = Transaction("coinbase", "user1", 10)
        
        # Add to A locally
        added = self.node_a.blockchain.add_transaction(tx)
        self.assertTrue(added)
        
        # Broadcast from A (simulating A receiving it from client)
        self.node_a.broadcast_message('NEW_TRANSACTION', {'transaction': tx.to_dict()})
        
        # Wait for propagation
        time.sleep(2)
        
        # Check Node B
        self.assertEqual(len(self.node_b.blockchain.pending_transactions), 1, "Node B pending empty")
        self.assertEqual(self.node_b.blockchain.pending_transactions[0].id, tx.id)
        
        # Check Node C
        self.assertEqual(len(self.node_c.blockchain.pending_transactions), 1, "Node C pending empty")
        self.assertEqual(self.node_c.blockchain.pending_transactions[0].id, tx.id)

if __name__ == '__main__':
    unittest.main()
