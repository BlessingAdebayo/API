from pydantic import BaseModel

from mm.domain.models import TransactionStatus


class RetrieveTransactionStatusResponse(BaseModel):
    message: TransactionStatus
