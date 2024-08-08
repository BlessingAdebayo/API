from trading_api.algorithm.models.algorithm import AlgorithmInDB, TradingContractVersion


def test_parse_algorithm_1_0():
    d = {
        "trading_contract_address": "0x81Aa010b21d020d956986b7aF5E7ABFcc9E23233",
        "chain_id": "BSC",
        "controller_wallet_address": "0x64F7988695885ea70f1626610714D5958b54d8E3",
        "disabled": False,
        "hashed_password": "$2b$12...",
        "trading_contract_version": "1.0",
    }

    algo = AlgorithmInDB.parse_obj(d)

    assert isinstance(algo, AlgorithmInDB)
    assert algo.trading_contract is not None
    assert algo.trading_contract.version == TradingContractVersion.V1_0


def test_parse_algorithm_1_1():
    d = {
        "trading_contract_address": "0x81Aa010b21d020d956986b7aF5E7ABFcc9E23233",
        "chain_id": "BSC",
        "controller_wallet_address": "0x64F7988695885ea70f1626610714D5958b54d8E3",
        "disabled": False,
        "hashed_password": "$2b$12...",
        "trading_contract_version": "1.1",
    }

    algo = AlgorithmInDB.parse_obj(d)

    assert isinstance(algo, AlgorithmInDB)
    assert algo.trading_contract is not None
    assert algo.trading_contract.version == TradingContractVersion.V1_1


def test_parse_algorithm_2_0():
    d = {
        "trading_contract_address": "0x81Aa010b21d020d956986b7aF5E7ABFcc9E23233",
        "chain_id": "BSC",
        "controller_wallet_address": "0x64F7988695885ea70f1626610714D5958b54d8E3",
        "disabled": False,
        "hashed_password": "$2b$12...",
        "trading_contract": {"version": "2.0"},
    }

    algo = AlgorithmInDB.parse_obj(d)

    assert isinstance(algo, AlgorithmInDB)
    assert algo.trading_contract is not None
    assert algo.trading_contract.version == TradingContractVersion.V2_0
