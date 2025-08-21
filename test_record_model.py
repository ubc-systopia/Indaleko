#!/usr/bin/env python
"""
Test script to verify IndalekoRecordDataModel with the hot tier recorder fix.

This script tests that the IndalekoRecordDataModel can be created with the correct
field names and data types.
"""

import json
import os
import sys

from datetime import UTC, datetime


# Set up environment
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

from data_models.record import IndalekoRecordDataModel
from data_models.source_identifier import IndalekoSourceIdentifierDataModel


# Create source identifier for the record
source_identifier = IndalekoSourceIdentifierDataModel(
    Identifier="f4dea3b8-5d3e-48ad-9b2c-0e72c9a1b867",
    Version="1.0",
    Description="Test Source Identifier",
)

# Import our data management utilities
from utils.misc.data_management import encode_binary_data


# Create record data model with the correct field names
# Using SourceIdentifier (not SourceId) and properly encoded Data
record = IndalekoRecordDataModel(
    SourceIdentifier=source_identifier,
    Timestamp=datetime.now(UTC),
    Data=encode_binary_data(json.dumps({"test": "value"}).encode("utf-8")),
)

