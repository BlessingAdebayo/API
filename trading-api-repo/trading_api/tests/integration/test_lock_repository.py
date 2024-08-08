from trading_api.algorithm.models.algorithm import (
    AlgorithmId,
    AlgorithmTransaction,
    AlgorithmWasLocked,
    NewAlgorithmLock,
)
from trading_api.algorithm.models.crypto import TransactionHash


def test_one_lock_per_algorithm(algorithm_lock_repository):
    repository = algorithm_lock_repository
    algorithm_one = AlgorithmId(public_address="123456")
    algorithm_two = AlgorithmId(public_address="123456789")

    lock = repository.get_algorithm_lock(algorithm_one)
    assert isinstance(lock, NewAlgorithmLock)

    second_lock = repository.get_algorithm_lock(algorithm_one)
    assert isinstance(second_lock, AlgorithmWasLocked)

    other_algorithm_lock = repository.get_algorithm_lock(algorithm_two)
    assert isinstance(other_algorithm_lock, NewAlgorithmLock)

    third_lock = repository.get_algorithm_lock(algorithm_one)
    assert isinstance(third_lock, AlgorithmWasLocked)

    repository.remove_algorithm_lock(algorithm_one)

    fourth_lock = repository.get_algorithm_lock(algorithm_one)
    assert isinstance(fourth_lock, NewAlgorithmLock)


def test_one_lock_per_algorithm_and_symbol(algorithm_lock_repository):
    repository = algorithm_lock_repository
    algorithm_one = AlgorithmId(public_address="123456")
    algorithm_two = AlgorithmId(public_address="123456789")

    def make_locks():
        for lock in [
            repository.get_algorithm_lock(algorithm_one, symbol="ETH"),
            repository.get_algorithm_lock(algorithm_one, symbol="BTC"),
            repository.get_algorithm_lock(algorithm_one),
            repository.get_algorithm_lock(algorithm_two, symbol="ETH"),
            repository.get_algorithm_lock(algorithm_two, symbol="BTC"),
            repository.get_algorithm_lock(algorithm_two),
        ]:
            yield lock

    for lock in make_locks():
        assert isinstance(lock, NewAlgorithmLock)
    for lock in make_locks():
        assert isinstance(lock, AlgorithmWasLocked)


def test_persist_tx_hash_per_symbol(algorithm_lock_repository):
    repository = algorithm_lock_repository
    algorithm_one = AlgorithmId(public_address="123456")
    algorithm_two = AlgorithmId(public_address="123456789")
    transaction_hash = TransactionHash(value="ABCDEFEG#9023480234")
    transaction_hash_two = TransactionHash(value="DEFOIEHFJOIEHI#9438590324509")

    lock = repository.get_algorithm_lock(algorithm_one)
    assert isinstance(lock, NewAlgorithmLock)

    repository.persist_algorithm_transaction(
        algorithm_transaction=AlgorithmTransaction(algorithm_id=algorithm_one, transaction_hash=transaction_hash)
    )
    repository.persist_algorithm_transaction(
        algorithm_transaction=AlgorithmTransaction(algorithm_id=algorithm_two, transaction_hash=transaction_hash_two),
        symbol="ETH",
    )

    retrieved_hash_one = repository.get_algorithm_transaction_hash(algorithm_id=algorithm_one)
    assert retrieved_hash_one.value == transaction_hash.value

    retrieved_hash_two = repository.get_algorithm_transaction_hash(algorithm_id=algorithm_two)
    assert retrieved_hash_two is None

    retrieved_hash_two = repository.get_algorithm_transaction_hash(algorithm_id=algorithm_two, symbol="ETH")
    assert retrieved_hash_two.value == transaction_hash_two.value


def test_persist_transaction_hashes(algorithm_lock_repository):
    repository = algorithm_lock_repository
    algorithm_one = AlgorithmId(public_address="123456")
    algorithm_two = AlgorithmId(public_address="123456789")
    transaction_hash = TransactionHash(value="ABCDEFEG#9023480234")
    transaction_hash_two = TransactionHash(value="DEFOIEHFJOIEHI#9438590324509")

    lock = repository.get_algorithm_lock(algorithm_one)
    assert isinstance(lock, NewAlgorithmLock)

    repository.persist_algorithm_transaction(
        algorithm_transaction=AlgorithmTransaction(algorithm_id=algorithm_one, transaction_hash=transaction_hash)
    )
    repository.persist_algorithm_transaction(
        algorithm_transaction=AlgorithmTransaction(algorithm_id=algorithm_two, transaction_hash=transaction_hash_two)
    )

    retrieved_hash_one = repository.get_algorithm_transaction_hash(algorithm_id=algorithm_one)
    assert retrieved_hash_one.value == transaction_hash.value

    retrieved_hash_two = repository.get_algorithm_transaction_hash(algorithm_id=algorithm_two)
    assert retrieved_hash_two.value == transaction_hash_two.value
