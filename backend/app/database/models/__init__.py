"""
Database models package for NeedleAi.
"""

from .api_key import ApiKey
from .chat_message import ChatMessage, MessageRoleEnum
from .chat_message_step import ChatMessageStep
from .chat_session import ChatSession
from .company import Company
from .credit_transaction import CreditTransaction, TransactionTypeEnum
from .data_import import DataImport, ImportStatusEnum, ImportTypeEnum
from .llm_call import LLMCall, LLMCallStatusEnum, LLMCallTypeEnum
from .product_intelligence import ProductIntelligence
from .review import Review
from .review_source import ReviewSource, SourceTypeEnum
from .scraping_job import JobStatusEnum, ScrapingJob
from .task_result import TaskResult
from .user import User, UserStatusEnum
from .user_credit import UserCredit
from .user_dataset import UserDataset

__all__ = [
    # Core Models
    "User",
    "ChatSession",
    "ChatMessage",
    "ChatMessageStep",
    "ApiKey",
    "TaskResult",
    "LLMCall",
    
    # Product Review Models
    "Company",
    "ReviewSource",
    "ScrapingJob",
    "Review",
    "ProductIntelligence",
    "UserCredit",
    "CreditTransaction",
    "DataImport",
    "UserDataset",

    # Enums
    "UserStatusEnum",
    "MessageRoleEnum",
    "SourceTypeEnum",
    "JobStatusEnum",
    "TransactionTypeEnum",
    "ImportTypeEnum",
    "ImportStatusEnum",
    "LLMCallTypeEnum",
    "LLMCallStatusEnum",
]
