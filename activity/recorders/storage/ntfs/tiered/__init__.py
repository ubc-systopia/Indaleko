"""
Tiered Recorder package for NTFS storage activities in Indaleko.

This package implements a multi-tiered storage approach for NTFS activity data,
with different tiers representing different time horizons and compression levels:

- Hot tier: Recent activities with full fidelity (hours to days)
- Warm tier: Medium-term activities with selective compression (weeks to months)
- Cool tier: Long-term activities with aggregation (months to years)
- Glacial tier: Historical activities with statistical summarization (5+ years)

Each tier implements specific storage and compression strategies while
maintaining access to the most relevant aspects of the activity data.
"""

__version__ = "0.1.0"