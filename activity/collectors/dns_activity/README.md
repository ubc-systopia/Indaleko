# DNS Activity Monitor for Indaleko

This module implements a DNS activity monitor for the Indaleko system, providing comprehensive visibility into network activity through DNS query monitoring.

## Overview

The DNS Activity Monitor captures Domain Name System (DNS) queries and responses across the network, offering insights into:

- Web browsing activity
- Application network connections
- IoT device communications
- Background services
- API calls and cloud service usage
- Content delivery networks (CDNs)
- Mobile device activity

Unlike traditional web history monitoring, DNS monitoring provides a comprehensive view of all network activity, not just web browsing.

## Architecture

The DNS Activity Monitor follows Indaleko's collector/recorder pattern:

1. **DnsActivityCollector**: Gathers DNS query data using various methods
2. **DnsActivityRecorder**: Stores and indexes the data in the Indaleko database

### Collection Methods

The collector supports multiple implementation strategies:

1. **Local DNS Proxy**
   - Run a local DNS proxy that handles all resolution requests
   - Forward queries to upstream DNS servers
   - Process all queries and responses

2. **Pi-hole Integration**
   - Leverage existing Pi-hole DNS ad-blocker infrastructure
   - Read from Pi-hole's query database or API
   - Add Indaleko-specific processing and analysis

3. **Packet Capture**
   - Use packet capture libraries to monitor DNS traffic
   - Process packets on port 53 (UDP/TCP)
   - Reassemble DNS queries and responses

4. **Windows ETW (Event Tracing for Windows)**
   - Use Windows ETW to monitor DNS client activity
   - Provides process attribution for DNS queries
   - Captures Windows DNS client events

### Data Model

#### Core Models

```python
# Core DNS activity event
class DnsActivityData(IndalekoBaseModel):
    activity_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    query_domain: str = Field(..., description="Queried domain name")
    query_type: Union[str, int] = Field(..., description="DNS record type")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Process attribution (if available)
    process_id: Optional[int] = Field(None)
    process_name: Optional[str] = Field(None)

    # Source information
    source_ip: Optional[str] = Field(None)
    source_port: Optional[int] = Field(None)

    # Response information
    response_ips: List[str] = Field(default_factory=list)
    response_ttl: Optional[int] = Field(None)
    response_error: Optional[str] = Field(None)

    # Contextual enrichment
    device_name: Optional[str] = Field(None)
    device_type: Optional[str] = Field(None)
    domain_category: Optional[str] = Field(None)
    application: Optional[str] = Field(None)

# Bulk container for activities
class DnsBulkActivityData(IndalekoBaseModel):
    activity_data_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    start_time: datetime
    end_time: datetime
    events: List[DnsActivityData]
    total_queries: int
    unique_domains: int
    Timestamp: IndalekoTimestamp = Field(default_factory=IndalekoTimestamp)
```

#### Domain Statistics

```python
class DomainStatisticsData(IndalekoBaseModel):
    domain: str = Field(..., description="Domain name")
    first_seen: datetime
    last_seen: datetime
    query_count: int
    unique_sources: int
    resolved_ips: List[str] = Field(default_factory=list)
    processes: List[str] = Field(default_factory=list)
    applications: List[str] = Field(default_factory=list)
    category: Optional[str] = Field(None)
    risk_score: Optional[float] = Field(None)
```

#### Device Profiles

```python
class DeviceProfileData(IndalekoBaseModel):
    device_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    ip_address: str
    hostname: Optional[str] = Field(None)
    mac_address: Optional[str] = Field(None)
    first_seen: datetime
    last_seen: datetime
    device_type: Optional[str] = Field(None)
    manufacturer: Optional[str] = Field(None)
    operating_system: Optional[str] = Field(None)
    top_domains: List[Tuple[str, int]] = Field(default_factory=list)
    domain_categories: Dict[str, int] = Field(default_factory=dict)
    active_hours: List[int] = Field(default_factory=list)
```

## Collection Process

### 1. DNS Proxy Method

