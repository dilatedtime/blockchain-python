from flask import Flask, jsonify, request, send_from_directory, render_template
from uuid import uuid4
from blockchain.blockchain import Blockchain
from flask_cors import CORS

# Instantiate the Node
app = Flask(__name__, static_folder='templates')

# Fix for "Status Offline": Allow all domains to access the API
CORS(app, resources={r"/*": {"origins": "*"}})

# Generate a globally unique address for this node
node_identifier = str(uuid4()).replace('-', '')

# Instantiate the Blockchain
blockchain = Blockchain()

@app.route('/')
def index():
    return render_template('index.html')

# Allow the browser to load the local crypto library
@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('templates', filename)

@app.route('/mine', methods=['GET'])
def mine():
    # 1. Add the Mining Reward Transaction BEFORE calculating proof
    # If we add it after, the proof will be invalid for the block content.
    blockchain.new_transaction(
        sender="0",
        recipient=node_identifier,
        amount=1,
    )

    # 2. Run the Proof of Work algorithm to get the next proof
    # We do NOT pass arguments because blockchain.py uses self.transactions
    proof = blockchain.proof_of_work()

    # 3. Forge the new Block by adding it to the chain
    previous_hash = blockchain.hash(blockchain.last_block)
    block = blockchain.new_block(proof, previous_hash)

    response = {
        'message': "New Block Forged",
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],
    }
    return jsonify(response), 200

@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()

    # Check that the required fields are in the POST'ed data
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return 'Missing values', 400

    # Create a new Transaction
    index = blockchain.new_transaction(values['sender'], values['recipient'], values['amount'])
    
    response = {'message': f'Transaction will be added to Block {index}'}
    return jsonify(response), 201

@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200

@app.route('/transactions', methods=['GET'])
def get_transactions():
    return jsonify(blockchain.transactions), 200

@app.route('/wallet', methods=['GET'])
def get_wallet():
    balance = calculate_balance(node_identifier)
    response = {
        'node_id': node_identifier,
        'balance': balance
    }
    return jsonify(response), 200

def calculate_balance(node_address):
    balance = 0
    # 1. Check confirmed blocks
    for block in blockchain.chain:
        for trans in block['transactions']:
            if trans['recipient'] == node_address:
                balance += trans['amount']
            if trans['sender'] == node_address:
                balance -= trans['amount']
    
    # 2. Check pending pool
    for trans in blockchain.transactions:
        if trans['sender'] == node_address:
            balance -= trans['amount']
            
    return balance

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)