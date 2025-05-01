#!/usr/bin/env python3
"""Metrics calculation for evaluating search results.

This module provides utilities for calculating precision, recall,
and other metrics for evaluating search results.
"""

import logging
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import numpy as np


class SearchMetrics:
    """Metrics for evaluating search results."""
    
    def __init__(self, truth_ids: Set[str], result_ids: Set[str]):
        """Initialize metrics with truth and result sets.
        
        Args:
            truth_ids: Set of IDs for truth records
            result_ids: Set of IDs for result records
        """
        self.truth_ids = truth_ids
        self.result_ids = result_ids
        self.true_positives = truth_ids.intersection(result_ids)
        self.false_positives = result_ids - truth_ids
        self.false_negatives = truth_ids - result_ids
        
        self.logger = logging.getLogger(self.__class__.__name__)
        self._calculate_metrics()
    
    def _calculate_metrics(self) -> None:
        """Calculate all metrics."""
        # Basic counts
        self.tp_count = len(self.true_positives)
        self.fp_count = len(self.false_positives)
        self.fn_count = len(self.false_negatives)
        
        # Precision
        if len(self.result_ids) > 0:
            self.precision = self.tp_count / len(self.result_ids)
        else:
            self.precision = 0.0
        
        # Recall
        if len(self.truth_ids) > 0:
            self.recall = self.tp_count / len(self.truth_ids)
        else:
            self.recall = 0.0
        
        # F1 score
        if self.precision + self.recall > 0:
            self.f1_score = 2 * (self.precision * self.recall) / (self.precision + self.recall)
        else:
            self.f1_score = 0.0
    
    def get_metrics(self) -> Dict[str, float]:
        """Get a dictionary of metrics.
        
        Returns:
            Dictionary mapping metric names to values
        """
        return {
            "precision": self.precision,
            "recall": self.recall,
            "f1_score": self.f1_score,
            "true_positives": self.tp_count,
            "false_positives": self.fp_count,
            "false_negatives": self.fn_count,
        }
    
    def log_metrics(self) -> None:
        """Log metrics for debugging and reporting."""
        metrics = self.get_metrics()
        self.logger.info("Search Results Metrics:")
        for name, value in metrics.items():
            self.logger.info(f"  {name}: {value}")
    
    def __str__(self) -> str:
        """Get a string representation of the metrics.
        
        Returns:
            String representation
        """
        metrics = self.get_metrics()
        lines = [f"{name}: {value:.4f}" for name, value in metrics.items()]
        return "\n".join(lines)


class RankedSearchMetrics(SearchMetrics):
    """Metrics for evaluating ranked search results."""
    
    def __init__(self, truth_ids: Set[str], result_ids: List[str], relevance_scores: Optional[Dict[str, float]] = None):
        """Initialize metrics with truth and ranked result lists.
        
        Args:
            truth_ids: Set of IDs for truth records
            result_ids: List of IDs for ranked result records
            relevance_scores: Optional dictionary mapping result IDs to relevance scores
        """
        self.ranked_result_ids = result_ids
        self.relevance_scores = relevance_scores or {}
        super().__init__(truth_ids, set(result_ids))
        
        # Calculate rank-based metrics
        self._calculate_rank_metrics()
    
    def _calculate_rank_metrics(self) -> None:
        """Calculate rank-based metrics."""
        # Mean reciprocal rank (MRR)
        self.mrr = self._calculate_mrr()
        
        # Mean average precision (MAP)
        self.map = self._calculate_map()
        
        # Normalized discounted cumulative gain (NDCG)
        self.ndcg = self._calculate_ndcg()
    
    def _calculate_mrr(self) -> float:
        """Calculate mean reciprocal rank.
        
        Returns:
            Mean reciprocal rank value
        """
        if not self.true_positives:
            return 0.0
        
        # Find the rank of the first relevant result
        for i, result_id in enumerate(self.ranked_result_ids):
            if result_id in self.truth_ids:
                return 1.0 / (i + 1)
        
        return 0.0
    
    def _calculate_map(self) -> float:
        """Calculate mean average precision.
        
        Returns:
            MAP value
        """
        if not self.true_positives:
            return 0.0
        
        # Calculate average precision
        relevant_count = 0
        cumulative_precision = 0.0
        
        for i, result_id in enumerate(self.ranked_result_ids):
            if result_id in self.truth_ids:
                relevant_count += 1
                precision_at_i = relevant_count / (i + 1)
                cumulative_precision += precision_at_i
        
        return cumulative_precision / len(self.truth_ids)
    
    def _calculate_ndcg(self) -> float:
        """Calculate normalized discounted cumulative gain.
        
        Returns:
            NDCG value
        """
        if not self.true_positives:
            return 0.0
        
        # Calculate DCG
        dcg = 0.0
        for i, result_id in enumerate(self.ranked_result_ids):
            if result_id in self.truth_ids:
                # Get relevance score (default to 1.0 for binary relevance)
                rel = self.relevance_scores.get(result_id, 1.0)
                # DCG formula: rel / log2(i + 2)
                dcg += rel / np.log2(i + 2)
        
        # Calculate ideal DCG (IDCG)
        # Sort truth IDs by relevance score
        sorted_truth_ids = sorted(
            self.truth_ids,
            key=lambda id_: self.relevance_scores.get(id_, 1.0),
            reverse=True
        )
        
        idcg = 0.0
        for i, truth_id in enumerate(sorted_truth_ids):
            rel = self.relevance_scores.get(truth_id, 1.0)
            idcg += rel / np.log2(i + 2)
        
        if idcg == 0:
            return 0.0
        
        return dcg / idcg
    
    def get_metrics(self) -> Dict[str, float]:
        """Get a dictionary of metrics.
        
        Returns:
            Dictionary mapping metric names to values
        """
        base_metrics = super().get_metrics()
        rank_metrics = {
            "mrr": self.mrr,
            "map": self.map,
            "ndcg": self.ndcg,
        }
        return {**base_metrics, **rank_metrics}