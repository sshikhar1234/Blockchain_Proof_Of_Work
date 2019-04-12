from flask import Flask, jsonify, request
import hashlib
import json
from time import time
from uuid import uuid4
import requests
from datetime import datetime

class GenericBlockchain(object):

    # Initializing the blockchain
    def __init__(self):
        self.chain = []
        self.current_transactions = []
        self.hashes = []
        self.new_block(proof=100, prev_hash=1)
        self.nodes = set()

    def reg_new_node(self, address):
        self.nodes.add(address)

    def new_block(self, proof, prev_hash=None):
        block = {
            'index': len(self.chain)+1,
            'timestamp': time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': prev_hash or self.hash(self.chain[-1])
            }
        self.chain.append(block)
        hash_detail = {
            'index': len(self.chain),
            'hash':  hashlib.sha256(json.dumps(block, sort_keys=True).encode()).hexdigest()
        }
        self.hashes.append(hash_detail)
        self.current_transactions = []

        return block

    def valid_chain(self, chain):
        last_block = chain[0]
        current_index = 1
        while current_index < len(chain):
            current_block = chain(current_index)

            print(f'{last_block}')
            print(f'{current_block}')
            print("\n-----------\n")

            if current_index['previous_hash'] != self.hash(last_block):
                return False
            if not self.valid_proof(current_block['proof'], last_block['proof']):
                return False
            last_block = current_block
            current_index += 1
        return True

    def resolve_conflicts(self):
        neighbour_nodes = self.nodes
        new_chain = None
        maximum_length = len(self.chain)

        for node in neighbour_nodes:

            current_chain = requests.get(f'http://{node}/chain')

            if current_chain.status_code == 200:
                length = current_chain.json()['length']
                chain = current_chain.json()['chain']

                if length > maximum_length and self.valid_chain(chain):
                    maximum_length = length
                    new_chain = chain

        if new_chain:
            self.chain = new_chain
            return True
        return False

    def new_transaction(self, sender, receiver, amount):
        self.current_transactions.append(
            {
                'sender': sender,
                'receiver': receiver,
                'amount': amount
            })
        return self.last_block['index'] + 1

    @staticmethod
    def hash(block):
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()
        pass

    @property
    def last_block(self):
        return self.chain[-1]

    def proof_of_work(self, last_proof):
        proof = 0
        while self.valid_proof(proof, last_proof) is False:
            proof += 1
        return proof

    @staticmethod
    def valid_proof(proof, last_proof):
        temp_hash = hashlib.sha256(f'{proof}{last_proof}'.encode()).hexdigest()
        return temp_hash[:6] == "000000"


node_identifier = str(uuid4()).replace('-', '')
blockchain = GenericBlockchain()
app = Flask(__name__)


@app.route('/')
def hello_world():
    blockchain.chain = []
    blockchain.current_transactions = []
    return "hello world"


@app.route('/transactions/new', methods=['POST'])
def new_transaction():

    values = request.get_json()
    print(request.get_json())
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return 'Missing value(s)', 400
    index = blockchain.new_transaction(values['sender'], values['recipient'], values['amount'])

    response = {
        'message': f'Transaction will be added to block {index}'
    }
    return jsonify(response), 201


@app.route('/mine', methods=['GET'])
def mine():

    # get last block and its proof
    last_block = blockchain.last_block
    last_proof = last_block['proof']

    # calculate the proof of work to mine new block
    proof = blockchain.proof_of_work(last_proof)

    # the reward of 100 coins for mining the block
    blockchain.new_transaction(
        sender="0",
        receiver=node_identifier,
        amount=50
    )
    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(proof, previous_hash)

    response = {
        'message': 'New Block Forged',
        'index': block['index'],
        'timestamp':  datetime.utcfromtimestamp(block['timestamp']).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],
        'current_hash': hashlib.sha256(json.dumps(blockchain.chain[-1], sort_keys=True).encode()).hexdigest()
    }

    return jsonify(response), 200


@app.route('/chain', methods=['GET'])
def full_chain():

    response = {
        'block_list': blockchain.chain,
        'hash_list': blockchain.hashes,
        'length': len(blockchain.chain)
    }
    return jsonify(response)
#
#
# @app.route('/nodes/register', methods=['POST'])
# def register_new_nodes():
#     values = request.get_json()
#     nodes = values.get('nodes')
#     if nodes is None:
#         return "Error: Please supply a valid list of nodes", 400
#
#     for node in nodes:
#         blockchain.reg_new_node(node)
#
#     response = {
#         'message': 'New nodes have been added',
#         'total_nodes': list(blockchain.nodes)
#     }
#     return jsonify(response), 201
#
#
# @app.route('/nodes/resolve', methods=['GET'])
# def consensus():
#     resolved = blockchain.resolve_conflicts()
#
#     if resolved:
#         response = {
#             'message': 'Our chain was replaced',
#             'new_chain': blockchain.chain
#         }
#     else:
#         response = {
#             'message': 'Our chain is authoritative',
#             'chain': blockchain.chain
#         }
#     return jsonify(response), 200
#

if __name__ == '__main__':
    app.run(debug=True)