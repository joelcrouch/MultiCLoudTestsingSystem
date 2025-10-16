# Multi-Cloud Data Pipeline Architecture

## Overview

The Multi-Cloud Data Pipeline is a distributed system for processing large-scale ML training data across AWS, GCP, and Azure cloud providers. The system emphasizes fault tolerance, network-aware data placement, and cross-cloud coordination.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Pipeline Orchestrator                            │
│                   (Coordinates all 4 stages)                         │
└─────────────────────────────────────────────────────────────────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │                         │                         │
        ▼                         ▼                         ▼
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│  Monitoring  │         │   Logging    │         │  Dashboard   │
│   (Metrics)  │         │  (JSON logs) │         │   (Status)   │
└──────────────┘         └──────────────┘         └──────────────┘

Data Flow: Ingestion → Processing → Distribution → Storage

┌──────────────────┐
│  Stage 1:        │     • Cloud-aware data ingestion
│  Ingestion       │────▶ • Automatic file chunking (100MB chunks)
│  Engine          │     • Multi-source support (local, S3, GCS)
└──────────────────┘

         │
         ▼

┌──────────────────┐
│  Stage 2:        │     • Parallel processing across nodes
│  Processing      │────▶ • Load-balanced work distribution
│  Workers         │     • Data transformation & validation
└──────────────────┘

         │
         ▼

┌──────────────────┐
│  Stage 3:        │     • Network-aware node selection
│  Distribution    │────▶ • 3x replication for fault tolerance
│  Coordinator     │     • Cross-cloud data transfer
└──────────────────┘

         │
         ▼

┌──────────────────┐
│  Stage 4:        │     • Persistent storage with checksums
│  Storage         │────▶ • Data integrity verification
│  Manager         │     • Automatic cleanup & garbage collection
└──────────────────┘
```

## Component Architecture

### 1. Pipeline Orchestrator
**File**: `src/pipeline/pipeline_orchestrator.py`

**Responsibilities**:
- Coordinates execution of all 4 pipeline stages
- Manages pipeline state and transitions
- Collects metrics across all stages
- Handles errors and provides graceful degradation

**Key Methods**:
- `run_pipeline()` - Execute complete end-to-end pipeline
- `get_status()` - Get current pipeline status
- `get_healthy_nodes()` - Query node health

**Monitoring Integration**:
- PipelineMonitor: Performance tracking & bottleneck detection
- PipelineLogger: Structured JSON logging
- StatusDashboard: Real-time status visualization

### 2. Data Ingestion Engine
**File**: `src/pipeline/ingestion_engine.py`

**Responsibilities**:
- Auto-detect cloud provider (AWS, GCP, Azure, local)
- Read from cloud-specific data sources
- Chunk large files into manageable pieces (default: 100MB)
- Distribute chunks to processing nodes

**Cloud Detection**:
- Environment variable: `CLOUD_PROVIDER`
- AWS: Instance metadata (169.254.169.254)
- GCP: Google metadata server
- Azure: Azure metadata service

**Configuration**: `config/data_sources.yml`

### 3. Processing Worker Pool
**File**: `src/pipeline/processing_workers.py`

**Responsibilities**:
- Manage pool of worker nodes
- Distribute processing tasks with load balancing
- Execute data transformation pipeline
- Handle worker failures and retry logic

**Load Balancing Strategies**:
- `least_loaded` - Assign to node with fewest tasks
- `round_robin` - Distribute evenly in rotation

**Configuration**: `config/processing_config.yml`

### 4. Distribution Coordinator
**File**: `src/pipeline/distribution_coordinator.py`

**Responsibilities**:
- Intelligent data placement across nodes
- Network-aware replica selection
- 3x replication (configurable)
- Quorum-based success (2/3 minimum)

**Placement Strategies**:
- **Network-aware**: Prefer same-cloud nodes, minimize latency
- Consider node availability and capacity
- Balance across cloud providers

**Configuration**: `config/distribution_config.yml`

### 5. Storage Manager
**File**: `src/pipeline/storage_manager.py`

**Responsibilities**:
- Persist distributed data chunks
- Data integrity verification (MD5/SHA256)
- Support multiple storage backends
- Automatic cleanup and retention policies

**Storage Backends**:
- **Local**: Filesystem storage (Sprint 2)
- **Cloud**: S3, GCS (Sprint 3+)

**Features**:
- Checksum verification on read/write
- Metadata storage
- Checkpoint creation
- Automatic garbage collection

**Configuration**: `config/storage_config.yml`

## Multi-Cloud Coordination

### Node Registry
**From Sprint 1**: `src/coordination/node_registry.py`

Maintains registry of all nodes across clouds:
- Node registration and health checks
- Cloud provider tracking
- Network latency measurements
- Status monitoring

### Communication Protocol
**From Sprint 1**: `src/communication/protocol.py`

Cross-cloud communication:
- HTTP-based message passing
- Retry logic for failed transfers
- Rate limiting
- Timeout handling

## Data Flow

### Normal Operation Flow

```
1. Ingestion:
   - Detect cloud provider
   - List available files from data source
   - Chunk files (100MB each)
   - Create DataChunk objects with metadata

