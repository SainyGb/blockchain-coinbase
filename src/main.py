import argparse
import sys
import logging
import threading
import time
from node import Node

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def parse_peers(peers_str):
    """Parses a comma-separated list of host:port strings into a set of tuples."""
    if not peers_str:
        return set()
    peers = set()
    try:
        for p in peers_str.split(','):
            host, port = p.split(':')
            peers.add((host, int(port)))
    except ValueError:
        logging.error("Invalid peer format. Use host:port,host:port")
        sys.exit(1)
    return peers

def main():
    parser = argparse.ArgumentParser(description="Start a Blockchain Node")
    parser.add_argument("--host", default="localhost", help="Host to bind to")
    parser.add_argument("--port", type=int, required=True, help="Port to listen on")
    parser.add_argument("--bootstrap", help="Comma-separated list of bootstrap peers (host:port)")
    
    args = parser.parse_args()

    bootstrap_nodes = parse_peers(args.bootstrap)
    node = Node(args.host, args.port, bootstrap_nodes)

    try:
        node.start()
        # Keep the main thread alive to allow the node to run
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Stopping node...")
        node.stop()
        sys.exit(0)

if __name__ == "__main__":
    main()