```
┌─────────────┐     ┌─────────────┐     ┌──────────────┐
│  Client     │     │  Indaleko   │     │  Upstream    │
│  Devices    │────>│  DNS Proxy  │────>│  DNS Servers │
└─────────────┘     └─────────────┘     └──────────────┘
                         │
                         ▼
                    ┌─────────────┐
                    │ Event Queue │
                    └─────────────┘
                         │
                         ▼
                    ┌─────────────┐     ┌─────────────┐
                    │ Processing  │────>│  Indaleko   │
                    │   Thread    │     │  Database   │
                    └─────────────┘     └─────────────┘
```

The proxy intercepts all DNS requests, forwards them to upstream servers, and logs all activity before returning responses to clients.

### 2. Pi-hole Integration Method

```
┌─────────────┐     ┌─────────────┐     ┌──────────────┐
│  Client     │     │  Pi-hole    │     │  Upstream    │
│  Devices    │────>│  DNS Server │────>│  DNS Servers │
└─────────────┘     └─────────────┘     └──────────────┘
                         │
                         │
                    ┌─────────────┐
                    │  Pi-hole    │
                    │  Database   │
                    └─────────────┘
                         │
                         ▼
                    ┌─────────────┐     ┌─────────────┐
                    │  Indaleko   │────>│  Indaleko   │
                    │  Collector  │     │  Database   │
                    └─────────────┘     └─────────────┘
```

The collector reads from Pi-hole's query database or API to gather DNS activity data.

## Data Enrichment

### 1. Domain Classification

Domains are classified into categories:

- Productivity (office365.com, google.docs.com)
- Development (github.com, npmjs.org)
- Social Media (facebook.com, instagram.com)
- Entertainment (netflix.com, spotify.com)
- Advertisement (doubleclick.net, adnxs.com)
- Analytics (google-analytics.com, hotjar.com)
- IoT/Smart Home (nest.com, ring.com)
- Content Delivery (cloudfront.net, akamai.com)

### 2. Device Identification

Devices making DNS queries are identified through:

- IP to hostname mapping
- MAC address OUI lookup for manufacturer
- Query pattern analysis for device type inference
- mDNS/Bonjour discovery for device names

### 3. Application Attribution

Where possible, DNS queries are attributed to specific applications:

- Process information (Windows ETW method)
- Known domain patterns (e.g., api.spotify.com → Spotify app)
- Temporal correlation with other activities

## Privacy Considerations

This module includes robust privacy protections:

1. **Local Processing**: All data collected and processed locally
2. **Domain Filtering**: Option to exclude sensitive domains:
   - Financial services
   - Healthcare providers
   - Adult content
   - Webmail services

3. **Data Retention**: Configurable retention periods
4. **Aggregation**: Option to store only aggregated statistics, not individual queries
5. **Device/User Opt-Out**: Ability to exclude specific devices or users
6. **Consent Controls**: Clear user consent mechanisms

## Semantic Attributes

DNS activity includes these semantic attributes:

```python
class DnsActivityAttributes(str, Enum):
    """Semantic attributes for DNS activity."""
    DNS_ACTIVITY = "6c7d8e9f-0a1b-2c3d-4e5f-6a7b8c9d0e1f"

    # Domain categories
    CATEGORY_DEVELOPMENT = "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d"
    CATEGORY_PRODUCTIVITY = "b2c3d4e5-f6a7-8b9c-0d1e-2f3a4b5c6d7"
    CATEGORY_SOCIAL = "c3d4e5f6-a7b8-9c0d-1e2f-3a4b5c6d7e8"
    CATEGORY_ENTERTAINMENT = "d4e5f6a7-b8c9-0d1e-2f3a-4b5c6d7e8f9"
    CATEGORY_CLOUD = "e5f6a7b8-c9d0-1e2f-3a4b-5c6d7e8f9a0"

    # Application categories
    APP_BROWSER = "f6a7b8c9-d0e1-2f3a-4b5c-6d7e8f9a0b1"
    APP_DEVELOPMENT = "a7b8c9d0-e1f2-3a4b-5c6d-7e8f9a0b1c2"
    APP_SYSTEM = "b8c9d0e1-f2a3-4b5c-6d7e-8f9a0b1c2d3"
    APP_COLLABORATION = "c9d0e1f2-a3b4-5c6d-7e8f-9a0b1c2d3e4"

    # Special attributes
    HIGH_FREQUENCY = "d0e1f2a3-b4c5-6d7e-8f9a-0b1c2d3e4f5"
    UNUSUAL_PATTERN = "e1f2a3b4-c5d6-7e8f-9a0b-1c2d3e4f5a6"
    NEW_DOMAIN = "f2a3b4c5-d6e7-8f9a-0b1c-2d3e4f5a6b7"
```

