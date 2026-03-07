from flask import Flask, render_template, jsonify, request, send_from_directory
from uuid import uuid4
from blockchain.blockchain import Blockchain
from flask_cors import CORS
import sys

# Configure Flask
app = Flask(__name__, static_folder='templates')
CORS(app, resources={r"/*": {"origins": "*"}})

# Unique Node Address
node_identifier = str(uuid4()).replace('-', '')

# Initialize Blockchain
blockchain = Blockchain()

# --- HELPER: Safe Transaction Getter ---
def get_pending_txs():
    # Tries different common names for the transaction list to avoid 500 Errors
    if hasattr(blockchain, 'current_transactions'):
        return blockchain.current_transactions
    elif hasattr(blockchain, 'pending_transactions'):
        return blockchain.pending_transactions
    elif hasattr(blockchain, 'transactions'):
        return blockchain.transactions
    else:
        print("ERROR: Could not find transaction list in Blockchain class!")
        return []

@app.route('/')
def index():
    return render_template('index.html')

# --- Serve Local Static Files (Fixes "Elliptic" load error) ---
@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('templates', filename)

@app.route('/transactions', methods=['GET'])
def get_transactions():
    try:
        txs = get_pending_txs()
        return jsonify(txs), 200
    except Exception as e:
        print(f"ERROR in /transactions: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/mine', methods=['GET'])
def mine():
    try:
        # 1. Run Proof of Work
        last_block = blockchain.last_block
        last_proof = last_block['proof']
        proof = blockchain.proof_of_work(last_proof)

        # 2. Reward the miner (Sender "0" means new coin)
        blockchain.new_transaction(
            sender="0",
            recipient=node_identifier,
            amount=1,
        )

        # 3. Forge the new Block
        previous_hash = blockchain.hash(last_block)
        block = blockchain.new_block(proof, previous_hash)

        response = {
            'message': "New Block Forged",
            'index': block['index'],
            'transactions': block['transactions'],
            'proof': block['proof'],
            'previous_hash': block['previous_hash'],
        }
        return jsonify(response), 200
    except Exception as e:
        print(f"ERROR in /mine: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    try:
        values = request.get_json()
        required = ['sender', 'recipient', 'amount']
        if not all(k in values for k in required):
            return 'Missing values', 400

        index = blockchain.new_transaction(values['sender'], values['recipient'], values['amount'])
        response = {'message': f'Transaction will be added to Block {index}'}
        return jsonify(response), 201
    except Exception as e:
        print(f"ERROR in /transactions/new: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/chain', methods=['GET'])
def full_chain():
    try:
        response = {
            'chain': blockchain.chain,
            'length': len(blockchain.chain),
        }
        return jsonify(response), 200
    except Exception as e:
        print(f"ERROR in /chain: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/wallet', methods=['GET'])
def get_wallet():
    try:
        balance = 0
        
        # 1. Check confirmed blocks
        for block in blockchain.chain:
            # Handle different transaction structures (dict vs object)
            txs = block.get('transactions', []) if isinstance(block, dict) else getattr(block, 'transactions', [])
            
            for trans in txs:
                # Safe access to sender/recipient
                if isinstance(trans, dict):
                    r = trans.get('recipient')
                    s = trans.get('sender')
                    a = trans.get('amount', 0)
                else:
                    r = getattr(trans, 'recipient', None)
                    s = getattr(trans, 'sender', None)
                    a = getattr(trans, 'amount', 0)

                if r == node_identifier:
                    balance += a
                if s == node_identifier:
                    balance -= a
        
        # 2. Check pending pool
        pending = get_pending_txs()
        for trans in pending:
            if isinstance(trans, dict):
                s = trans.get('sender')
                a = trans.get('amount', 0)
            else:
                s = getattr(trans, 'sender', None)
                a = getattr(trans, 'amount', 0)
                
            if s == node_identifier:
                balance -= a
                
        response = {
            'node_id': node_identifier,
            'balance': balance
        }
        return jsonify(response), 200
    except Exception as e:
        print(f"ERROR in /wallet: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Print what the server is finding to help debug
    print("--- DEBUG INFO ---")
    print(f"Blockchain initialized.")
    if hasattr(blockchain, 'current_transactions'):
        print("Using: blockchain.current_transactions")
    elif hasattr(blockchain, 'pending_transactions'):
        print("Using: blockchain.pending_transactions")
    else:
        print("WARNING: Could not find transaction list variable name!")
    print("------------------")
    
    app.run(host='0.0.0.0', port=5000, debug=True)