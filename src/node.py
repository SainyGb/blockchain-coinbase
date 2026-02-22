import socket
import threading
import json
import logging
import time
from blockchain import Blockchain
from transaction import Transaction
from block import Block

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
        self.mining = False
        self.server_socket = None
        self.blockchain = Blockchain()

    def start(self):
        """Starts the node server and initiates connections to peers."""
        self.running = True
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        logging.info(f"Node started on {self.host}:{self.port}")

        # Start listening for incoming connections in a separate thread
        listen_thread = threading.Thread(target=self._listen_for_connections)
        listen_thread.daemon = True
        listen_thread.start()

        # Connect to known peers
        self._connect_to_peers()

    def start_mining(self):
        """Starts the mining process in a separate thread."""
        if not self.mining:
            self.mining = True
            mining_thread = threading.Thread(target=self._mine_loop)
            mining_thread.daemon = True
            mining_thread.start()
            logging.info("Mining started.")

    def stop_mining(self):
        """Stops the mining process."""
        self.mining = False
        logging.info("Mining stopped.")

    def _mine_loop(self):
        """Continuous mining loop."""
        while self.mining and self.running:
            # Check for pending transactions
            if not self.blockchain.pending_transactions:
                time.sleep(1) # Wait for transactions
                continue

            # Create a candidate block
            # For simplicity, include all pending transactions (up to a limit in real life)
            pending_txs = list(self.blockchain.pending_transactions)
            
            # Create block
            prev_block = self.blockchain.get_latest_block()
            new_block = Block(
                index=prev_block.index + 1,
                previous_hash=prev_block.hash,
                transactions=pending_txs,
                timestamp=time.time()
            )

            # Mine the block (PoW)
            # We need to mine while checking if a new block arrived from network (interruption).
            # For simplicity, we mine in chunks or check flag.
            # Block.mine_block is blocking. We might want to make it interruptible or fast.
            # With difficulty 3, it's fast.
            logging.info(f"Mining block {new_block.index} with {len(pending_txs)} txs...")
            new_block.mine_block(self.blockchain.difficulty)
            
            # Check if someone else solved it while we were mining?
            # If we received a block, our previous_hash might be old.
            if prev_block.hash != self.blockchain.get_latest_block().hash:
                logging.info("Chain updated while mining. Restarting...")
                continue

            # Add to own chain
            if self.blockchain.add_block(new_block):
                logging.info(f"Block {new_block.index} mined! Hash: {new_block.hash[:8]}...")
                self.broadcast_message('NEW_BLOCK', new_block.to_dict())
            else:
                logging.warning("Mined block rejected by self (invalid?).")

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
            
            msg_type = message.get('type')
            payload = message.get('payload')
            
            if msg_type == 'NEW_TRANSACTION':
                self._handle_new_transaction(payload)
            elif msg_type == 'NEW_BLOCK':
                self._handle_new_block(payload)
            # Add other types here
            
        except json.JSONDecodeError:
            logging.error(f"Invalid JSON received from {addr}: {message_str}")

    def _handle_new_transaction(self, payload):
        """Handles a new transaction received from a peer."""
        try:
            tx = Transaction.from_dict(payload)
            # Add to pool. If it's new and valid, add_transaction returns True.
            if self.blockchain.add_transaction(tx):
                logging.info(f"New valid transaction {tx.id[:8]} added to pool. Relaying...")
                self.broadcast_message('NEW_TRANSACTION', payload)
            else:
                logging.info(f"Transaction {tx.id[:8]} rejected or already known.")
        except Exception as e:
            logging.error(f"Error processing transaction: {e}")

    def _handle_new_block(self, payload):
        """Handles a new block received from a peer."""
        try:
            block = Block.from_dict(payload)
            logging.info(f"Received block {block.index} from network.")
            
            # Attempt to add to chain
            if self.blockchain.add_block(block):
                logging.info(f"Block {block.index} added to chain. Relaying...")
                self.broadcast_message('NEW_BLOCK', payload)
            else:
                # If block is not valid or doesn't link, we might need to sync (Week 5).
                # Or it's just invalid.
                logging.info(f"Block {block.index} rejected.")
        except Exception as e:
            logging.error(f"Error processing block: {e}")

    def create_transaction(self, recipient, amount):
        """Creates a transaction from this node (e.g. via CLI) and broadcasts it."""
        # For simplicity, using 'self.host:self.port' as sender ID for now, 
        # but in reality it should be a public key / address.
        sender = f"{self.host}:{self.port}" 
        # Check if we are the 'admin' or have funds. 
        # For Week 3 tests, we might need to be 'admin' to send.
        # Let's assume the node has an identity.
        
        tx = self.blockchain.create_new_transaction(sender, recipient, amount)
        if tx:
            logging.info(f"Created transaction {tx.id[:8]}")
            self.broadcast_message('NEW_TRANSACTION', tx.to_dict())
            return tx
        else:
            logging.error("Failed to create transaction (insufficient funds?)")
            return None

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
        self.stop_mining()
        if self.server_socket:
            self.server_socket.close()
