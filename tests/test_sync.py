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

class TestSynchronization(unittest.TestCase):
    def setUp(self):
        self.host = 'localhost'
        self.node_a = Node(self.host, 5030)
        self.node_b = Node(self.host, 5031)
        # B knows A
        self.node_b.peers.add(('localhost', 5030))
        # A knows B (so A can send to B)
        self.node_a.peers.add(('localhost', 5031))

    def tearDown(self):
        self.node_a.stop()
        self.node_b.stop()

    def test_sync_on_connect(self):
        """Test that Node B syncs with Node A upon connection."""
        # Use different ports to avoid conflict with other test if cleanup fails
        node_a = Node(self.host, 5032)
        node_b = Node(self.host, 5033)
        node_b.peers.add(('localhost', 5032))
        node_a.peers.add(('localhost', 5033))
        
        try:
            # 1. Start Node A and mine some blocks
            node_a.start()
            time.sleep(1)
            
            # Mine block 1
            tx1 = Transaction("admin", "user1", 10)
            node_a.blockchain.add_transaction(tx1)
            node_a.start_mining()
            
            while len(node_a.blockchain.chain) < 2:
                time.sleep(0.1)
                
            # Mine block 2
            tx2 = Transaction("admin", "user2", 10)
            node_a.blockchain.add_transaction(tx2)
            # Mining loop should pick it up
            
            start_time = time.time()
            while len(node_a.blockchain.chain) < 3:
                if time.time() - start_time > 10:
                    self.fail("Node A failed to mine 2nd block")
                time.sleep(0.5)
            node_a.stop_mining()
            
            # 2. Start Node B
            node_b.start()
            
            # Wait for sync
            time.sleep(3)
            
            # Check
            self.assertEqual(len(node_b.blockchain.chain), len(node_a.blockchain.chain))
            self.assertEqual(node_b.blockchain.get_latest_block().hash, node_a.blockchain.get_latest_block().hash)
        finally:
            node_a.stop()
            node_b.stop()

    def test_conflict_resolution(self):
        """Test that Node B switches to a longer chain from Node A."""
        # 1. Start both nodes
        self.node_a.start()
        self.node_b.start()
        time.sleep(1)
        
        # 2. Disconnect them logically (or just ensure they don't sync automatically yet)
        # Actually they are connected.
        # Let's mine 1 block on B first.
        tx_b = Transaction("coinbase", "user2", 5)
        self.node_b.blockchain.add_transaction(tx_b)
        self.node_b.start_mining()
        
        while len(self.node_b.blockchain.chain) < 2:
            time.sleep(0.1)
        self.node_b.stop_mining()
        
        # 3. Mine 2 blocks on A (making it longer)
        tx_a1 = Transaction("coinbase", "user1", 10)
        self.node_a.blockchain.add_transaction(tx_a1)
        self.node_a.start_mining()
        
        while len(self.node_a.blockchain.chain) < 3:
            time.sleep(0.1)
        self.node_a.stop_mining()
        
        # Now A has length 3, B has length 2.
        
        self.node_b.broadcast_message('REQUEST_CHAIN', {'port': 5031})
        time.sleep(2)
        
        # B should have switched to A's chain
        self.assertGreaterEqual(len(self.node_b.blockchain.chain), 3)
        # Check that B's tip is valid (it should be equal to A's tip or A's chain should contain it)
        # A might have mined more.
        # But B synced from A. So B's tip should be A's tip (at sync time) or A's tip (now).
        # Let's check consistency.
        self.assertEqual(self.node_b.blockchain.get_latest_block().hash, self.node_a.blockchain.chain[len(self.node_b.blockchain.chain)-1].hash)

if __name__ == '__main__':
    unittest.main()