## Usage Examples

### Basic Setup with DNS Proxy

```python
from activity.collectors.dns_activity.dns_collector import DnsActivityCollector
from activity.recorders.dns_activity.dns_recorder import DnsActivityRecorder

# Create a DNS proxy collector
collector = DnsActivityCollector(
    collection_method="proxy",
    upstream_dns="8.8.8.8",  # Google DNS
    cache_enabled=True,
    port=53,
    privacy_filters={
        "exclude_domains": ["*bank*", "*health*", "*mail*"],
        "exclude_categories": ["financial", "healthcare"]
    },
    auto_start=True
)

# Create a recorder
recorder = DnsActivityRecorder(
    collector=collector,
    collection_name="DnsActivity",
    domain_enrichment=True,
    update_interval=300  # Update every 5 minutes
)

# Start collection and recording
collector.start_collection()
recorder.start_recording()
```

### Pi-hole Integration

```python
from activity.collectors.dns_activity.pihole_collector import PiholeBasedDnsCollector
from activity.recorders.dns_activity.dns_recorder import DnsActivityRecorder

# Create a Pi-hole based collector
collector = PiholeBasedDnsCollector(
    pihole_host="pi.hole",
    pihole_api_token="your_api_token",  # Optional
    use_sqlite=True,  # Read directly from Pi-hole database
    enrichment_enabled=True,
    auto_start=True
)

# Create a recorder
recorder = DnsActivityRecorder(
    collector=collector,
    collection_name="PiholeDnsActivity",
    domain_enrichment=True
)

# Start collection
collector.start_collection()
```

### Querying DNS Activity

```python
# Get all queries to a specific domain
github_queries = recorder.get_queries_by_domain(
    domain="github.com",
    include_subdomains=True
)

# Get all queries from a specific device
device_queries = recorder.get_queries_by_source(
    source_ip="192.168.1.100"
)

# Get queries in a time range
recent_queries = recorder.get_queries_by_time_range(
    start_time=datetime.now() - timedelta(hours=1),
    end_time=datetime.now()
)

# Get domain statistics
domain_stats = recorder.get_domain_statistics(
    min_query_count=5,
    sort_by="query_count",
    limit=100
)

# Get top domains by category
social_domains = recorder.get_top_domains_by_category(
    category="social",
    limit=10
)
```

## Integration with Other Indaleko Components

### NTFS Activity

Link downloaded files to their source domains:

```python
def find_file_source_domains(file_path):
    """Find domains that might be the source of a downloaded file."""
    # Get file creation time
    file_creation = ntfs_recorder.get_file_creation(file_path)

    if not file_creation:
        return []

    # Look for DNS queries in a window before file creation
    window_start = file_creation.timestamp - timedelta(minutes=5)
    window_end = file_creation.timestamp

    # Get DNS queries in this window
    queries = dns_recorder.get_queries_by_time_range(
        start_time=window_start,
        end_time=window_end
    )

    # Look for download domains
    download_domains = []
    for query in queries:
        domain = query.query_domain
        # Check if this looks like a file hosting domain
        if any(pattern in domain for pattern in ["download", "cdn", "content", "storage"]):
            download_domains.append({
                "domain": domain,
                "timestamp": query.timestamp,
                "time_before_file": (file_creation.timestamp - query.timestamp).total_seconds()
            })

    return sorted(download_domains, key=lambda x: x["time_before_file"])
```

### Task Activity

Associate DNS activity with tasks:

