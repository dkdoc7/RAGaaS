from .base import RetrievalStrategy
from .vector import VectorRetrievalStrategy
from .keyword import KeywordRetrievalStrategy
from .hybrid import HybridRetrievalStrategy
from .two_stage import TwoStageRetrievalStrategy
from .reranker import reranking_service

class RetrievalFactory:
    @staticmethod
    def get_strategy(strategy_name: str) -> RetrievalStrategy:
        if strategy_name == "keyword":
            return KeywordRetrievalStrategy()
        elif strategy_name == "hybrid":
            return HybridRetrievalStrategy()
        elif strategy_name == "2-stage":
            return TwoStageRetrievalStrategy()
        else:
            return VectorRetrievalStrategy()

retrieval_factory = RetrievalFactory()
