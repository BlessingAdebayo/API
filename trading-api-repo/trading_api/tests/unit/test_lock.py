import pytest
from hexbytes import HexBytes

from tests.utils import (
    ADDR1,
    ADDR3,
    make_algorithm_db,
    make_algorithm_transaction,
    make_buy_trade,
    make_buy_trade_v2,
    make_sell_trade,
    make_sell_trade_v2,
)
from trading_api.algorithm.lock import get_lock_symbol
from trading_api.algorithm.models.algorithm import AlgorithmId, AlgorithmWasLocked, NewAlgorithmLock
from trading_api.algorithm.models.crypto import ChainId, TransactionHash
from trading_api.algorithm.repositories.algorithm import InMemoryAlgorithmRepository
from trading_api.algorithm.repositories.lock import SYMBOL_V1
from trading_api.algorithm.trade import retrieve_lock


@pytest.mark.parametrize(
    "trade,expected",
    [
        (make_buy_trade(), SYMBOL_V1),
        (make_sell_trade(), SYMBOL_V1),
        (make_sell_trade_v2(), "BTC"),
        (make_sell_trade_v2(symbol="ETH"), "ETH"),
        (make_buy_trade_v2(), "BTC"),
        (make_buy_trade_v2(), "BTC"),
        (make_buy_trade_v2(symbol="ETH"), "ETH"),
    ],
)
def test_retrieve_lock_symbol(trade, expected):
    r = get_lock_symbol(trade)

    assert r == expected


def test_retrieve_lock(lock_repository, in_memory_w3, transaction_repository, algorithm_repository):
    trade = make_buy_trade()
    lock = retrieve_lock(
        lock_repository,
        trade=trade,
        web3_provider=in_memory_w3,
        trading_transaction_repository=transaction_repository,
        algorithm_repository=algorithm_repository,
    )

    assert isinstance(lock, NewAlgorithmLock)
    assert lock.algorithm_id.public_address == ADDR1


def test_algorithm_is_locked(
    lock_repository, in_memory_w3, transaction_repository, algorithm_repository: InMemoryAlgorithmRepository
):
    trading_contract_address = ADDR1
    algorithm_id = AlgorithmId(public_address=trading_contract_address)
    algorithm_repository.upsert_algorithm(
        algorithm=make_algorithm_db(trading_contract_address=trading_contract_address)
    )
    trade = make_buy_trade(trading_contract_address=trading_contract_address)
    transaction = make_algorithm_transaction(algorithm_id)

    lock_repository.get_algorithm_lock(algorithm_id)
    lock_repository.persist_algorithm_transaction(algorithm_transaction=transaction)

    lock = retrieve_lock(
        lock_repository,
        trade=trade,
        web3_provider=in_memory_w3,
        trading_transaction_repository=transaction_repository,
        algorithm_repository=algorithm_repository,
    )

    assert isinstance(lock, AlgorithmWasLocked)
    assert lock == AlgorithmWasLocked(
        lock=NewAlgorithmLock(algorithm_id=AlgorithmId(public_address=trading_contract_address), symbol=SYMBOL_V1),
        transaction_hash=TransactionHash(value=ADDR3),
    )


def test_algorithm_is_locked_but_unlocked(
    lock_repository, eth_tester, in_memory_w3, transaction_repository, algorithm_repository
):
    trading_contract_address = ADDR1
    algorithm_id = AlgorithmId(public_address=trading_contract_address)
    algorithm_repository.upsert_algorithm(
        algorithm=make_algorithm_db(trading_contract_address=trading_contract_address)
    )
    trade = make_buy_trade(trading_contract_address=trading_contract_address)

    w3 = in_memory_w3.get_web3(chain=ChainId.RTN)
    tx_hash = w3.eth.send_transaction(
        {
            "to": eth_tester.get_accounts()[0],
            "from": w3.eth.coinbase,
            "value": 12345,
            "gas": 1_000_000,
            "gasPrice": w3.toWei(50, "gwei"),
            "nonce": 0,
        }
    )
    tx_receipt = w3.eth.wait_for_transaction_receipt(HexBytes(tx_hash), timeout=0)
    assert tx_receipt["status"] == 1

    transaction = make_algorithm_transaction(algorithm_id, hash_value=tx_hash.hex())

    lock_repository.get_algorithm_lock(algorithm_id)
    lock_repository.persist_algorithm_transaction(algorithm_transaction=transaction)

    lock = retrieve_lock(
        lock_repository,
        trade=trade,
        web3_provider=in_memory_w3,
        trading_transaction_repository=transaction_repository,
        algorithm_repository=algorithm_repository,
    )

    assert isinstance(lock, NewAlgorithmLock)
    assert lock == NewAlgorithmLock(algorithm_id=AlgorithmId(public_address=trading_contract_address), symbol=SYMBOL_V1)
