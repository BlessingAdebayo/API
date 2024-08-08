import math

from eth_typing import ChecksumAddress

from trading_api.algorithm.models.algorithm import AlgorithmId
from trading_api.algorithm.models.trade import TransactionPage
from trading_api.algorithm.repositories.transaction import TransactionRepository


def handle_transaction_list_request(
    trading_wallet_address: ChecksumAddress, skip: int, limit: int, transaction_repository: TransactionRepository
) -> TransactionPage:
    algorithm_id = AlgorithmId(public_address=trading_wallet_address)
    transactions = list(transaction_repository.get_transactions_paginated(algorithm_id, skip=skip, limit=limit))
    total = transaction_repository.get_transaction_count(algorithm=algorithm_id)

    return TransactionPage(
        transactions=transactions,
        page=math.floor(skip / limit),
        page_size=limit,
        total_pages=math.ceil(total / limit),
        total=total,
    )