2. Processing:
   - Distribute chunks to worker nodes
   - Apply transformation pipeline
   - Validate processed data
   - Return ProcessedChunk results

3. Distribution:
   - Select 3 target nodes (network-aware)
   - Transfer data to replicas
   - Wait for quorum (2/3) success
   - Return DistributionTask results

4. Storage:
   - Persist all replicas to storage backend
   - Calculate and verify checksums
   - Store metadata separately
   - Create checkpoints periodically
```

### Error Handling Flow

```
Component Failure → Retry Logic → Alternative Node → Success/Failure

- Retries: 3 attempts per operation (configurable)
- Retry delay: 5 seconds (configurable)
- Quorum writes: Succeed if 2/3 replicas succeed
- Graceful degradation: Continue with reduced capacity
```

## Monitoring Architecture

### PipelineMonitor
**File**: `src/monitoring/pipeline_monitor.py`

Tracks performance metrics:
- Stage duration and throughput
- Bottleneck detection (>25%, >35%, >50% thresholds)
- Success rates
- Historical trends

**Bottleneck Severity Levels**:
- **Severe**: >50% of total time
- **Moderate**: 35-50% of total time
- **Minor**: 25-35% of total time

### PipelineLogger
**File**: `src/monitoring/pipeline_logger.py`

Structured JSON logging:
- Pipeline lifecycle events
- Stage start/complete events
- Error events with context
- Performance metrics

**Log Storage**: `logs/pipeline_YYYYMMDD.log`

### StatusDashboard
**File**: `src/monitoring/status_dashboard.py`

Real-time visualization:
- Pipeline status and current stage
- Node health (healthy/unhealthy counts)
- Stage metrics (items, duration, throughput)
- Visual health bars

## Key Design Decisions

### 1. **Asynchronous Architecture**
- All I/O operations use `async/await`
- Enables high concurrency
- Non-blocking network operations

**Rationale**: Multi-cloud operations involve significant network latency. Async architecture maximizes throughput.

### 2. **3x Replication with 2/3 Quorum**
- Every chunk replicated 3 times
- Success requires 2/3 replicas

**Rationale**: Balance between fault tolerance and performance. Can tolerate 1 node failure while maintaining data availability.

### 3. **Network-Aware Placement**
- Prefer same-cloud nodes
- Consider measured latency
- Balance across providers

**Rationale**: Cross-cloud network latency (50ms) >> same-cloud latency (5ms). Minimize expensive cross-cloud transfers.

### 4. **100MB Chunk Size**
- Default chunk size for large files
- Configurable per deployment

**Rationale**: Balance between parallelism (small chunks) and overhead (large chunks). 100MB allows ~10 chunks from 1GB file.

### 5. **Checksum Verification**
- MD5 checksums on all stored data
- Verification on read and write

**Rationale**: Ensure data integrity across cloud boundaries and storage systems.

### 6. **Monitoring Optional but Default Enabled**
- `enable_monitoring=True` by default
- Can disable for testing

**Rationale**: Production needs monitoring, tests need speed. Optional monitoring provides flexibility.

## Configuration Files

### Node Configuration
```yaml
# config/node_config.yml
nodes:
  aws-node-1:
    cloud_provider: aws
    region: us-east-1
    address: http://10.0.1.10:8080

  gcp-node-1:
    cloud_provider: gcp
    region: us-central1
    address: http://10.0.2.10:8080
