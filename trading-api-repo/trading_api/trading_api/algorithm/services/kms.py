import logging
import uuid
from abc import ABC, abstractmethod
from collections import namedtuple
from concurrent.futures import ThreadPoolExecutor
from typing import Iterator, Tuple, Union

import asn1
from boto3 import Session
from Crypto.Hash import keccak
from cytoolz import dissoc, merge, pipe
from cytoolz.curried import partial
from eth_account import Account
from eth_account._utils.legacy_transactions import (
    TRANSACTION_DEFAULTS,
    UnsignedTransaction,
    chain_id_to_v,
    encode_transaction,
)
from eth_account._utils.validation import LEGACY_TRANSACTION_FORMATTERS
from eth_account.datastructures import SignedTransaction
from eth_typing import ChecksumAddress, HexStr
from eth_utils.curried import apply_formatters_to_dict
from hexbytes import HexBytes
from web3 import Web3
from web3.contract import Contract

from trading_api import Stage
from trading_api.algorithm.models.address import AddressKeyPair
from trading_api.algorithm.models.crypto import ChainId
from trading_api.algorithm.repositories.key import KeyRepository
from trading_api.algorithm.services.web3 import Web3Provider

logger = logging.getLogger(__name__)

RSV = namedtuple("RSV", ["r", "s", "v"])
PublicKey = namedtuple("PublicKey", ["der", "address", "key"])
KEYId = namedtuple("KEYId", ["external", "internal", "address"])
SignedMaterial = namedtuple("SignedMaterial", ["signature", "message_hash", "rsv"])


class KMSClient:
    def __init__(self, region_name: str, key_manager_username: str = None, key_manager_password: str = None):
        self.client = None
        self.key_manager_username = key_manager_username
        self.key_manager_password = key_manager_password
        self.region_name = region_name

    def __enter__(self):
        if self.key_manager_password is not None and self.key_manager_username is not None:
            self.client = Session(
                aws_access_key_id=self.key_manager_username,
                aws_secret_access_key=self.key_manager_password,
                region_name=self.region_name,
            ).client("kms")
            return self.client

        self.client = Session(region_name=self.region_name).client("kms")
        return self.client

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client = None


class KeyManagementService(ABC):
    @abstractmethod
    def sign_transaction(self, transaction: dict, address: ChecksumAddress, chain: ChainId) -> SignedTransaction:
        pass

    @abstractmethod
    def list_key_aliases(self) -> Iterator[str]:
        pass

    @abstractmethod
    def create_new_key(self) -> KEYId:
        pass

    @abstractmethod
    def address_to_key_alias(self, address: ChecksumAddress) -> str:
        pass

    @abstractmethod
    def key_alias_to_key_info(self, key: str) -> PublicKey:
        pass

    @abstractmethod
    def all_keyed_addresses(self) -> Iterator[AddressKeyPair]:
        pass


class LocalKeyManagementService(KeyManagementService):
    web3_provider: Web3Provider
    keys: dict[str, ChecksumAddress]

    def __init__(self, web3_provider: Web3Provider):
        self.web3_provider = web3_provider
        self.keys = {}

    def list_key_aliases(self) -> Iterator[str]:
        return iter(self.keys.keys())

    def create_new_key(self) -> KEYId:
        internal = str(uuid.uuid4())
        external = str(uuid.uuid4())  # unused

        self.keys[internal] = (
            address := Web3.toChecksumAddress(Account().create("KEYSMASH FJAFJKLDSKF7JKFDJ 1530").address)
        )
        return KEYId(external, internal, address)

    def sign_transaction(self, transaction: dict, address: ChecksumAddress, chain: ChainId) -> SignedTransaction:
        return self.web3_provider.get_account(address).sign_transaction(transaction)

    def address_to_key_alias(self, address: ChecksumAddress) -> str:
        for key, value in self.keys.items():
            if value == address:
                return key
        raise ValueError(f"couldnt find key for {address=}")

    def key_alias_to_key_info(self, key_alias: str) -> PublicKey:
        return PublicKey("", self.keys[key_alias], "")

    def all_keyed_addresses(self) -> Iterator[AddressKeyPair]:
        yield from [
            AddressKeyPair(controller_wallet_address=controller_wallet_address, key_alias=key_alias)
            for controller_wallet_address, key_alias in self.keys.items()
        ]


