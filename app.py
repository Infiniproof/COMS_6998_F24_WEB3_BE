from fastapi import FastAPI, HTTPException
from web3 import Web3
import json
import os

app = FastAPI()

w3 = Web3(Web3.HTTPProvider('https://<network>.infura.io/v3/OUR_PROJECT_ID'))
if not w3.isConnected():
    raise Exception("Failed to connect to Ethereum network!")

contract_abi_path = os.path.join('compiled_contract', 'HashStorage_sol_HashStorage.abi')

with open(contract_abi_path, 'r') as file:
    contract_abi = json.load(file)

contract_address = '0xContractAddress'  # address of where the contract was deployed
contract = w3.eth.contract(address=contract_address, abi=contract_abi)


# this is assuming we use our own account for all transactions and the user pays us with other means
@app.post("/store-hash/")
async def store_hash(hash_value: str):
    try:
        account_address = '0xOurAccountAddress'
        private_key = os.getenv('PRIVATE_KEY')

        nonce = w3.eth.getTransactionCount(account_address)
        transaction = contract.functions.storeHash(hash_value).buildTransaction({
            'from': account_address,
            'nonce': nonce,
            'gas': 2000000,
            'gasPrice': w3.eth.gas_price
        })

        signed_txn = w3.eth.account.sign_transaction(transaction, private_key=private_key)
        tx_hash = w3.eth.sendRawTransaction(signed_txn.rawTransaction)
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

        block = w3.eth.getBlock(tx_receipt.blockHash)
        timestamp = block.timestamp

        return {"tx_hash": tx_receipt.transactionHash.hex(), "timestamp": timestamp, "status": "Hash stored"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/verify-hash/")
async def verify_hash(tx_hash: str):
    try:
        tx_receipt = w3.eth.getTransactionReceipt(tx_hash)
        if not tx_receipt:
            raise HTTPException(status_code=404, detail="Transaction not found")

        event = contract.events.HashStored()
        event_data = event.processReceipt(tx_receipt)
        if not event_data:
            raise HTTPException(status_code=404, detail="No event found in the transaction")

        event_args = event_data[0]['args']
        return {"hash": event_args['hash'], "timestamp": event_args['timestamp'], "index": event_args['index']}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)