```python
def associate_domains_with_task(task_id):
    """Find domains accessed while working on a task."""
    # Get task timing
    task = task_recorder.get_task_by_id(task_id)
    if not task:
        return []

    # Get DNS queries during task active periods
    task_domains = []
    for session in task.active_sessions:
        session_start = session.start_time
        session_end = session.end_time

        # Get DNS queries in this session
        queries = dns_recorder.get_queries_by_time_range(
            start_time=session_start,
            end_time=session_end
        )

        # Group by domain
        domains = {}
        for query in queries:
            domain = query.query_domain
            if domain not in domains:
                domains[domain] = {
                    "domain": domain,
                    "query_count": 0,
                    "first_seen": None,
                    "last_seen": None
                }

            domains[domain]["query_count"] += 1

            if not domains[domain]["first_seen"] or query.timestamp < domains[domain]["first_seen"]:
                domains[domain]["first_seen"] = query.timestamp

            if not domains[domain]["last_seen"] or query.timestamp > domains[domain]["last_seen"]:
                domains[domain]["last_seen"] = query.timestamp

        task_domains.extend(domains.values())

    # Return sorted by query count
    return sorted(task_domains, key=lambda x: x["query_count"], reverse=True)
```

### Activity Timeline

Generate comprehensive activity timelines:

```python
def generate_network_activity_timeline(user_id, start_time, end_time):
    """Generate network activity timeline for a user."""
    timeline_items = []

    # Get user's devices
    devices = device_recorder.get_devices_by_user(user_id)
    device_ips = [device.ip_address for device in devices]

    # Get DNS activity for these devices
    dns_events = dns_recorder.get_queries_by_sources(
        sources=device_ips,
        start_time=start_time,
        end_time=end_time
    )

    # Add to timeline
    for event in dns_events:
        timeline_items.append({
            "type": "dns_query",
            "timestamp": event.timestamp,
            "domain": event.query_domain,
            "domain_category": event.domain_category,
            "source": event.source_ip,
            "application": event.application if hasattr(event, "application") else None
        })

    # Get file activities
    file_events = ntfs_recorder.get_activities_by_time_range(
        start_time=start_time,
        end_time=end_time
    )

    # Add to timeline
    for event in file_events:
        timeline_items.append({
            "type": "file_activity",
            "subtype": event.activity_type,
            "timestamp": event.timestamp,
            "file_path": event.file_path,
            "process": event.process_name
        })

    # Sort by timestamp
    timeline_items.sort(key=lambda x: x["timestamp"])

    return timeline_items
```

## Security Insights

The DNS activity monitor provides valuable security insights:

1. **Malicious Domain Detection**:
   - Check queries against threat intelligence feeds
   - Detect communication with known malicious domains

2. **DNS Tunneling Detection**:
   - Identify abnormally long domain names
   - Detect high-entropy domains that may indicate data exfiltration

3. **Unusual Query Patterns**:
   - Detect sudden changes in query volume
   - Identify devices querying unusual domains

4. **Shadow IT Discovery**:
   - Discover unauthorized cloud services
   - Identify personal email or file sharing services

## Future Work

Planned enhancements include:

1. **Encrypted DNS Monitoring** (DoH/DoT):
   - Support for DNS over HTTPS
   - Support for DNS over TLS

2. **Advanced Correlation**:
   - Better process-to-query attribution
   - Enhanced file download correlation

3. **Network Topology Mapping**:
   - Build network graph based on DNS activity
   - Visualize device communication patterns

4. **Machine Learning Integration**:
   - Anomaly detection for unusual DNS patterns
   - Domain categorization improvements

5. **Cross-Device Activity Correlation**:
   - Link activities across devices for the same user
   - Build user-centric rather than device-centric views

## Requirements

- Python 3.8+
- Additional packages:
  - `dnslib`: For DNS packet processing
  - `scapy`: For packet capture methods
  - `dnspython`: For general DNS operations
  - `pywin32`: For Windows ETW implementation (Windows only)

## Platform Support

- **Windows**: Full support with process attribution via ETW
- **Linux**: DNS proxy and packet capture methods
- **macOS**: DNS proxy and packet capture methods
- **Raspberry Pi**: Pi-hole integration
