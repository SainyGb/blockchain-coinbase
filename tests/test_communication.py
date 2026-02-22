import unittest
import threading
import socket
import json
import time
import sys
import os

# Add src to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from node import Node

class TestNodeCommunication(unittest.TestCase):
    def setUp(self):
        self.node_a_port = 5040
        self.node_b_port = 5041
        self.host = 'localhost'
        
        # Start Node A
        self.node_a = Node(self.host, self.node_a_port)
        self.node_a.start()
        
        # Start Node B with Node A as bootstrap
        self.node_b = Node(self.host, self.node_b_port, {(self.host, self.node_a_port)})
        self.node_b.start()
        
        # Give time for servers to start
        time.sleep(1)

    def tearDown(self):
        self.node_a.stop()
        self.node_b.stop()

    def test_send_receive_message(self):
        """Test sending a message from Node B to Node A."""
        test_message = {"content": "Hello Node A!"}
        
        # We need to spy on Node A's processing logic or check logs.
        # For simplicity, let's override _process_message temporarily or add a callback.
        received_messages = []
        
        original_process = self.node_a._process_message
        def spy_process(msg, addr):
            received_messages.append(msg)
            original_process(msg, addr)
            
        self.node_a._process_message = spy_process
        
        # Send message from B to A
        self.node_b.send_message(self.host, self.node_a_port, "TEST_MSG", test_message)
        
        # Wait for processing
        time.sleep(1)
        
        self.assertEqual(len(received_messages), 1)
        msg_obj = json.loads(received_messages[0])
        self.assertEqual(msg_obj['type'], "TEST_MSG")
        self.assertEqual(msg_obj['payload'], test_message)

if __name__ == '__main__':
    unittest.main()
