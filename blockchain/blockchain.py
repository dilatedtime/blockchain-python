import binascii
import hashlib
import json
from time import time
from urllib.parse import urlparse
from uuid import uuid4
import requests

# We will skip RSA imports to avoid conflicts with your UI's Elliptic Curve signatures
# for this pilot version.

MINING_SENDER = "0"  # Standardize on "0" for the network reward address
MINING_REWARD = 1
MINING_DIFFICULTY = 2

class Blockchain:
    def __init__(self):
        self.chain = []
        self.transactions = []
        self.nodes = set()
        self.node_id = str(uuid4()).replace("-", "")
        # Create the genesis block
        self.new_block(previous_hash="1", nonce=100)

    def new_block(self, nonce: int, previous_hash: str = None) -> dict:
        """
        Create a new Block in the Blockchain
        """
        block = {
            "index": len(self.chain) + 1,
            "timestamp": time(),
            "transactions": self.transactions,
            "nonce": nonce,
            "previous_hash": previous_hash or self.hash(self.chain[-1]),
        }

        # Reset the current list of transactions
        self.transactions = []
        self.chain.append(block)
        return block

    def new_transaction(self, sender: str, recipient: str, amount: int) -> int:
        """
        Creates a new transaction to go into the next mined Block
        """
        self.transactions.append({
            "sender": sender,
            "recipient": recipient,
            "amount": amount,
        })
        return self.last_block["index"] + 1

    @staticmethod
    def hash(block: dict) -> str:
        """
        Creates a SHA-256 hash of a Block
        """
        # We must make sure that the Dictionary is Ordered, or we'll have inconsistent hashes
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    @property
    def last_block(self):
        return self.chain[-1]

    def proof_of_work(self) -> int:
        """
        Simple Proof of Work Algorithm:
        """
        last_block = self.chain[-1]
        last_hash = self.hash(last_block)

        nonce = 0
        while self.valid_proof(self.transactions, last_hash, nonce) is False:
            nonce += 1

        return nonce

    @staticmethod
    def valid_proof(transactions, last_hash, nonce, difficulty=MINING_DIFFICULTY):
        """
        Check if a hash value satisfies the mining conditions.
        """
        # We use json.dumps to ensure the transactions string is consistent
        guess = (json.dumps(transactions, sort_keys=True) + str(last_hash) + str(nonce)).encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:difficulty] == "0" * difficulty

    def register_node(self, address: str) -> None:
        parsed_url = urlparse(address)
        if parsed_url.netloc:
            self.nodes.add(parsed_url.netloc)
        elif parsed_url.path:
            self.nodes.add(parsed_url.path)
        else:
            raise ValueError("Invalid URL")

    def valid_chain(self, chain: list) -> bool:
        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]

            if block["previous_hash"] != self.hash(last_block):
                return False

            # Check that the Proof of Work is correct
            transactions = block["transactions"]
            if not self.valid_proof(transactions, block["previous_hash"], block["nonce"]):
                return False

            last_block = block
            current_index += 1

        return True

    def resolve_conflicts(self) -> bool:
        neighbours = self.nodes
        new_chain = None
        max_length = len(self.chain)

        for node in neighbours:
            response = requests.get(f"http://{node}/chain")
            if response.status_code == 200:
                length = response.json()["length"]
                chain = response.json()["chain"]

                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        if new_chain:
            self.chain = new_chain
            return True

        return False