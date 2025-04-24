"""
Helper to build standardized Indaleko log filenames.
"""
from datetime import datetime

def build_indaleko_log_name(
    platform: str,
    service: str,
    machine_uuid: str,
    timestamp: datetime
) -> str:
    """
    Build a filename of the form:
      indaleko-plt=<platform>-svc=<service>-machine=<machine_uuid>-ts=<timestamp>.log

    Timestamp uses format YYYY_MM_DDTHH#MM#SS.microZ
    """
    ts = timestamp.strftime("%Y_%m_%dT%H#%M#%S.%fZ")
    return f"indaleko-plt={platform}-svc={service}-machine={machine_uuid}-ts={ts}.log"