```

### Data Sources
```yaml
# config/data_sources.yml
data_sources:
  aws:
    type: s3_simulation
    local_simulation: ./test_data/aws_s3_simulation

  gcp:
    type: gcs_simulation
    local_simulation: ./test_data/gcp_gcs_simulation
```

### Processing
```yaml
# config/processing_config.yml
processing:
  max_workers_per_node: 4
  load_balancing: least_loaded
  retry_attempts: 3
```

### Distribution
```yaml
# config/distribution_config.yml
distribution:
  replication_factor: 3
  min_replicas_success: 2
  placement_strategy: network_aware
```

### Storage
```yaml
# config/storage_config.yml
storage:
  backends:
    local:
      base_path: ./storage/data

  integrity:
    verify_on_write: true
    checksum_algorithm: md5

  cleanup:
    retention_days: 30
    enable_auto_cleanup: true
```

## Performance Characteristics

### Throughput Targets
- **Ingestion**: >200 MB/minute for large files
- **Processing**: <100ms average latency per chunk
- **Distribution**: >99% replica creation success
- **Storage**: >95% successful stores

### Scalability
- Horizontal: Add more nodes to increase capacity
- Vertical: Increase worker count per node
- Current test: 4 nodes (2 AWS, 2 GCP)

### Bottlenecks (Typical)
1. **Processing** (40-50% of time) - Most CPU-intensive
2. **Distribution** (25-35% of time) - Network-bound
3. **Storage** (15-20% of time) - I/O-bound
4. **Ingestion** (10-15% of time) - Usually fast

## Testing Architecture

### Test Coverage: 80%+

**Unit Tests** (41 tests):
- Individual component logic
- Data transformations
- Error handling

**Integration Tests** (51 tests):
- End-to-end pipeline flow
- Cross-cloud data transfer
- Node failure recovery
- Large-scale testing (1GB datasets)

**Monitoring Tests** (27 tests):
- Performance tracking
- Bottleneck detection
- Logging functionality
- Dashboard display

### Test Data
- Small: ~100KB files for quick tests
- Medium: ~1MB files for integration tests
- Large: 1GB+ synthetic datasets for performance tests

## Security Considerations

### Current Implementation (Sprint 2)
- Local filesystem storage
- Simulated cloud environments
- No authentication/authorization

### Future Enhancements (Sprint 3+)
- Cloud IAM integration (AWS IAM, GCP SA)
- Encrypted data transfer (TLS)
- Data encryption at rest
- Access control and auditing

## Deployment Architecture

### Development/Testing
```
Single machine:
- Multiple simulated nodes
- Local filesystem storage
- Environment variables for cloud simulation
```

### Production (Future)
```
Multi-cloud deployment:
- Real AWS EC2, GCP Compute, Azure VMs
- Cloud-native storage (S3, GCS, Blob)
- VPN or direct connect between clouds
- Distributed coordination service
```

## Future Enhancements

### Sprint 3: Performance & Stress Testing
- Comprehensive chaos engineering
- Performance optimization
- Advanced caching strategies
- Real cloud deployment

### Beyond Sprint 3
- Machine learning integration
- Auto-scaling based on load
- Advanced placement algorithms
- Cost optimization
- Real-time streaming data support

## References

- Sprint 1: Multi-cloud foundation and coordination
- Sprint 2: Data pipeline implementation
- Detailed Sprint 2 Plan: `docs/detailed_sprint_2_plan.md`
- Research Paper Outline: `docs/research_paper_outline.md`
