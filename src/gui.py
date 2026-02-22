import queue
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import logging
import time
import sys
import os

# Add src to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from node import Node

class QueueHandler(logging.Handler):
    """This class logs to a queue, thread-safe."""
    def __init__(self, log_queue):
        logging.Handler.__init__(self)
        self.log_queue = log_queue

    def emit(self, record):
        msg = self.format(record)
        self.log_queue.put(msg)

class BlockchainGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Blockchain Node GUI")
        self.root.geometry("900x700")
        
        self.node = None
        self.mining_status = False

        # --- Top Frame: Configuration ---
        config_frame = ttk.LabelFrame(root, text="Node Configuration")
        config_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(config_frame, text="Host:").grid(row=0, column=0, padx=5, pady=5)
        self.host_entry = ttk.Entry(config_frame)
        self.host_entry.insert(0, "localhost")
        self.host_entry.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(config_frame, text="Port:").grid(row=0, column=2, padx=5, pady=5)
        self.port_entry = ttk.Entry(config_frame, width=10)
        self.port_entry.insert(0, "5000")
        self.port_entry.grid(row=0, column=3, padx=5, pady=5)
        
        ttk.Label(config_frame, text="Bootstrap (host:port):").grid(row=0, column=4, padx=5, pady=5)
        self.bootstrap_entry = ttk.Entry(config_frame)
        self.bootstrap_entry.grid(row=0, column=5, padx=5, pady=5)
        
        self.start_btn = ttk.Button(config_frame, text="Start Node", command=self.start_node)
        self.start_btn.grid(row=0, column=6, padx=10, pady=5)

        # --- Middle Frame: Actions & Status ---
        action_frame = ttk.LabelFrame(root, text="Actions")
        action_frame.pack(fill="x", padx=10, pady=5)
        
        # Transaction
        ttk.Label(action_frame, text="Recipient:").grid(row=0, column=0, padx=5, pady=5)
        self.recipient_entry = ttk.Entry(action_frame)
        self.recipient_entry.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(action_frame, text="Amount:").grid(row=0, column=2, padx=5, pady=5)
        self.amount_entry = ttk.Entry(action_frame, width=10)
        self.amount_entry.grid(row=0, column=3, padx=5, pady=5)
        
        self.send_btn = ttk.Button(action_frame, text="Send Transaction", command=self.send_transaction, state="disabled")
        self.send_btn.grid(row=0, column=4, padx=10, pady=5)
        
        # Mining
        self.mine_btn = ttk.Button(action_frame, text="Start Mining", command=self.toggle_mining, state="disabled")
        self.mine_btn.grid(row=0, column=5, padx=10, pady=5)

        # Refresh
        self.refresh_btn = ttk.Button(action_frame, text="Refresh Chain", command=self.update_chain_display, state="disabled")
        self.refresh_btn.grid(row=0, column=6, padx=10, pady=5)

        # Status Label
        self.status_label = ttk.Label(action_frame, text="Status: Stopped", font=("Arial", 10, "bold"))
        self.status_label.grid(row=1, column=0, columnspan=7, pady=5)
        
        self.last_height = 0

        # --- Bottom Frame: Blockchain View & Logs ---
        paned_window = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
        paned_window.pack(fill="both", expand=True, padx=10, pady=5)

        # Left: Chain Treeview
        chain_frame = ttk.Frame(paned_window)
        paned_window.add(chain_frame, weight=1)
        
        ttk.Label(chain_frame, text="Blockchain (Blocks)").pack(anchor="w")
        
        columns = ("Index", "Hash", "Prev Hash", "Tx Count", "Nonce")
        self.tree = ttk.Treeview(chain_frame, columns=columns, show="headings", height=15)
        self.tree.heading("Index", text="Index")
        self.tree.heading("Hash", text="Hash")
        self.tree.heading("Prev Hash", text="Prev Hash")
        self.tree.heading("Tx Count", text="Tx Count")
        self.tree.heading("Nonce", text="Nonce")
        
        self.tree.column("Index", width=50)
        self.tree.column("Hash", width=150)
        self.tree.column("Prev Hash", width=150)
        self.tree.column("Tx Count", width=80)
        self.tree.column("Nonce", width=80)
        
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_block_select)

        # Right: Block Details & Logs
        details_frame = ttk.Frame(paned_window)
        paned_window.add(details_frame, weight=1)

        # Block Details
        ttk.Label(details_frame, text="Block Details / Transactions").pack(anchor="w")
        self.details_text = scrolledtext.ScrolledText(details_frame, height=10, state="disabled")
        self.details_text.pack(fill="x", expand=False, pady=(0, 10))

        # Logs
        ttk.Label(details_frame, text="Node Logs").pack(anchor="w")
        self.log_text = scrolledtext.ScrolledText(details_frame, height=10, state="disabled")
        self.log_text.pack(fill="both", expand=True)

        # Setup logging
        self.log_queue = queue.Queue()
        queue_handler = QueueHandler(self.log_queue)
        queue_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
        logging.getLogger().addHandler(queue_handler)
        logging.getLogger().setLevel(logging.INFO)

        # Initial loop
        self.root.after(100, self.poll_log_queue)
        self.root.after(1000, self.periodic_update)

    def poll_log_queue(self):
        """Polls the log queue and updates the text widget."""
        while not self.log_queue.empty():
            try:
                msg = self.log_queue.get_nowait()
                self.log_text.configure(state='normal')
                self.log_text.insert(tk.END, msg + '\n')
                self.log_text.configure(state='disabled')
                self.log_text.yview(tk.END)
            except queue.Empty:
                break
        self.root.after(100, self.poll_log_queue)

    def start_node(self):
        host = self.host_entry.get()
        try:
            port = int(self.port_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Port must be an integer")
            return

        bootstrap = self.bootstrap_entry.get()
        bootstrap_nodes = set()
        if bootstrap:
            try:
                for p in bootstrap.split(','):
                    h, po = p.split(':')
                    bootstrap_nodes.add((h, int(po)))
            except ValueError:
                messagebox.showerror("Error", "Invalid bootstrap format. Use host:port")
                return

        try:
            self.node = Node(host, port, bootstrap_nodes)
            self.node.start()
            
            self.start_btn.config(state="disabled")
            self.send_btn.config(state="normal")
            self.mine_btn.config(state="normal")
            self.refresh_btn.config(state="normal")
            self.status_label.config(text=f"Status: Running on {host}:{port}", foreground="green")
            
            logging.info(f"GUI started node on {host}:{port}")
            self.update_chain_display()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start node: {e}")

    def send_transaction(self):
        if not self.node:
            return
        
        recipient = self.recipient_entry.get()
        try:
            amount = float(self.amount_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Amount must be a number")
            return
            
        if not recipient or amount <= 0:
            messagebox.showerror("Error", "Invalid recipient or amount")
            return

        # Run in thread to prevent GUI freeze
        def task():
            try:
                tx = self.node.create_transaction(recipient, amount)
                if tx:
                    self.root.after(0, lambda: messagebox.showinfo("Success", f"Transaction created: {tx.id[:8]}..."))
                    self.root.after(0, lambda: self.recipient_entry.delete(0, tk.END))
                    self.root.after(0, lambda: self.amount_entry.delete(0, tk.END))
                else:
                    self.root.after(0, lambda: messagebox.showerror("Error", "Failed to create transaction (Balance too low?)"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", f"Transaction failed: {e}"))
        
        threading.Thread(target=task, daemon=True).start()

    def toggle_mining(self):
        if not self.node:
            return
        
        if not self.mining_status:
            self.node.start_mining()
            self.mine_btn.config(text="Stop Mining")
            self.mining_status = True
            logging.info("GUI: Mining started")
        else:
            self.node.stop_mining()
            self.mine_btn.config(text="Start Mining")
            self.mining_status = False
            logging.info("GUI: Mining stopped")

    def update_chain_display(self):
        if not self.node:
            return
            
        # Clear existing
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        # Add blocks (reverse order to show latest first)
        # Use safe getter
        blocks = self.node.get_blocks()
        for block in reversed(blocks):
            self.tree.insert("", "end", values=(
                block.index,
                block.hash[:16] + "...",
                block.previous_hash[:16] + "...",
                len(block.transactions),
                block.nonce
            ), tags=(str(block.index),))
            
        # Also update status details if needed
        # logging.info("Chain display updated.")

    def on_block_select(self, event):
        selected_item = self.tree.selection()
        if not selected_item:
            return
        
        # Get values
        item = self.tree.item(selected_item)
        values = item['values']
        block_index = values[0]
        
        # Find block object safely
        blocks = self.node.get_blocks()
        block = next((b for b in blocks if b.index == block_index), None)
        
        self.details_text.configure(state='normal')
        self.details_text.delete(1.0, tk.END)
        
        if block:
            details = f"Block #{block.index}"
            details += f"Hash: {block.hash}"
            details += f"Prev Hash: {block.previous_hash}"
            details += f"Nonce: {block.nonce}"
            details += f"Timestamp: {block.timestamp}"
            details += f"Transactions ({len(block.transactions)}):"
            for tx in block.transactions:
                if hasattr(tx, 'to_dict'):
                    details += f"  - {tx.to_dict()}"
                else:
                    details += f"  - {tx}"
        else:
            details = "Block not found."
            
        self.details_text.insert(tk.END, details)
        self.details_text.configure(state='disabled')

    def periodic_update(self):
        if self.node and self.node.running:
            current_height = len(self.node.blockchain.chain)
            
            # Update chain view if height changed
            if current_height > self.last_height:
                self.update_chain_display()
                self.last_height = current_height
                
            # Update status text periodically
            host = self.node.host
            port = self.node.port
            status_text = f"Status: Running on {host}:{port} | Height: {current_height} | Peers: {len(self.node.peers)}"
            if self.node.mining:
                status_text += " | Mining..."
            
            self.status_label.config(text=status_text, foreground="green")
            
        self.root.after(2000, self.periodic_update)

if __name__ == "__main__":
    root = tk.Tk()
    app = BlockchainGUI(root)
    root.mainloop()
