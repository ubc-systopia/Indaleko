#!/usr/bin/env python3
"""Dataset utilities for managing generated metadata.

This module provides utilities for working with generated metadata
datasets, including containers for storing and manipulating metadata.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from data_models.base import IndalekoBaseModel
from db.db_collections import IndalekoDBCollections


class MetadataDataset:
    """Container for a set of generated metadata records."""
    
    def __init__(self, name: str):
        """Initialize a metadata dataset.
        
        Args:
            name: Name of the dataset
        """
        self.name = name
        self.records: List[Dict[str, Any]] = []
        self.truth_records: List[Dict[str, Any]] = []
        self.filler_records: List[Dict[str, Any]] = []
        self.record_ids: Set[str] = set()
        self.truth_ids: Set[str] = set()
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def add_record(self, record: Dict[str, Any], is_truth: bool = False) -> None:
        """Add a record to the dataset.
        
        Args:
            record: Metadata record to add
            is_truth: Whether this is a truth record
        """
        record_id = record.get("_key", str(len(self.records)))
        
        if record_id in self.record_ids:
            self.logger.warning(f"Duplicate record ID: {record_id}")
            return
        
        self.records.append(record)
        self.record_ids.add(record_id)
        
        if is_truth:
            self.truth_records.append(record)
            self.truth_ids.add(record_id)
        else:
            self.filler_records.append(record)
    
    def add_records(self, records: List[Dict[str, Any]], truth_ids: Optional[Set[str]] = None) -> None:
        """Add multiple records to the dataset.
        
        Args:
            records: Metadata records to add
            truth_ids: Set of record IDs that are truth records
        """
        truth_ids = truth_ids or set()
        
        for record in records:
            record_id = record.get("_key", str(len(self.records)))
            is_truth = record_id in truth_ids
            self.add_record(record, is_truth)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the dataset.
        
        Returns:
            Dictionary of dataset statistics
        """
        return {
            "name": self.name,
            "total_records": len(self.records),
            "truth_records": len(self.truth_records),
            "filler_records": len(self.filler_records),
            "unique_record_ids": len(self.record_ids),
        }
    
    def save_to_file(self, directory: Union[str, Path], suffix: str = "") -> str:
        """Save the dataset to a file.
        
        Args:
            directory: Directory to save the file in
            suffix: Optional suffix to add to the filename
            
        Returns:
            Path to the saved file
        """
        directory = Path(directory)
        os.makedirs(directory, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.name}_{timestamp}{suffix}.json"
        filepath = directory / filename
        
        with open(filepath, "w") as f:
            json.dump({
                "name": self.name,
                "statistics": self.get_statistics(),
                "records": self.records,
                "truth_records": [r.get("_key", "") for r in self.truth_records],
            }, f, indent=2)
        
        self.logger.info(f"Saved dataset to {filepath}")
        return str(filepath)
    
    @classmethod
    def load_from_file(cls, filepath: Union[str, Path]) -> 'MetadataDataset':
        """Load a dataset from a file.
        
        Args:
            filepath: Path to the file to load
            
        Returns:
            Loaded dataset
            
        Raises:
            FileNotFoundError: If the file does not exist
            ValueError: If the file format is invalid
        """
        filepath = Path(filepath)
        
        with open(filepath, "r") as f:
            data = json.load(f)
        
        if not isinstance(data, dict) or "records" not in data or "name" not in data:
            raise ValueError(f"Invalid dataset file format: {filepath}")
        
        dataset = cls(data["name"])
        truth_ids = set(data.get("truth_records", []))
        dataset.add_records(data["records"], truth_ids)
        
        return dataset


class MetadataCollection:
    """Collection of metadata datasets for different record types."""
    
    def __init__(self, name: str = "synthetic"):
        """Initialize a metadata collection.
        
        Args:
            name: Name of the collection
        """
        self.name = name
        self.datasets: Dict[str, MetadataDataset] = {}
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def add_dataset(self, dataset_type: str, dataset: MetadataDataset) -> None:
        """Add a dataset to the collection.
        
        Args:
            dataset_type: Type of the dataset (e.g., "storage", "semantic")
            dataset: Dataset to add
        """
        self.datasets[dataset_type] = dataset
    
    def create_dataset(self, dataset_type: str, name: Optional[str] = None) -> MetadataDataset:
        """Create a new dataset and add it to the collection.
        
        Args:
            dataset_type: Type of the dataset (e.g., "storage", "semantic")
            name: Optional name for the dataset
            
        Returns:
            Created dataset
        """
        name = name or f"{dataset_type}_{self.name}"
        dataset = MetadataDataset(name)
        self.add_dataset(dataset_type, dataset)
        return dataset
    
    def get_dataset(self, dataset_type: str) -> Optional[MetadataDataset]:
        """Get a dataset by type.
        
        Args:
            dataset_type: Type of the dataset to get
            
        Returns:
            Dataset if found, None otherwise
        """
        return self.datasets.get(dataset_type)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the collection.
        
        Returns:
            Dictionary of collection statistics
        """
        return {
            "name": self.name,
            "dataset_count": len(self.datasets),
            "datasets": {
                dtype: dataset.get_statistics()
                for dtype, dataset in self.datasets.items()
            },
        }
    
    def save_to_directory(self, directory: Union[str, Path]) -> Dict[str, str]:
        """Save all datasets to a directory.
        
        Args:
            directory: Directory to save the files in
            
        Returns:
            Dictionary mapping dataset types to filepaths
        """
        directory = Path(directory)
        os.makedirs(directory, exist_ok=True)
        
        filepaths = {}
        for dataset_type, dataset in self.datasets.items():
            filepath = dataset.save_to_file(directory / dataset_type)
            filepaths[dataset_type] = filepath
        
        # Save collection metadata
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        metadata_filepath = directory / f"{self.name}_metadata_{timestamp}.json"
        with open(metadata_filepath, "w") as f:
            json.dump({
                "name": self.name,
                "timestamp": timestamp,
                "statistics": self.get_statistics(),
                "datasets": {
                    dtype: filepath
                    for dtype, filepath in filepaths.items()
                },
            }, f, indent=2)
        
        self.logger.info(f"Saved collection metadata to {metadata_filepath}")
        return filepaths