import hashlib
import json
from time import time
from uuid import uuid4
from flask import Flask, jsonify, request, send_from_directory, render_template
from flask_cors import CORS

# ==========================================
# PART 1: BLOCKCHAIN LOGIC
# ==========================================

class Blockchain:
    def __init__(self):
        self.chain = []
        self.transactions = []
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)