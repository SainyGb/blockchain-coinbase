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
        self.mining_thread = None
        self.server_socket = None
        self.lock = threading.RLock() # Thread safety for chain/peers
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
        
        # Request chain from peers (Synchronization)
        self.broadcast_message('REQUEST_CHAIN', {})
        logging.info("Requested blockchain from peers.")

    def start_mining(self):
        """Starts the mining process in a separate thread."""
        self.mining = True
        if self.mining_thread and self.mining_thread.is_alive():
            logging.info("Mining process resumed.")
        else:
            self.mining_thread = threading.Thread(target=self._mine_loop)
            self.mining_thread.daemon = True
            self.mining_thread.start()
            logging.info("Mining started.")

    def stop_mining(self):
        """Stops the mining process."""
        self.mining = False
        logging.info("Mining stopped.")

    def _mine_loop(self):
        """Continuous mining loop."""
        while self.mining and self.running:
            # Simulate mining effort/time to prevent UI freezing and log flooding
            time.sleep(1)

            # Allow mining empty blocks (Coinbase)
            # if not self.blockchain.pending_transactions:
            #    time.sleep(1) 
            
            # Create a candidate block
            # For simplicity, include all pending transactions (up to a limit in real life)
            pending_txs = list(self.blockchain.pending_transactions)
            
            # Add Coinbase transaction (Mining Reward)
            miner_address = f"{self.host}:{self.port}"
            block_timestamp = time.time()
            coinbase_tx = Transaction("coinbase", miner_address, self.blockchain.mining_reward, timestamp=block_timestamp)
            # Coinbase is usually the first transaction
            pending_txs.insert(0, coinbase_tx)
            
            # Create block
            prev_block = self.blockchain.get_latest_block()
            new_block = Block(
                index=prev_block.index + 1,
                previous_hash=prev_block.hash,
                transactions=pending_txs,
                timestamp=block_timestamp
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
                # logging.info(f"Amount of transactions in block: {len(new_block.transactions)}")
                # logging.info(f"Amount of coins mined: {self.blockchain.get_balance(miner_address)}")
                self.broadcast_message('NEW_BLOCK', {"block": new_block.to_dict()})
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
            try:
                # Read 4-byte header (big-endian size)
                header = conn.recv(4)
                if not header:
                    return
                length = int.from_bytes(header, 'big')
                
                # Read JSON body
                data = b""
                while len(data) < length:
                    packet = conn.recv(length - len(data))
                    if not packet:
                        break
                    data += packet
                
                if len(data) == length:
                    message_str = data.decode('utf-8')
                    response_dict = self._process_message(message_str, addr)
                    if response_dict:
                        resp_bytes = json.dumps(response_dict).encode('utf-8')
                        resp_header = len(resp_bytes).to_bytes(4, 'big')
                        conn.sendall(resp_header + resp_bytes)
                else:
                    logging.error(f"Incomplete message from {addr}")
            except Exception as e:
                logging.error(f"Error handling client {addr}: {e}")
        logging.info(f"Disconnected from {addr}")

    def _process_message(self, message_str, addr):
        """Processes a received message string."""
        try:
            message = json.loads(message_str)
            
            msg_type = message.get('type')
            payload = message.get('payload')

            # Log received message (except large chain responses)
            if msg_type != 'RESPONSE_CHAIN':
                logging.info(f"Received message from {addr}: {message}")
            else:
                logging.info(f"Received RESPONSE_CHAIN from {addr}")
            
            if msg_type == 'NEW_TRANSACTION':
                self._handle_new_transaction(payload)
            elif msg_type == 'NEW_BLOCK':
                self._handle_new_block(payload)
            elif msg_type == 'REQUEST_CHAIN':
                return self._handle_request_chain(payload, message, addr)
            elif msg_type == 'RESPONSE_CHAIN':
                self._handle_response_chain(payload)
            
        except json.JSONDecodeError:
            logging.error(f"Invalid JSON received from {addr}: {message_str}")
        return None

    def _handle_request_chain(self, payload, message, addr):
        """Handles a request for the blockchain."""
        try:
            peer_host = addr[0]
            peer_port = None
            
            sender = message.get('sender')
            if sender:
                try:
                    peer_host, peer_port_str = sender.split(':')
                    peer_port = int(peer_port_str)
                except ValueError:
                    pass
            
            if not peer_port:
                peer_port = payload.get('port')
            
            if peer_port:
                # Add requesting peer to known peers for bidirectional communication
                if (peer_host, peer_port) not in self.peers and (peer_host, peer_port) != (self.host, self.port):
                    self.peers.add((peer_host, peer_port))
                    logging.info(f"Added peer {peer_host}:{peer_port} from REQUEST_CHAIN")

                logging.info(f"Sending blockchain to {peer_host}:{peer_port}")
                chain_data = {
                    "blockchain": {
                        "chain": [block.to_dict() for block in self.blockchain.chain],
                        "pending_transactions": [tx.to_dict() if hasattr(tx, 'to_dict') else tx for tx in self.blockchain.pending_transactions]
                    }
                }
                return {
                    "type": "RESPONSE_CHAIN",
                    "payload": chain_data,
                    "sender": f"{self.host}:{self.port}"
                }
            else:
                logging.warning(f"Received REQUEST_CHAIN without port from {addr}")
        except Exception as e:
            logging.error(f"Error handling REQUEST_CHAIN: {e}")
        return None

    def _handle_response_chain(self, payload):
        """Handles a received blockchain."""
        try:
            if isinstance(payload, dict) and "blockchain" in payload:
                chain_data = payload["blockchain"].get("chain", [])
            elif isinstance(payload, list):
                chain_data = payload
            else:
                chain_data = []

            new_chain = []
            for block_data in chain_data:
                new_chain.append(Block.from_dict(block_data))
            
            logging.info(f"Received chain with {len(new_chain)} blocks.")
            with self.lock:
                replaced = self.blockchain.replace_chain(new_chain)
                
            if replaced:
                logging.info("Replaced local chain with longer valid chain.")
            else:
                logging.info("Received chain rejected (shorter or invalid).")
        except Exception as e:
            logging.error(f"Error processing RESPONSE_CHAIN: {e}")

    def _handle_new_transaction(self, payload):
        """Handles a new transaction received from a peer."""
        try:
            tx_data = payload.get("transaction", payload) if isinstance(payload, dict) else payload
            tx = Transaction.from_dict(tx_data)
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
            block_data = payload.get("block", payload) if isinstance(payload, dict) else payload
            block = Block.from_dict(block_data)
            logging.info(f"Received block {block.index} from network.")
            
            # Attempt to add to chain
            with self.lock:
                added = self.blockchain.add_block(block)
            
            if added:
                logging.info(f"Block {block.index} added to chain. Relaying...")
                self.broadcast_message('NEW_BLOCK', payload)
            else:
                # If block is not valid or doesn't link, we might need to sync (Week 5).
                # Or it's just invalid.
                logging.info(f"Block {block.index} rejected. Requesting chain sync.")
                self.broadcast_message('REQUEST_CHAIN', {})
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
            self.broadcast_message('NEW_TRANSACTION', {"transaction": tx.to_dict()})
            return tx
        else:
            logging.error("Failed to create transaction (insufficient funds?)")
            return None

    def _connect_to_peers(self):
        """Connects to known peers."""
        connected_peers = set()
        for peer_host, peer_port in self.peers:
            if (peer_host, peer_port) == (self.host, self.port):
                continue
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(5)
                    s.connect((peer_host, peer_port))
                logging.info(f"Successfully connected to known peer: {peer_host}:{peer_port}")
                connected_peers.add((peer_host, peer_port))
            except Exception as e:
                logging.warning(f"Failed to connect to known peer {peer_host}:{peer_port}: {e}")
        self.peers = connected_peers

    def connect_to_peer(self, host, port):
        """Attempts to connect to a new peer dynamically and add it to the network."""
        if (host, port) == (self.host, self.port):
            return False
        
        if (host, port) in self.peers:
            return True
            
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5)
                s.connect((host, port))
            logging.info(f"Successfully connected to new peer: {host}:{port}")
            with self.lock:
                self.peers.add((host, port))
            
            # Send a REQUEST_CHAIN to the new peer so they add us and we sync
            self.send_message(host, port, 'REQUEST_CHAIN', {})
            return True
        except Exception as e:
            logging.warning(f"Failed to connect to new peer {host}:{port}: {e}")
            return False

    def send_message(self, host, port, message_type, payload):
        """Sends a JSON message to a specific peer."""
        message = {
            "type": message_type,
            "payload": payload,
            "sender": f"{self.host}:{self.port}"
        }
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5) # Prevent hanging
                s.connect((host, port))
                # Standard: [4 bytes big-endian size] [JSON]
                json_bytes = (json.dumps(message)).encode('utf-8')
                header = len(json_bytes).to_bytes(4, 'big')
                s.sendall(header + json_bytes)
                logging.info(f"Sent {message_type} to {host}:{port}")
                
                # Try to read response on the same socket
                try:
                    resp_header = s.recv(4)
                    if resp_header:
                        resp_length = int.from_bytes(resp_header, 'big')
                        resp_data = b""
                        while len(resp_data) < resp_length:
                            packet = s.recv(resp_length - len(resp_data))
                            if not packet:
                                break
                            resp_data += packet
                        if len(resp_data) == resp_length:
                            resp_message_str = resp_data.decode('utf-8')
                            self._process_message(resp_message_str, (host, port))
                except socket.timeout:
                    pass  # No response received, which is fine for most messages
                except Exception as e:
                    logging.error(f"Error reading response from {host}:{port}: {e}")
        except ConnectionRefusedError:
            logging.error(f"Failed to connect to {host}:{port}")
        except Exception as e:
            logging.error(f"Error sending message to {host}:{port}: {e}")

    def broadcast_message(self, message_type, payload):
        """Broadcasts a message to all known peers."""
        for host, port in list(self.peers):
            if (host, port) != (self.host, self.port):
                self.send_message(host, port, message_type, payload)

    def get_blocks(self):
        """Returns a copy of the blockchain safely."""
        with self.lock:
            return list(self.blockchain.chain)

    def stop(self):
        """Stops the node."""
        self.running = False
        self.stop_mining()
        if self.server_socket:
            self.server_socket.close()
