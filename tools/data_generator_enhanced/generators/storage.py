#!/usr/bin/env python3
"""
Storage metadata generator.

This module provides implementation for generating realistic storage
metadata records (POSIX attributes, file paths, etc.).
"""

import hashlib
import logging
import os
import random
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePath
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from data_models.base import IndalekoBaseModel
from db.db_collections import IndalekoDBCollections
from db.db_config import IndalekoDBConfig
from pydantic import Field

from tools.data_generator_enhanced.generators.base import BaseGenerator, StorageMetadataGenerator
from tools.data_generator_enhanced.utils.statistical import Distribution


class StorageRecord(IndalekoBaseModel):
    """Storage record model for IndalekoObjects collection."""
    
    # Required fields based on IndalekoObjects schema
    Name: str
    Path: str
    Size: int
    Volume: str
    LocalIdentifier: str
    CreationTime: float
    ModificationTime: float
    LastAccessTime: float
    
    # Optional fields with defaults
    IsDirectory: bool = False
    IsHidden: bool = False
    Extensions: List[str] = []
    SHA256: Optional[str] = None
    MD5: Optional[str] = None


class StorageMetadataGeneratorImpl(StorageMetadataGenerator):
    """Generator for storage metadata records."""
    
    def __init__(self, config: Dict[str, Any], seed: Optional[int] = None):
        """Initialize the storage metadata generator.
        
        Args:
            config: Configuration dictionary for the generator
            seed: Optional random seed for reproducible generation
        """
        super().__init__(config, seed)
        
        # Set random seed if provided
        if seed is not None:
            random.seed(seed)
        
        # Initialize distributions from config
        self.file_size_dist = Distribution.create(
            config.get("distributions", {}).get(
                "file_sizes", 
                {"type": "lognormal", "mu": 8.5, "sigma": 2.0}
            )
        )
        
        self.mod_time_dist = Distribution.create(
            config.get("distributions", {}).get(
                "modification_times",
                {"type": "normal", "mean": "now-30d", "std": "15d"}
            )
        )
        
        self.file_ext_dist = Distribution.create(
            config.get("distributions", {}).get(
                "file_extensions",
                {"type": "weighted", "values": {".pdf": 0.2, ".docx": 0.3, ".txt": 0.5}}
            )
        )
        
        # Define various distribution constants
        self.extensions_map = {
            ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            ".txt": "text/plain",
            ".html": "text/html",
            ".css": "text/css",
            ".js": "application/javascript",
            ".json": "application/json",
            ".xml": "application/xml",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".svg": "image/svg+xml",
            ".mp3": "audio/mpeg",
            ".mp4": "video/mp4",
            ".avi": "video/x-msvideo",
            ".webm": "video/webm",
            ".zip": "application/zip",
            ".gz": "application/gzip",
            ".tar": "application/x-tar",
        }
        
        # Load word lists for name generation
        self.adjectives = ["big", "small", "red", "blue", "green", "fast", "slow", 
                          "happy", "sad", "bright", "dark", "new", "old", "hot", 
                          "cold", "good", "bad", "early", "late", "high", "low", 
                          "long", "short", "wide", "narrow", "deep", "shallow", 
                          "thick", "thin", "round", "square", "smooth", "rough", 
                          "hard", "soft", "heavy", "light", "strong", "weak", 
                          "rich", "poor", "loud", "quiet", "sweet", "sour", 
                          "clean", "dirty", "brave", "afraid", "kind", "cruel", 
                          "wise", "foolish", "patient", "eager", "calm", "anxious"]
        
        self.nouns = ["time", "year", "people", "way", "day", "man", "woman", 
                      "child", "world", "life", "hand", "part", "eye", "place", 
                      "work", "week", "case", "point", "company", "number", 
                      "group", "problem", "fact", "money", "water", "month", 
                      "book", "story", "job", "night", "word", "house", "area", 
                      "family", "home", "state", "country", "school", "student", 
                      "friend", "business", "side", "kind", "head", "question", 
                      "program", "issue", "system", "car", "party", "service", 
                      "room", "market", "team", "art", "war", "project", "line"]
        
        self.business_nouns = ["report", "memo", "plan", "presentation", "analysis", 
                              "budget", "forecast", "proposal", "strategy", "review", 
                              "summary", "invoice", "contract", "agreement", "schedule", 
                              "agenda", "minutes", "draft", "guide", "specification", 
                              "manual", "policy", "procedure", "template", "checklist", 
                              "worksheet", "roadmap", "timeline", "portfolio", "inventory", 
                              "catalog", "brochure", "newsletter", "whitepaper", "case-study", 
                              "dataset", "survey", "questionnaire", "form", "chart", 
                              "diagram", "graph", "table", "list", "matrix", "profile", 
                              "certificate", "receipt", "order", "quote", "estimate", 
                              "statement", "record", "log", "history", "archive"]
        
        # Basic folder structure with common directories
        self.common_directories = [
            "/Documents",
            "/Documents/Work",
            "/Documents/Personal",
            "/Pictures",
            "/Pictures/Vacation",
            "/Pictures/Family",
            "/Music",
            "/Videos",
            "/Downloads",
            "/Desktop",
            "/Projects",
            "/Reports",
            "/Presentations",
            "/Backups",
            "/Archive",
        ]
        
        # Add subdirectories
        for base_dir in ["/Documents/Work", "/Documents/Personal", "/Projects"]:
            for year in range(2020, 2025):
                self.common_directories.append(f"{base_dir}/{year}")
        
        # Generate virtual volumes
        self.volumes = ["C:", "D:", "E:", "/home/user", "/Users/user"]
        
        # Truth generator tracks
        self.truth_list = []
    
    def generate(self, count: int) -> List[Dict[str, Any]]:
        """Generate the specified number of storage metadata records.
        
        Args:
            count: Number of records to generate
            
        Returns:
            List of generated storage metadata records
        """
        records = []
        
        # Generate directory structure first
        directories = self._generate_directories(count // 10)  # ~10% directories
        records.extend(directories)
        
        # Then generate files
        files_to_generate = count - len(directories)
        files = self._generate_files(files_to_generate, [d["Path"] for d in directories])
        records.extend(files)
        
        # Ensure we return exactly the requested number of records
        return records[:count]
    
    def generate_truth(self, count: int, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate truth records that match specific criteria.
        
        Args:
            count: Number of truth records to generate
            criteria: Criteria that the truth records must satisfy
            
        Returns:
            List of generated truth records
        """
        records = []
        
        # Process criteria to determine what kind of truth records to generate
        file_extension = criteria.get("file_extension")
        time_range = criteria.get("time_range", {})
        start_time = time_range.get("start")
        end_time = time_range.get("end")
        size_range = criteria.get("size_range", {})
        min_size = size_range.get("min")
        max_size = size_range.get("max")
        
        # Generate directories for truth records if needed
        if criteria.get("is_directory", False):
            directories = self._generate_specific_directories(count, criteria)
            records.extend(directories)
        else:
            # Generate files that match criteria
            files = self._generate_specific_files(count, criteria)
            records.extend(files)
        
        # Keep track of truth records for later evaluation
        self.truth_list.extend([r.get("_key") for r in records])
        
        return records
    
    def generate_paths(self, count: int) -> List[str]:
        """Generate realistic file paths.
        
        Args:
            count: Number of paths to generate
            
        Returns:
            List of generated file paths
        """
        paths = []
        for _ in range(count):
            # Choose a volume
            volume = random.choice(self.volumes)
            
            # Choose or generate a directory path
            if random.random() < 0.8:  # 80% use common directories
                dir_path = random.choice(self.common_directories)
            else:
                # Generate a random path with 1-3 levels
                levels = random.randint(1, 3)
                dir_parts = []
                for _ in range(levels):
                    dir_name = random.choice(self.nouns).capitalize()
                    dir_parts.append(dir_name)
                dir_path = "/" + "/".join(dir_parts)
            
            # Combine volume and path
            if volume.endswith(":"):  # Windows-style
                path = volume + dir_path.replace("/", "\\")
            else:  # Unix-style
                path = volume + dir_path
            
            paths.append(path)
        
        return paths
    
    def _generate_directories(self, count: int) -> List[Dict[str, Any]]:
        """Generate directory records.
        
        Args:
            count: Number of directory records to generate
            
        Returns:
            List of generated directory records
        """
        directories = []
        
        # First, add all common directories
        for volume in self.volumes:
            for dir_path in self.common_directories:
                # Skip if we've generated enough
                if len(directories) >= count:
                    break
                
                # Formulate complete path
                if volume.endswith(":"):  # Windows-style
                    path = volume + dir_path.replace("/", "\\")
                    name = dir_path.split("/")[-1]
                else:  # Unix-style
                    path = volume + dir_path
                    name = dir_path.split("/")[-1]
                
                # Generate times
                creation_time = self.mod_time_dist.sample() - random.uniform(0, 86400 * 30)  # Up to 30 days older
                mod_time = self.mod_time_dist.sample()
                access_time = mod_time + random.uniform(0, 86400 * 7)  # Up to 7 days newer
                
                directory = {
                    "_key": str(uuid.uuid4()),
                    "Name": name,
                    "Path": path,
                    "Size": 0,  # Directories have size 0
                    "Volume": volume,
                    "LocalIdentifier": hashlib.md5(path.encode()).hexdigest(),
                    "CreationTime": creation_time,
                    "ModificationTime": mod_time,
                    "LastAccessTime": access_time,
                    "IsDirectory": True,
                    "IsHidden": False,
                    "Extensions": []
                }
                
                directories.append(directory)
        
        # If we need more directories, generate random ones
        remaining = count - len(directories)
        if remaining > 0:
            # Generate random directories
            for _ in range(remaining):
                volume = random.choice(self.volumes)
                
                # Generate path with 1-3 levels
                levels = random.randint(1, 3)
                dir_parts = []
                for _ in range(levels):
                    dir_name = random.choice(self.nouns).capitalize()
                    dir_parts.append(dir_name)
                
                if volume.endswith(":"):  # Windows-style
                    path = volume + "\\" + "\\".join(dir_parts)
                    name = dir_parts[-1]
                else:  # Unix-style
                    path = volume + "/" + "/".join(dir_parts)
                    name = dir_parts[-1]
                
                # Generate times
                creation_time = self.mod_time_dist.sample() - random.uniform(0, 86400 * 30)
                mod_time = self.mod_time_dist.sample()
                access_time = mod_time + random.uniform(0, 86400 * 7)
                
                directory = {
                    "_key": str(uuid.uuid4()),
                    "Name": name,
                    "Path": path,
                    "Size": 0,
                    "Volume": volume,
                    "LocalIdentifier": hashlib.md5(path.encode()).hexdigest(),
                    "CreationTime": creation_time,
                    "ModificationTime": mod_time,
                    "LastAccessTime": access_time,
                    "IsDirectory": True,
                    "IsHidden": False,
                    "Extensions": []
                }
                
                directories.append(directory)
        
        return directories
    
    def _generate_files(self, count: int, directory_paths: List[str]) -> List[Dict[str, Any]]:
        """Generate file records.
        
        Args:
            count: Number of file records to generate
            directory_paths: List of existing directory paths to place files in
            
        Returns:
            List of generated file records
        """
        files = []
        
        for _ in range(count):
            # Choose a directory to place the file in
            if directory_paths and random.random() < 0.9:  # 90% use existing directories
                parent_path = random.choice(directory_paths)
            else:
                # Use a root path if no directories are available
                volume = random.choice(self.volumes)
                if volume.endswith(":"):  # Windows-style
                    parent_path = volume + "\\"
                else:  # Unix-style
                    parent_path = volume + "/"
            
            # Generate file name
            file_name = self._generate_file_name()
            
            # Get full path
            if parent_path.endswith("\\") or parent_path.endswith("/"):
                path = parent_path + file_name
            else:
                if "\\" in parent_path:  # Windows-style
                    path = parent_path + "\\" + file_name
                else:  # Unix-style
                    path = parent_path + "/" + file_name
            
            # Determine volume
            if ":" in path:
                volume = path.split(":")[0] + ":"
            else:
                volume = path.split("/")[1]
                volume = "/" + volume
            
            # Generate file size (log-normal distribution)
            size = int(self.file_size_dist.sample())
            
            # Generate times
            creation_time = self.mod_time_dist.sample() - random.uniform(0, 86400 * 30)
            mod_time = self.mod_time_dist.sample()
            access_time = mod_time + random.uniform(0, 86400 * 7)
            
            # Determine extension
            extension = None
            if "." in file_name:
                extension = "." + file_name.split(".")[-1].lower()
            
            file_record = {
                "_key": str(uuid.uuid4()),
                "Name": file_name,
                "Path": path,
                "Size": size,
                "Volume": volume,
                "LocalIdentifier": hashlib.md5(path.encode()).hexdigest(),
                "CreationTime": creation_time,
                "ModificationTime": mod_time,
                "LastAccessTime": access_time,
                "IsDirectory": False,
                "IsHidden": random.random() < 0.05,  # 5% chance to be hidden
                "Extensions": [extension] if extension else []
            }
            
            files.append(file_record)
        
        return files
    
    def _generate_specific_directories(self, count: int, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate directory records that match specific criteria.
        
        Args:
            count: Number of directory records to generate
            criteria: Criteria that the directories must satisfy
            
        Returns:
            List of generated directory records
        """
        directories = []
        
        # Extract criteria
        time_range = criteria.get("time_range", {})
        start_time = time_range.get("start")
        end_time = time_range.get("end")
        name_pattern = criteria.get("name_pattern")
        
        for _ in range(count):
            # Choose a volume based on criteria
            if criteria.get("volume"):
                volume = criteria.get("volume")
            else:
                volume = random.choice(self.volumes)
            
            # Generate name based on criteria
            if name_pattern:
                name = self._generate_name_from_pattern(name_pattern)
            else:
                name = random.choice(self.nouns).capitalize()
            
            # Generate path
            if criteria.get("parent_path"):
                parent_path = criteria.get("parent_path")
                if volume.endswith(":"):  # Windows-style
                    path = f"{volume}\\{parent_path}\\{name}".replace("/", "\\")
                else:  # Unix-style
                    path = f"{volume}/{parent_path}/{name}"
            else:
                if volume.endswith(":"):  # Windows-style
                    path = f"{volume}\\{name}"
                else:  # Unix-style
                    path = f"{volume}/{name}"
            
            # Generate times based on criteria
            if start_time and end_time:
                creation_time = random.uniform(start_time, end_time - 86400)  # One day before end time at latest
                mod_time = random.uniform(creation_time, end_time)
                access_time = random.uniform(mod_time, end_time + 86400)  # One day after end time at most
            else:
                creation_time = self.mod_time_dist.sample() - random.uniform(0, 86400 * 30)
                mod_time = self.mod_time_dist.sample()
                access_time = mod_time + random.uniform(0, 86400 * 7)
            
            directory = {
                "_key": str(uuid.uuid4()),
                "Name": name,
                "Path": path,
                "Size": 0,
                "Volume": volume,
                "LocalIdentifier": hashlib.md5(path.encode()).hexdigest(),
                "CreationTime": creation_time,
                "ModificationTime": mod_time,
                "LastAccessTime": access_time,
                "IsDirectory": True,
                "IsHidden": criteria.get("is_hidden", False),
                "Extensions": []
            }
            
            directories.append(directory)
        
        return directories
    
    def _generate_specific_files(self, count: int, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate file records that match specific criteria.
        
        Args:
            count: Number of file records to generate
            criteria: Criteria that the files must satisfy
            
        Returns:
            List of generated file records
        """
        files = []
        
        # Extract criteria
        time_range = criteria.get("time_range", {})
        start_time = time_range.get("start")
        end_time = time_range.get("end")
        size_range = criteria.get("size_range", {})
        min_size = size_range.get("min")
        max_size = size_range.get("max")
        file_extension = criteria.get("file_extension")
        name_pattern = criteria.get("name_pattern")
        parent_paths = criteria.get("parent_paths", [])
        
        for _ in range(count):
            # Choose a directory to place the file in
            if parent_paths:
                parent_path = random.choice(parent_paths)
            else:
                # Use a root path
                volume = criteria.get("volume", random.choice(self.volumes))
                if volume.endswith(":"):  # Windows-style
                    parent_path = volume + "\\"
                else:  # Unix-style
                    parent_path = volume + "/"
            
            # Generate file name based on criteria
            if name_pattern:
                base_name = self._generate_name_from_pattern(name_pattern)
                if file_extension:
                    file_name = f"{base_name}{file_extension}"
                else:
                    file_name = base_name
            else:
                if file_extension:
                    # Generate name with specific extension
                    base_name = self._generate_base_name()
                    file_name = f"{base_name}{file_extension}"
                else:
                    # Generate name with random extension
                    file_name = self._generate_file_name()
            
            # Get full path
            if parent_path.endswith("\\") or parent_path.endswith("/"):
                path = parent_path + file_name
            else:
                if "\\" in parent_path:  # Windows-style
                    path = parent_path + "\\" + file_name
                else:  # Unix-style
                    path = parent_path + "/" + file_name
            
            # Determine volume
            if ":" in path:
                volume = path.split(":")[0] + ":"
            else:
                parts = path.split("/")
                if len(parts) > 1:
                    volume = "/" + parts[1]
                else:
                    volume = "/"
            
            # Generate file size based on criteria
            if min_size is not None and max_size is not None:
                size = random.randint(min_size, max_size)
            else:
                size = int(self.file_size_dist.sample())
            
            # Generate times based on criteria
            if start_time and end_time:
                creation_time = random.uniform(start_time, end_time - 86400)  # One day before end time at latest
                mod_time = random.uniform(creation_time, end_time)
                access_time = random.uniform(mod_time, end_time + 86400)  # One day after end time at most
            else:
                creation_time = self.mod_time_dist.sample() - random.uniform(0, 86400 * 30)
                mod_time = self.mod_time_dist.sample()
                access_time = mod_time + random.uniform(0, 86400 * 7)
            
            # Determine extension
            extension = None
            if "." in file_name:
                extension = "." + file_name.split(".")[-1].lower()
            
            file_record = {
                "_key": str(uuid.uuid4()),
                "Name": file_name,
                "Path": path,
                "Size": size,
                "Volume": volume,
                "LocalIdentifier": hashlib.md5(path.encode()).hexdigest(),
                "CreationTime": creation_time,
                "ModificationTime": mod_time,
                "LastAccessTime": access_time,
                "IsDirectory": False,
                "IsHidden": criteria.get("is_hidden", False),
                "Extensions": [extension] if extension else []
            }
            
            files.append(file_record)
        
        return files
    
    def _generate_file_name(self) -> str:
        """Generate a realistic file name with extension.
        
        Returns:
            Generated file name
        """
        extension = self.file_ext_dist.sample()
        base_name = self._generate_base_name()
        return f"{base_name}{extension}"
    
    def _generate_base_name(self) -> str:
        """Generate a base file name without extension.
        
        Returns:
            Generated base name
        """
        name_type = random.choices(
            ["adjective_noun", "business", "date_prefixed", "numeric_prefixed"],
            weights=[0.4, 0.3, 0.2, 0.1]
        )[0]
        
        if name_type == "adjective_noun":
            adjective = random.choice(self.adjectives).capitalize()
            noun = random.choice(self.nouns).capitalize()
            return f"{adjective}{noun}"
        
        elif name_type == "business":
            doc_type = random.choice(self.business_nouns).capitalize()
            topic = random.choice(self.nouns).capitalize()
            date = datetime.now() - timedelta(days=random.randint(0, 365))
            date_str = date.strftime("%Y%m%d")
            return f"{doc_type}_{topic}_{date_str}"
        
        elif name_type == "date_prefixed":
            topic = random.choice(self.nouns).capitalize()
            date = datetime.now() - timedelta(days=random.randint(0, 365))
            date_str = date.strftime("%Y-%m-%d")
            return f"{date_str}_{topic}"
        
        elif name_type == "numeric_prefixed":
            topic = random.choice(self.nouns).capitalize()
            number = random.randint(1, 100)
            return f"{number:03d}_{topic}"
        
        return "File"  # Fallback
    
    def _generate_name_from_pattern(self, pattern: str) -> str:
        """Generate a name based on a pattern.
        
        Args:
            pattern: Pattern to base the name on
            
        Returns:
            Generated name
        """
        if "%" in pattern:
            # Replace % with random word
            if pattern == "%":
                return self._generate_base_name()
            else:
                parts = pattern.split("%")
                replacements = [random.choice(self.nouns).capitalize() for _ in range(len(parts) - 1)]
                result = parts[0]
                for i, replacement in enumerate(replacements):
                    result += replacement + parts[i + 1]
                return result
        else:
            # Use pattern directly with possible date suffix
            if random.random() < 0.3:  # 30% chance to add date
                date = datetime.now() - timedelta(days=random.randint(0, 365))
                date_str = date.strftime("%Y%m%d")
                return f"{pattern}_{date_str}"
            else:
                return pattern


def main():
    """Main function for testing the storage metadata generator."""
    logging.basicConfig(level=logging.INFO)
    
    # Sample configuration
    config = {
        "distributions": {
            "file_sizes": {"type": "lognormal", "mu": 8.5, "sigma": 2.0},
            "modification_times": {"type": "normal", "mean": "now-30d", "std": "15d"},
            "file_extensions": {
                "type": "weighted", 
                "values": {
                    ".pdf": 0.2, 
                    ".docx": 0.3, 
                    ".txt": 0.5
                }
            }
        }
    }
    
    # Create generator
    generator = StorageMetadataGeneratorImpl(config, seed=42)
    
    # Generate some records
    records = generator.generate(10)
    
    # Generate some truth records
    criteria = {
        "file_extension": ".pdf",
        "time_range": {
            "start": (datetime.now() - timedelta(days=7)).timestamp(),
            "end": datetime.now().timestamp()
        },
        "name_pattern": "Report%"
    }
    truth_records = generator.generate_truth(5, criteria)
    
    # Print records for inspection
    logging.info(f"Generated {len(records)} regular records")
    logging.info(f"Generated {len(truth_records)} truth records")
    
    # Print sample record
    if records:
        logging.info(f"Sample record: {records[0]}")
    
    # Print sample truth record
    if truth_records:
        logging.info(f"Sample truth record: {truth_records[0]}")
    
    # Print truth list
    logging.info(f"Truth list: {generator.truth_list}")


if __name__ == "__main__":
    main()
