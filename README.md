# Pilot Chain

Pilot Chain is an educational Proof-of-Work blockchain built with Python and Flask. It includes a browser dashboard for creating a local secp256k1 wallet, submitting transactions, mining blocks, viewing the chain, registering peer nodes, and resolving conflicts with the longest-valid-chain rule.

[GitHub Pages dashboard](https://dilatedtime.github.io/blockchain-python/) | [Render deployment](https://blockchain-python-it0b.onrender.com/) | [Source code](https://github.com/dilatedtime/blockchain-python)

> The GitHub Pages dashboard uses the same interface as the Render deployment and connects to its live Flask API. GitHub Pages hosts the browser files, while Render runs the blockchain node. Both URLs therefore show and change the same in-memory chain.

## Features

- Flask blockchain node with an in-memory ledger
- SHA-256 block hashing
- Adjustable Proof-of-Work validation, currently set to difficulty 2
- Pending transaction pool and a reward of 1 coin per mined block
- Browser-generated secp256k1 wallet keys
- Wallet balance calculation from confirmed blocks
- Block and transaction explorer
- Peer-node registration and longest-valid-chain consensus
- JSON API with CORS support

## Requirements

- Python 3.9 or newer
- `pip`

## Run the dashboard

```bash
git clone https://github.com/dilatedtime/blockchain-python.git
cd blockchain-python

python -m venv venv
```

Activate the virtual environment:

```powershell
# Windows PowerShell
.\venv\Scripts\Activate.ps1
```

```bash
# macOS or Linux
source venv/bin/activate
```

Install the dependencies and start the current node server:

```bash
pip install -r requirements.txt
python node_server.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

You can also start the packaged blockchain interface with:

```bash
python -m blockchain
```

The separate transaction client accepts a port number:

```bash
python -m client 8080
```

## API

| Method | Route | Purpose |
| --- | --- | --- |
| `GET` | `/` | Open the Pilot Chain dashboard |
| `GET` | `/chain` | Return the full blockchain and its length |
| `GET` | `/transactions` | Return pending transactions |
| `POST` | `/transactions/new` | Queue a transaction with `sender`, `recipient`, and `amount` |
| `GET` | `/mine?address=<wallet>` | Mine a block and send the reward to a wallet |
| `GET` | `/wallet` | Return the node identifier and node balance |
| `POST` | `/nodes/register` | Register peer-node URLs |
| `GET` | `/nodes/resolve` | Replace the local chain if a longer valid peer chain exists |

Example transaction:

```bash
curl -X POST http://127.0.0.1:5000/transactions/new \
  -H "Content-Type: application/json" \
  -d '{"sender":"alice","recipient":"bob","amount":5}'
```

Register a peer node:

```bash
curl -X POST http://127.0.0.1:5000/nodes/register \
  -H "Content-Type: application/json" \
  -d '{"nodes":["http://127.0.0.1:5001"]}'
```

## Project structure

```text
blockchain-python/
├── node_server.py          # Current all-in-one node, API, and dashboard server
├── templates/              # Pilot Chain dashboard and local elliptic library
├── blockchain/             # Packaged blockchain implementation and Flask UI
├── client/                 # RSA transaction client
├── docs/                   # GitHub Pages copy of the live dashboard
├── requirements.txt        # Runtime dependencies
├── Pipfile                  # Pipenv configuration
└── config.ini              # Host, port, and debug settings for packaged apps
```

## Current limitations

- The chain and pending transactions live in memory and reset when the server stops.
- The browser creates secp256k1 signatures, but the node does not yet verify them before accepting a transaction.
- The longest-chain rule is a learning implementation, not a production consensus protocol.
- The default mining difficulty is intentionally low so blocks can be mined quickly during a demo.
- The server has no authentication, persistent storage, rate limiting, or production key management.

Use this project for learning and local experiments. Do not use it to hold assets or process real payments.