class AWSKeyManagementService(KeyManagementService):
    """
    - creation of wallets and corresponding keys in AWS KMS
    - Signing of a transaction using the AWS KMS

    Implementation based on:
    https://github.com/lucashenning/aws-kms-ethereum-signing/tree/a90ed8ecff8423eb21c797ff066d0aed982e08c5
    https://ethereum.stackexchange.com/questions/73192/using-aws-cloudhsm-to-sign-transactions
    https://luhenning.medium.com/the-dark-side-of-the-elliptic-curve-signing-ethereum-transactions-with-aws-kms-in-javascript-83610d9a6f81
    """

    key_repository: KeyRepository
    web3_provider: Web3Provider

    def __init__(
        self,
        web3_provider: Web3Provider,
        key_repository: KeyRepository,
        region_name: str,
        stage: Stage,
        key_manager_username: str = None,
        key_manager_password: str = None,
    ):
        self.key_repository = key_repository
        self.web3_provider = web3_provider
        self.stage = stage
        self.key_manager_username = key_manager_username
        self.key_manager_password = key_manager_password
        self.region_name = region_name

    def __client(self) -> KMSClient:
        return KMSClient(self.region_name, self.key_manager_username, self.key_manager_password)

    def sign_transaction(self, transaction: dict, address: ChecksumAddress, chain: ChainId) -> SignedTransaction:
        try:
            # get corresponding key
            key_id = self.address_to_key_alias(address)

            unsigned_transaction = self._serializable_unsigned_transaction_from_dict(transaction_dict=transaction)
            unsigned_tx_hash = unsigned_transaction.hash()

            unsigned_tx_sign = self.sign_message(chain=chain, message=unsigned_tx_hash, key_id=key_id, address=address)
            r, s, v = unsigned_tx_sign.rsv
            signed_serialized_tx = encode_transaction(unsigned_transaction, vrs=(v, r, s))

            return SignedTransaction(
                rawTransaction=HexBytes(signed_serialized_tx),
                hash=HexBytes(unsigned_tx_hash),  # Note this is *not* the correct hash.
                r=r,
                s=s,
                v=v,
            )
        except Exception as e:
            logger.error(f"failed signing {transaction=} for {address=}: {e} ({e.__class__})")
            raise e

    def all_keyed_addresses(self) -> Iterator[AddressKeyPair]:  # can also be retrieved from DB
        for key_alias in self.list_key_aliases():
            address = self.key_repository.get_address_by_key_alias(key_alias=key_alias)
            if address is not None:
                yield AddressKeyPair(controller_wallet_address=Web3.toChecksumAddress(address), key_alias=key_alias)

            yield AddressKeyPair(
                controller_wallet_address=Web3.toChecksumAddress(
                    self.key_alias_to_key_info(key_alias=key_alias).address
                ),
                key_alias=key_alias,
            )

    def key_alias_to_key_info(self, key_alias: str) -> PublicKey:
        try:
            with self.__client() as client:
                der = client.get_public_key(
                    KeyId=f"alias/{key_alias}",
                )["PublicKey"]

                pub_key = self._decode_der_to_key(der)
                address = self._key2address(pub_key)
                return PublicKey(der, address, pub_key)
        except Exception as e:
            logger.error(f"failed fetching {key_alias=}: {e} ({e.__class__})")
            raise e

    def list_key_aliases(self) -> Iterator[str]:
        try:
            with self.__client() as client:
                next_marker = None
                while True:
                    response = client.list_aliases(
                        Limit=100, **({} if next_marker is None else dict(Marker=next_marker))
                    )

                    yield from self._filter_retrieved_aliases(client, response)

                    if not response["Truncated"]:
                        break
                    next_marker = response["NextMarker"]

        except Exception as e:
            logger.error(f"failed fetching keynames: {e} ({e.__class__})")
            raise e

    def _filter_retrieved_aliases(self, client, response):

        # define result set
        results = []

        # exclude other stages
        aliases = [item["AliasName"] for item in response["Aliases"] if self.stage.value in item["AliasName"]]

        # Exclude all deleted aliases:
        def check_alias(alias_: str):
            try:
                alias_response = client.describe_key(KeyId=alias_)["KeyMetadata"]
                if alias_response["Enabled"] and "DeletionDate" not in alias_response:
                    results.append(alias_.replace("alias/", ""))
            except Exception as ee:
                logger.error(f"error in checking aliases concurrently {ee} ({ee.__class__})")

        with ThreadPoolExecutor(max_workers=10) as exc:
            for alias in aliases:
                exc.submit(check_alias, alias_=alias)

        logger.info(f"filtered {len(response['Aliases'])} keys down to {len(results)} active ones.")
        return results

    def create_new_key(self) -> KEYId:
        try:
            # start client
            with self.__client() as client:
                # create the key
                key_alias = self.create_key_alias()
                response = client.create_key(
                    Description=f"key-{key_alias}",
                    KeyUsage="SIGN_VERIFY",
                    CustomerMasterKeySpec="ECC_SECG_P256K1",
                    Origin="AWS_KMS",
                    Tags=[
                        {"TagKey": "Name", "TagValue": key_alias},
                        {"TagKey": "environment", "TagValue": self.stage.value},
                    ],
                    MultiRegion=False,
                )
                # extract external id
                id_external = response["KeyMetadata"]["KeyId"]
                assert bool(
                    response["KeyMetadata"]["Enabled"]
                ), f"key with id {id_external=}, {key_alias=} came back disabled from KMS"

                # links internal and external
                client.create_alias(AliasName=f"alias/{key_alias}", TargetKeyId=id_external)

                # get corresponding address and save it
                address = self.key_alias_to_key_info(key_alias).address
                self.key_repository.add_address_key(
                    AddressKeyPair(controller_wallet_address=address, key_alias=key_alias)
                )

                logger.info(f"Created KMS key: {id_external=}, {key_alias=}, {address=}")
                # return values
                return KEYId(id_external, key_alias, address)
        except Exception as e:
            logger.error(f"failed creating key: {e} ({e.__class__})")
            raise e

    def create_key_alias(self) -> str:
        return f"controller-wallet/{self.stage.value}/{str(uuid.uuid4())}"

    def address_to_key_alias(self, address: ChecksumAddress) -> str:
        if (key := self._address_to_key_alias_via_repository(address)) is not None:
            return key
        else:
            logger.warning(
                f"couldn't find corresponding key for {address=} in keyrepository,"
                f" will try to look through KMS to find instead (might be slow)"
            )
            return self._address_to_aws_key_alias(address)

    def _address_to_key_alias_via_repository(self, address: ChecksumAddress) -> Union[str, None]:
        try:
            return self.key_repository.get_key_alias_by_address(address)
        except Exception as e:
            logger.error(f"error finding key for {address=} in keyrepository: {e} ({e.__class__})")
            return None

    def _address_to_aws_key_alias(self, address: ChecksumAddress) -> str:
        try:
            for key_alias in self.list_key_aliases():
                if Web3.toChecksumAddress(self.key_alias_to_key_info(key_alias=key_alias).address) == address:
                    logger.info("found key_alias!")
                    return key_alias
            raise KeyError(f"key_alias id for {address=} was not found anywhere in repository or in KMS")
        except Exception as e:
            logger.error(f"error finding key_alias for {address=} in KMS: {e} ({e.__class__})")
            raise e

    def sign_message(
        self, chain: ChainId, message: bytes, key_id: str, address: str, needs_hashing=False
    ) -> SignedMaterial:

        try:
            # start client
            with self.__client() as client:
                # hash first?
                if needs_hashing:
                    message = self._hash_message(message)

                signature = client.sign(
                    KeyId=f"alias/{key_id}", Message=message, MessageType="DIGEST", SigningAlgorithm="ECDSA_SHA_256"
                )["Signature"]

                recovered_address, rsv = self._recover_rsv_from_transaction(
                    address, message, signature, self.web3_provider.get_ecr_contract(chain=chain)
                )
                recovered_address = Web3.toChecksumAddress(recovered_address)

                assert recovered_address == address, f"{recovered_address=} and {address=} don't match"

                return SignedMaterial(signature, message, rsv)
        except Exception as e:
            logger.error(f"failed signing {message=} with key {key_id=}: {e} ({e.__class__})")
            raise e

    def verify_message(self, message: bytes, key_id: str, signature: bytes, needs_hashing=False) -> bool:
        try:
            # start client
            with self.__client() as client:
                # hash first
                if needs_hashing:
                    message = self._hash_message(message)
                return client.verify(
                    KeyId=f"alias/{key_id}",
                    Message=message,
                    MessageType="DIGEST",
                    Signature=signature,
                    SigningAlgorithm="ECDSA_SHA_256",
                )["SignatureValid"]
        except Exception as e:
            logger.error(f"failed verifying {message=} with {key_id=} and {signature=}: {e} ({e.__class__})")
            raise e

    def _recover_rsv_from_transaction(
        self, contract_address: str, transaction_hash: bytes, transaction_signature: bytes, ecr_contract: Contract
    ) -> Tuple[HexStr, RSV]:

        logger.info(f"TxHash: {transaction_hash=}")
        logger.info(f"Made {transaction_signature.hex()=}")

        r, s = self._find_r_s_from_signature(transaction_signature)
        logger.info(f"Found values: {r=} {s=}")

        recovered_address, v = self._find_right_pubkey((r, s), transaction_hash, contract_address, ecr_contract)
        logger.info(f"Found values r,s,v {r=} {s=} {v=}")

        return recovered_address, RSV(r, s, v)

    def _find_right_pubkey(
        self, rs: Tuple[int, int], transaction_hash: bytes, contract_address: str, ecr_contract: Contract
    ) -> Tuple[HexStr, int]:
        v = 27
        address = self._recover_address((*rs, v), transaction_hash, ecr_contract)
        if address == contract_address:
            logger.debug(f"adress with v=27 equals original_adress {address=} {contract_address=}")
            return address, v

        v = 28
        address = self._recover_address((*rs, v), transaction_hash, ecr_contract)
        assert address == contract_address, "original adresss wasn't recovered"
        logger.debug(
            f"adress with v=28 equals original_adress {address=} {contract_address=}",
        )

        return address, v

    def _recover_address(self, rsv: Tuple[int, int, int], transaction_hash: bytes, ecr_contract: Contract) -> HexStr:
        ec_recover_args = (
            transaction_hash,
            rsv[2],
            self._to_32byte_hex(rsv[0]),
            self._to_32byte_hex(rsv[1]),
        )

        result_pub_key: str = ecr_contract.functions.ecr(*ec_recover_args).call()
        logger.info(f"{ec_recover_args=}")
        logger.info(f"contract.functions.ecr(*ec_recover_args).call()={result_pub_key} {type(result_pub_key)=}")
        recovered_address = Web3.toHex(hexstr=result_pub_key)  # type: ignore
        recovered_address = Web3.toChecksumAddress(recovered_address)
        logger.info(f"Recovered address={recovered_address} {rsv[2]=}")

        return recovered_address

    def _decode_der_to_key(self, der: bytes) -> bytes:
        decoder = asn1.Decoder()
        decoder.start(der)
        public_key = self._decode_key(input_stream=decoder)
        logger.info(f"Found {public_key=}")
        return public_key

    def _find_r_s_from_signature(self, signature: bytes) -> Tuple[int, int]:
        decoder = asn1.Decoder()
        decoder.start(signature)
        signature_values = self._decode_signature(decoder)
        r, s = signature_values
        r, s = self._transform_rs(r, s)
        return r, s

    @staticmethod
    def _serializable_unsigned_transaction_from_dict(transaction_dict):
        transaction_dict = dissoc(transaction_dict, "chainId")

        filled_transaction = pipe(
            transaction_dict,
            dict,
            partial(merge, TRANSACTION_DEFAULTS),
            chain_id_to_v,
            apply_formatters_to_dict(LEGACY_TRANSACTION_FORMATTERS),
        )
        serializer = UnsignedTransaction
        return serializer.from_dict(filled_transaction)

    @staticmethod
    def _key2address(public_key: bytes) -> str:
        logger.info(f"{public_key.hex()=}")

        public_key = public_key[2:]
        k = keccak.new(digest_bits=256)
        k.update(public_key)
        public_key = k.digest()[-20:]

        address = "0x" + public_key.hex()
        is_address = Web3.isAddress(address)

        assert is_address
        logger.info(f"{address=} is a valid adress: {is_address=}")

        return Web3.toChecksumAddress(address)

    @staticmethod
    def _hash_message(message: bytes) -> bytes:
        k = keccak.new(digest_bits=256)
        k.update(message)
        message_hash = k.digest()
        return message_hash

    @staticmethod
    def _transform_rs(r: int, s: int) -> Tuple[int, int]:
        # Warning: overflow risk.
        # Although I read that this doesn't happen for python ints:
        # https://mortada.net/can-integer-operations-overflow-in-python.html
        # If it does, use a Decimal object
        secp_256k_1N = int("fffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd0364141", 16)
        half = secp_256k_1N / 2

        # Because of EIP-2 not all elliptic curve signatures are accepted
        # the value of s needs to be SMALLER than half of the curve
        # i.e. we need to flip s if it's greater than half of the curve
        if s > half:
            tempsig = str(r) + str(s)
            logger.debug(f"s is on the wrong side of the curve... flipping - tempsig: {tempsig} length: {len(tempsig)}")
            # According to EIP2 https://github.com/ethereum/EIPs/blob/master/EIPS/eip-2.md
            # if s < half the curve we need to invert it
            # s = curve.n - s
            s = secp_256k_1N - s
            logger.debug(f"New s: {s=}")

        return r, s

    @staticmethod
    def _decode_key(input_stream):
        """Decode ASN.1 data and find the BitString."""
        while not input_stream.eof():
            tag = input_stream.peek()
            if tag.typ == asn1.Types.Primitive:
                tag, value = input_stream.read()

                if tag.nr == asn1.Numbers.BitString:
                    return value

            elif tag.typ == asn1.Types.Constructed:
                input_stream.enter()
                return_value = AWSKeyManagementService._decode_key(input_stream)
                if return_value:
                    return return_value

                input_stream.leave()

    @staticmethod
    def _to_32byte_hex(val):
        return Web3.toHex(Web3.toBytes(val).rjust(32, b"\0"))

    @staticmethod
    def _decode_signature(input_stream, return_values=None):
        """Decode ASN.1 data and find the values r and s."""
        if return_values is None:
            return_values = []

        while not input_stream.eof():
            tag = input_stream.peek()
            if tag.typ == asn1.Types.Primitive:
                tag, value = input_stream.read()

                if tag.nr == asn1.Numbers.Integer:
                    return_values.append(value)

            elif tag.typ == asn1.Types.Constructed:
                input_stream.enter()
                AWSKeyManagementService._decode_signature(input_stream, return_values)

                input_stream.leave()

        return return_values
