import socket
import threading
import json
import logging
from blockchain import Blockchain

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Node:
    def __init__(self, host, port, bootstrap_nodes=None):
        self.host = host
        self.port = port
        self.peers = set()  # Set of (host, port) tuples
        if bootstrap_nodes:
            self.peers.update(bootstrap_nodes)
        self.running = False
        self.server_socket = None
        self.blockchain = Blockchain()


    def start(self):
        """Starts the node server and initiates connections to peers."""
        self.running = True
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        logging.info(f"Node started on {self.host}:{self.port}")

        # Start listening for incoming connections in a separate thread
        listen_thread = threading.Thread(target=self._listen_for_connections)
        listen_thread.daemon = True
        listen_thread.start()

        # Connect to known peers
        self._connect_to_peers()

    def _listen_for_connections(self):
        """Listens for incoming TCP connections."""
        while self.running:
            try:
                conn, addr = self.server_socket.accept()
                threading.Thread(target=self._handle_client, args=(conn, addr), daemon=True).start()
            except Exception as e:
                if self.running:
                    logging.error(f"Error accepting connection: {e}")

    def _handle_client(self, conn, addr):
        """Handles communication with a connected client."""
        logging.info(f"Connected to {addr}")
        with conn:
            buffer = ""
            while True:
                try:
                    data = conn.recv(1024).decode('utf-8')
                    if not data:
                        break
                    buffer += data
                    while '\\n' in buffer:
                        message, buffer = buffer.split('\\n', 1)
                        self._process_message(message, addr)
                except Exception as e:
                    logging.error(f"Error handling client {addr}: {e}")
                    break
        logging.info(f"Disconnected from {addr}")

    def _process_message(self, message_str, addr):
        """Processes a received message string."""
        try:
            message = json.loads(message_str)
            logging.info(f"Received message from {addr}: {message}")
            # Here we will add logic to handle specific message types later
        except json.JSONDecodeError:
            logging.error(f"Invalid JSON received from {addr}: {message_str}")

    def _connect_to_peers(self):
        """Connects to known peers."""
        for peer_host, peer_port in self.peers:
            if (peer_host, peer_port) == (self.host, self.port):
                continue
            logging.info(f"Known peer: {peer_host}:{peer_port}")

    def send_message(self, host, port, message_type, payload):
        """Sends a JSON message to a specific peer."""
        message = {
            "type": message_type,
            "payload": payload
        }
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((host, port))
                s.sendall((json.dumps(message) + '\\n').encode('utf-8'))
                logging.info(f"Sent {message_type} to {host}:{port}")
        except ConnectionRefusedError:
            logging.error(f"Failed to connect to {host}:{port}")
        except Exception as e:
            logging.error(f"Error sending message to {host}:{port}: {e}")

    def broadcast_message(self, message_type, payload):
        """Broadcasts a message to all known peers."""
        for host, port in self.peers:
            if (host, port) != (self.host, self.port):
                self.send_message(host, port, message_type, payload)

    def stop(self):
        """Stops the node."""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
