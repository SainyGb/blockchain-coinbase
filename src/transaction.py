import time
import json
import hashlib
import uuid

class Transaction:
    def __init__(self, sender, recipient, amount, timestamp=None, tx_id=None):
        self.sender = sender
        self.recipient = recipient
        self.amount = amount
        self.timestamp = timestamp if timestamp is not None else time.time()
        self.id = tx_id if tx_id else self.calculate_id()

    def calculate_id(self):
        """Generates a unique ID for the transaction."""
        return str(uuid.uuid4())

    def to_dict(self):
        return {
            "id": self.id,
            "origem": self.sender,
            "destino": self.recipient,
            "valor": self.amount,
            "timestamp": self.timestamp
        }

    @staticmethod
    def from_dict(data):
        return Transaction(
            sender=data["origem"],
            recipient=data["destino"],
            amount=data["valor"],
            timestamp=data["timestamp"],
            tx_id=data["id"]
        )

    def is_valid(self):
        """Checks if the transaction structure is valid (positive amount, etc.)."""
        if not self.sender or not self.recipient:
            return False
        if self.amount <= 0:
            return False
        # In a real system, we'd check signatures here.
        return True
