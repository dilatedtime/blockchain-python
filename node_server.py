import hashlib
import json
from time import time
from uuid import uuid4
from urllib.parse import urlparse  # <--- Make sure this is here
import requests
from flask import Flask, jsonify, request, send_from_directory, render_template
from flask_cors import CORS

# ==========================================
# PART 1: BLOCKCHAIN LOGIC
# ==========================================

class Blockchain:
    def __init__(self):
        self.chain = []
        self.transactions = []
        self.nodes = set()  # <--- ADD THIS EXACT LINE
        self.node_id = str(uuid4()).replace("-", "")
        # Genesis block
        self.new_block(previous_hash="1", nonce=100)

    def new_block(self, nonce: int, previous_hash: str = None) -> dict:
        block = {
            "index": len(self.chain) + 1,
            "timestamp": time(),
            "transactions": self.transactions,
            "nonce": nonce,
            "previous_hash": previous_hash or self.hash(self.chain[-1]),
        }
        self.transactions = []
        self.chain.append(block)
        return block

    def new_transaction(self, sender: str, recipient: str, amount: int) -> int:
        self.transactions.append({
            "sender": sender,
            "recipient": recipient,
            "amount": amount,
        })
        return self.last_block["index"] + 1

    @staticmethod
    def hash(block: dict) -> str:
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    @property
    def last_block(self):
        return self.chain[-1]

    def proof_of_work(self) -> int:
        last_block = self.chain[-1]
        last_hash = self.hash(last_block)
        nonce = 0
        while self.valid_proof(self.transactions, last_hash, nonce) is False:
            nonce += 1
        return nonce

    @staticmethod
    def valid_proof(transactions, last_hash, nonce, difficulty=2):
        guess = (json.dumps(transactions, sort_keys=True) + str(last_hash) + str(nonce)).encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:difficulty] == "0" * difficulty
    
    def register_node(self, address: str) -> None:
        """Add a new node to the list of nodes"""
        parsed_url = urlparse(address)
        if parsed_url.netloc:
            self.nodes.add(parsed_url.netloc)
        elif parsed_url.path:
            self.nodes.add(parsed_url.path)
        else:
            raise ValueError("Invalid URL")

    def valid_chain(self, chain: list) -> bool:
        """Determine if a given blockchain is valid"""
        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            if block["previous_hash"] != self.hash(last_block):
                return False
            
            # Check that the Proof of Work is correct
            if not self.valid_proof(block["transactions"], block["previous_hash"], block["nonce"]):
                return False

            last_block = block
            current_index += 1

        return True

    def resolve_conflicts(self) -> bool:
        """Consensus Algorithm: Replaces our chain with the longest one in the network"""
        neighbours = self.nodes
        new_chain = None
        max_length = len(self.chain)

        for node in neighbours:
            try:
                response = requests.get(f"http://{node}/chain", timeout=3)
                if response.status_code == 200:
                    length = response.json()["length"]
                    chain = response.json()["chain"]

                    if length > max_length and self.valid_chain(chain):
                        max_length = length
                        new_chain = chain
            except requests.exceptions.RequestException:
                continue 

        if new_chain:
            self.chain = new_chain
            return True

        return False

# ==========================================
# PART 2: FLASK SERVER
# ==========================================

app = Flask(__name__, static_folder='templates')
CORS(app, resources={r"/*": {"origins": "*"}})

blockchain = Blockchain()

# --- ROUTES ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('templates', filename)

@app.route('/mine', methods=['GET']) # Changed to GET for simplicity, but accepts query param
def mine():
    # LOGIC FIX 1: Who gets the reward?
    # We look for a 'miner_address' in the request. If none, the Node keeps it.
    miner_address = request.args.get('address')
    if not miner_address or miner_address == "null":
        miner_address = blockchain.node_id

    # LOGIC FIX 2: Prevent Empty Blocks (If you prefer that logic)
    # Uncomment the next 3 lines if you STRICTLY want to forbid empty blocks
    # if len(blockchain.transactions) == 0:
    #     return jsonify({'message': 'No transactions to mine'}), 400

    # 1. Add Reward Transaction
    blockchain.new_transaction(
        sender="0",
        recipient=miner_address,
        amount=1,
    )

    # 2. Proof of Work
    proof = blockchain.proof_of_work()

    # 3. Forge Block
    previous_hash = blockchain.hash(blockchain.last_block)
    block = blockchain.new_block(proof, previous_hash)

    return jsonify({
        'message': "New Block Forged",
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],
    }), 200

@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return 'Missing values', 400

    index = blockchain.new_transaction(values['sender'], values['recipient'], values['amount'])
    return jsonify({'message': f'Transaction will be added to Block {index}'}), 201

@app.route('/chain', methods=['GET'])
def full_chain():
    return jsonify({
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }), 200

@app.route('/transactions', methods=['GET'])
def get_transactions():
    return jsonify(blockchain.transactions), 200

@app.route('/wallet', methods=['GET'])
def get_wallet():
    # This endpoint calculates balance for the NODE, not the browser user.
    # The browser user calculates their own balance in JS.
    balance = 0
    for block in blockchain.chain:
        for trans in block['transactions']:
            if trans['recipient'] == blockchain.node_id:
                balance += trans['amount']
            if trans['sender'] == blockchain.node_id:
                balance -= trans['amount']
    
    return jsonify({
        'node_id': blockchain.node_id,
        'balance': balance
    }), 200
    
@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()
    nodes = values.get('nodes')
    
    if nodes is None:
        return "Error: Please supply a valid list of nodes", 400

    for node in nodes:
        blockchain.register_node(node)

    return jsonify({
        'message': 'New nodes have been added',
        'total_nodes': list(blockchain.nodes)
    }), 201

@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    # Trigger the longest chain rule
    replaced = blockchain.resolve_conflicts()

    if replaced:
        return jsonify({
            'message': 'Our chain was replaced by a longer, valid chain from the network.',
            'new_chain': blockchain.chain
        }), 200
    else:
        return jsonify({
            'message': 'Our chain is authoritative (We have the longest chain).',
            'chain': blockchain.chain
        }), 200

if __name__ == '__main__':
    import os
    
    # Render dynamically assigns a PORT environment variable. 
    # If it doesn't exist (like on your laptop), it safely defaults to 5000.
    port = int(os.environ.get("PORT", 5000))
    
    print(f"Node started! Your Mining ID is: {blockchain.node_id}")
    app.run(host='0.0.0.0', port=port)