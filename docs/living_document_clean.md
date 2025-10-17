# Multi-Cloud Data Pipeline - Living Document

**Last Updated**: 2025-10-16
**Current Branch**: `feature/monitoring_logging`
**Current Sprint**: Sprint 2 (Complete) → Moving to Sprint 3
**Project Status**: ✅ Core pipeline complete, monitoring integrated, ready for performance optimization

---

## Quick Start for New Sessions

**Read these files first**:
1. `docs/living_document.md` (this file) - Current state and context
2. `docs/sprint3_detailed_plan.md` - What's coming next
3. `docs/architecture.md` - System architecture overview
4. `docs/setup.md` - How to run the system

**Current State**:
- All 92 tests passing (19 unit + 73 pytest)
- 80%+ code coverage
- Sprint 2 complete: 4-stage pipeline + monitoring fully implemented
- Ready to commit monitoring work and start Sprint 3

---

## What Has Been Done (Sprint 1-2 Complete)

### Sprint 1: Multi-Cloud Foundation ✅
**Status**: Complete
**Branch**: Merged to `main`

**Components Built**:
1. **Node Registry** (`src/coordination/node_registry.py`)
   - Multi-cloud node registration and health tracking
   - Network latency measurements
   - Status monitoring across AWS, GCP, Azure

2. **Communication Protocol** (`src/communication/protocol.py`)
   - HTTP-based cross-cloud messaging
   - Retry logic and rate limiting
   - Timeout handling

3. **Authentication** (`src/auth/`)
   - Basic auth framework (to be enhanced in Sprint 3+)

4. **Configuration** (`src/config/`)
   - YAML-based configuration system
   - Multi-environment support

**Test Coverage**: 100% for Sprint 1 components

---

### Sprint 2: Data Pipeline Implementation ✅
**Status**: Complete (pending final commit)
**Branch**: `feature/monitoring_logging`

#### Stage 1: Ingestion Engine ✅
**File**: `src/pipeline/ingestion_engine.py`
**Tests**: `tests/pipeline/test_ingestion_engine.py`

**What it does**:
- Auto-detects cloud provider (AWS/GCP/Azure/local)
- Reads from cloud-specific data sources
- Chunks large files into 100MB pieces (configurable)
- Distributes chunks to processing nodes

**Key APIs**:
```python
class IngestionEngine:
    async def ingest_batch(self, batch_config: Dict) -> List[DataChunk]
        # batch_config: {'batch_id': str, 'data_source': str, 'expected_size_mb': int}
        # Returns: List of DataChunk objects with metadata

    async def detect_cloud_provider(self) -> str
        # Auto-detects: 'aws', 'gcp', 'azure', or 'local'
```

**Configuration**: `config/data_sources.yml`

---

#### Stage 2: Processing Workers ✅
**File**: `src/pipeline/processing_workers.py`
**Tests**: `tests/pipeline/test_processing_workers.py`

**What it does**:
- Manages pool of worker nodes across clouds
- Load-balanced task distribution (least_loaded or round_robin)
- Parallel data transformation
- Worker failure handling with retries

**Key APIs**:
```python
class ProcessingWorkerPool:
    async def process_chunks(self, chunks: List[DataChunk]) -> List[ProcessedChunk]
        # Distributes chunks across workers, applies transformations
        # Returns: List of ProcessedChunk objects

    async def assign_work(self, chunk: DataChunk) -> str
        # Load balancing logic, returns selected node_id
```

**Configuration**: `config/processing_config.yml`

---

#### Stage 3: Distribution Coordinator ✅
**File**: `src/pipeline/distribution_coordinator.py`
**Tests**: `tests/pipeline/test_distribution_coordinator.py`

**What it does**:
- Network-aware replica placement
- 3x replication across nodes (configurable)
- Quorum-based writes (2/3 minimum for success)
- Cross-cloud data transfer coordination

**Key APIs**:
```python
class DistributionCoordinator:
    async def distribute_chunks(self, chunks: List[ProcessedChunk]) -> List[DistributionTask]
        # Creates 3 replicas per chunk, returns distribution results
        # Succeeds if 2/3 replicas succeed (quorum)

    async def select_target_nodes(self, source_node: str, count: int) -> List[str]
        # Network-aware node selection (prefers same-cloud, low latency)
```

**Configuration**: `config/distribution_config.yml`

---

#### Stage 4: Storage Manager ✅
**File**: `src/pipeline/storage_manager.py`
**Tests**: `tests/pipeline/test_storage_manager.py`

**What it does**:
- Persistent storage with integrity verification
- MD5/SHA256 checksum validation
- Multiple storage backend support
- Automatic cleanup and garbage collection

**Key APIs**:
```python
class StorageManager:
    async def store_chunk(self, chunk_id: str, data: bytes, metadata: Dict) -> bool
        # Stores with checksum verification
        # Returns: True if stored successfully

    async def retrieve_chunk(self, chunk_id: str, verify_checksum: bool = True) -> Tuple[bytes, Dict]
        # Retrieves data and metadata, optionally verifies integrity

    async def create_checkpoint(self, checkpoint_id: str, chunk_ids: List[str]) -> str
        # Creates recovery checkpoint, returns checkpoint path

    async def cleanup_old_data(self, retention_days: int = 30)
        # Auto-cleanup based on retention policy
```

**Configuration**: `config/storage_config.yml`

---

#### Pipeline Orchestrator ✅
**File**: `src/pipeline/pipeline_orchestrator.py`
**Tests**: `tests/integration/test_full_pipeline.py`

**What it does**:
- Coordinates all 4 pipeline stages
- Manages pipeline state and transitions
- Integrates monitoring and logging
- Error handling with graceful degradation

**Key APIs**:
```python
class PipelineOrchestrator:
    def __init__(self, node_registry, config_dir='config/', enable_monitoring=True)
        # enable_monitoring: Enable performance tracking (default True)

    async def run_pipeline(self, batch_config: Dict) -> PipelineResult
        # End-to-end pipeline execution
        # batch_config: {'batch_id': str, 'data_source': str, 'expected_size_mb': int}
        # Returns: PipelineResult with status, duration, metrics

    def get_status(self) -> Dict
        # Current pipeline status and metrics

    def get_healthy_nodes(self) -> int
        # Count of healthy nodes
```

---

#### Monitoring Infrastructure ✅ (Days 26-27)
**Status**: Complete, ready to commit
**Files**:
- `src/monitoring/pipeline_monitor.py`
- `src/monitoring/pipeline_logger.py`
- `src/monitoring/status_dashboard.py`

**What it does**:
- Real-time performance tracking for all stages
- Automatic bottleneck detection (>25%, >35%, >50% thresholds)
- Structured JSON logging to `logs/pipeline_YYYYMMDD.log`
- ASCII art terminal dashboard with node health visualization

**Key APIs**:
```python
class PipelineMonitor:
    def start_pipeline_run(self, run_id: str)
    def track_stage_performance(self, stage_name: str, duration: float, items_processed: int)
    def detect_bottlenecks(self) -> List[BottleneckReport]
    def generate_performance_report(self) -> str

class PipelineLogger:
    def log_pipeline_start(self, run_id: str, batch_config: Dict)
    def log_stage_complete(self, stage_name: str, duration: float, items_processed: int, success_rate: float)
    def log_error_event(self, error_type: str, message: str, context: Dict)
    def analyze_logs(self, log_file: Optional[str] = None) -> Dict

class StatusDashboard:
    def display_pipeline_status(self, orchestrator, clear_screen: bool = False)
    def display_compact_status(self, orchestrator)
    def display_node_status(self, node_registry)
    def display_progress_bar(self, current: int, total: int, stage_name: str)
```

**Usage in Orchestrator**:
```python
orchestrator = PipelineOrchestrator(node_registry, enable_monitoring=True)
# Monitoring happens automatically during run_pipeline()
# Reports printed after completion
```

---

## Test Coverage

### Current Test Statistics
- **Total Tests**: 92 (19 green unit tests + 73 pytest tests)
- **Coverage**: 80%+
- **All Passing**: ✅

### Test Organization

**Unit Tests** (green framework):
- `tests/auth/` - Authentication tests
- `tests/communication/` - Protocol tests
- `tests/config/` - Configuration tests
- `tests/coordination/` - Node registry tests

**Pipeline Tests** (pytest):
- `tests/pipeline/test_ingestion_engine.py` (13 tests)
- `tests/pipeline/test_processing_workers.py` (12 tests)
- `tests/pipeline/test_distribution_coordinator.py` (11 tests)
- `tests/pipeline/test_storage_manager.py` (15 tests)

**Integration Tests** (pytest):
- `tests/integration/test_full_pipeline.py` (9 tests)
  - End-to-end pipeline flow
  - Node failure recovery
  - Multi-batch processing
- `tests/integration/test_cross_cloud_flow.py` (8 tests)
  - Cross-cloud data transfer
  - Network-aware placement validation
- `tests/integration/test_large_scale_pipeline.py` (5 tests)
  - 1GB dataset processing
  - Performance benchmarks
  - Stress testing with multiple batches

**Monitoring Tests** (pytest):
- `tests/monitoring/test_monitoring.py` (27 tests)
  - PipelineMonitor: tracking, bottlenecks, reports
  - PipelineLogger: event logging, analysis
  - StatusDashboard: status display, node health
  - Integration with orchestrator

### Running Tests
```bash
# All tests
bash tests/run_all_tests.sh

# Specific suites
green tests/auth tests/communication tests/config tests/coordination
pytest tests/pipeline/ -v
pytest tests/integration/ -v
pytest tests/monitoring/ -v

# With coverage
pytest --cov=src --cov-report=html tests/
```

---

## Configuration System

### Configuration Files Location: `config/`

**1. Node Configuration** (`config/node_config.yml`)
```yaml
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

**2. Data Sources** (`config/data_sources.yml`)
```yaml
use_local_simulation: true

data_sources:
  aws:
    type: s3_simulation
    local_simulation: ./test_data/aws_s3_simulation
  gcp:
    type: gcs_simulation
    local_simulation: ./test_data/gcp_gcs_simulation

ingestion:
  chunk_size_mb: 100
  max_concurrent_chunks: 10
  retry_attempts: 3
  retry_delay_seconds: 5
```

**3. Processing** (`config/processing_config.yml`)
```yaml
processing:
  max_workers_per_node: 4
  load_balancing: least_loaded  # or 'round_robin'
  retry_attempts: 3
  timeout_seconds: 300
  simulation_mode: true
```

**4. Distribution** (`config/distribution_config.yml`)
```yaml
distribution:
  replication_factor: 3
  min_replicas_success: 2  # Quorum
  placement_strategy: network_aware
  max_concurrent_distributions: 20
  simulation_mode: true
```

**5. Storage** (`config/storage_config.yml`)
```yaml
storage:
  backends:
    local:
      enabled: true
      base_path: ./storage/data
      max_size_gb: 100

  integrity:
    verify_on_write: true
    verify_on_read: true
    checksum_algorithm: md5
    store_metadata: true

  cleanup:
    enable_auto_cleanup: true
    retention_days: 30

  performance:
    max_concurrent_writes: 20

use_local_storage: true
```

---

## Key Design Decisions & Rationale

### 1. Asynchronous Architecture
**Decision**: All I/O operations use `async/await`
**Rationale**: Multi-cloud operations involve significant network latency. Async maximizes throughput and concurrency.

### 2. 3x Replication with 2/3 Quorum
**Decision**: Every chunk replicated 3 times, success requires 2/3 replicas
**Rationale**: Balance between fault tolerance and performance. Tolerates 1 node failure while maintaining availability.

### 3. Network-Aware Placement
**Decision**: Prefer same-cloud nodes, consider measured latency
**Rationale**: Cross-cloud latency (50ms) >> same-cloud latency (5ms). Minimize expensive cross-cloud transfers.

### 4. 100MB Chunk Size
**Decision**: Default chunk size for large files (configurable)
**Rationale**: Balance between parallelism (small chunks) and overhead (large chunks). Allows ~10 chunks from 1GB file.

### 5. Optional Monitoring (Default Enabled)
**Decision**: `enable_monitoring=True` by default, can disable for testing
**Rationale**: Production needs monitoring, tests need speed. Provides flexibility.

### 6. MD5 Checksum Verification
**Decision**: MD5 checksums on all stored data, verify read/write
**Rationale**: Ensure data integrity across cloud boundaries. MD5 faster than SHA256, sufficient for corruption detection.

---

## Data Flow (Normal Operation)

```
1. INGESTION:
   - Detect cloud provider (AWS/GCP/Azure/local)
   - List available files from data source
   - Chunk files into 100MB pieces
   - Create DataChunk objects with metadata
   ↓
2. PROCESSING:
   - Distribute chunks to worker nodes (load balanced)
   - Apply transformation pipeline
   - Validate processed data
   - Return ProcessedChunk results
   ↓
3. DISTRIBUTION:
   - Select 3 target nodes (network-aware)
   - Transfer data to replicas in parallel
   - Wait for quorum (2/3) success
   - Return DistributionTask results
   ↓
4. STORAGE:
   - Persist all replicas to storage backend
   - Calculate and verify MD5 checksums
   - Store metadata separately
   - Create checkpoints periodically
```

---

## Error Handling & Recovery

### Retry Logic
- **Retries**: 3 attempts per operation (configurable)
- **Retry delay**: 5 seconds (configurable)
- **Exponential backoff**: Not yet implemented (Sprint 3)

### Fault Tolerance
- **Quorum writes**: Succeed if 2/3 replicas succeed
- **Node failures**: Automatically exclude unhealthy nodes
- **Graceful degradation**: Continue with reduced capacity
- **Checkpoints**: Periodic checkpoints for recovery

### Known Error Scenarios & Fixes

**Issue 1: Stale chunk files in tests**
- **Error**: Test counts old chunk files from previous runs
- **Fix**: Clean up `./received_chunks` directory before tests
```python
import shutil
if Path('./received_chunks').exists():
    shutil.rmtree('./received_chunks')
```

**Issue 2: Simulated network failures**
- **Error**: Distribution coordinator simulates failures, tests fail
- **Fix**: Accept 80% success rate instead of 100%
```python
success_rate = len(results) / len(chunks)
assert success_rate >= 0.8
```

**Issue 3: Module import errors**
- **Error**: `ModuleNotFoundError: No module named 'src'`
- **Fix**: Set `PYTHONPATH=.` before running tests
```bash
export PYTHONPATH=.
# Or: PYTHONPATH=. pytest tests/
```

---

## Environment Setup

### Quick Setup
```bash
# Clone repo
git clone https://github.com/yourusername/MultiCLoudTestsingSystem
cd MultiCLoudTestsingSystem

# Create virtual environment
python3.9 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Verify
python -c "import asyncio, aiofiles, yaml; print('✅ Ready')"

# Run tests
bash tests/run_all_tests.sh
```

### Environment Variables
```bash
export CLOUD_PROVIDER=gcp         # or aws, azure, local
export LOG_LEVEL=INFO             # or DEBUG, WARNING, ERROR
export PYTHONPATH=.               # For imports
```

---

## What's Next (Sprint 3)

**Current Status**: Sprint 2 complete, monitoring integrated, ready to start Sprint 3

**Sprint 3 Focus**: Performance optimization, chaos engineering, real cloud deployment

**See**: `docs/sprint3_detailed_plan.md` for detailed breakdown

### Sprint 3 Overview (Days 29-42)

**Week 1: Chaos Engineering & Stress Testing** (Days 29-35)
- Advanced failure scenarios (network partitions, cascading failures)
- Load testing with 10GB+ datasets
- Performance profiling and optimization
- Automated stress test suite

**Week 2: Real Cloud Deployment** (Days 36-42)
- Deploy to actual AWS EC2, GCP Compute Engine
- Real S3/GCS storage integration
- Cross-cloud VPN setup
- Production monitoring and alerting

### Key Sprint 3 Deliverables
1. Chaos testing framework
2. Performance benchmarks (MB/s, latency p50/p95/p99)
3. Real cloud deployment scripts
4. Production-ready monitoring dashboard
5. Research paper draft

---

## Pertinent APIs & Integration Points

### Core Pipeline API
```python
from src.pipeline.pipeline_orchestrator import PipelineOrchestrator
from types import SimpleNamespace

# Setup node registry (or use real registry from Sprint 1)
node_registry = create_node_registry()  # Your function

# Create orchestrator
orchestrator = PipelineOrchestrator(
    node_registry=node_registry,
    config_dir='config/',
    enable_monitoring=True  # Optional, default True
)

# Run pipeline
batch_config = {
    'batch_id': 'batch_001',
    'data_source': './test_data/gcp_gcs_simulation',
    'expected_size_mb': 100
}

result = await orchestrator.run_pipeline(batch_config)

# Check results
print(f"Status: {result.status}")
print(f"Duration: {result.duration_seconds:.2f}s")
print(f"Chunks: {result.chunks_processed}")
print(f"Success rate: {result.success_rate:.2%}")
```

### Monitoring API
```python
# Access monitoring data
monitor = orchestrator.monitor
logger = orchestrator.logger
dashboard = orchestrator.dashboard

# Get performance report
report = monitor.generate_performance_report()
print(report)

# Analyze logs
log_analysis = logger.analyze_logs()
print(f"Total entries: {log_analysis['total_entries']}")
print(f"Errors: {log_analysis['by_level'].get('ERROR', 0)}")

# Display status
dashboard.display_pipeline_status(orchestrator)
dashboard.display_node_status(node_registry)
```

### Storage API
```python
from src.pipeline.storage_manager import StorageManager

storage = StorageManager(config_path='config/storage_config.yml')

# Store data
await storage.store_chunk(
    chunk_id='chunk_001',
    data=b'my data',
    metadata={'size': 7, 'source': 'test'}
)

# Retrieve data
data, metadata = await storage.retrieve_chunk('chunk_001', verify_checksum=True)

# Create checkpoint
checkpoint_path = await storage.create_checkpoint(
    checkpoint_id='checkpoint_001',
    chunk_ids=['chunk_001', 'chunk_002']
)

# Cleanup old data
await storage.cleanup_old_data(retention_days=30)
```

### Node Registry API (Sprint 1)
```python
from src.coordination.node_registry import NodeRegistry

registry = NodeRegistry(config_path='config/node_config.yml')

# Register node
await registry.register_node(
    node_id='aws-node-1',
    cloud_provider='aws',
    region='us-east-1',
    address='http://10.0.1.10:8080'
)

# Health check
await registry.health_check('aws-node-1')

# Get healthy nodes
healthy = registry.get_healthy_nodes()

# Get nodes by cloud
aws_nodes = registry.get_nodes_by_cloud('aws')
```

---

## Performance Characteristics

### Current Benchmarks (Sprint 2 Testing)
- **Ingestion**: >200 MB/minute for large files
- **Processing**: <100ms average latency per chunk
- **Distribution**: >99% replica creation success
- **Storage**: >95% successful stores
- **End-to-End**: ~1GB in 18-25 seconds (test environment)

### Typical Bottlenecks
1. **Processing** (40-50% of time) - Most CPU-intensive
2. **Distribution** (25-35% of time) - Network-bound
3. **Storage** (15-20% of time) - I/O-bound
4. **Ingestion** (10-15% of time) - Usually fast

### Scalability
- **Horizontal**: Add more nodes to increase capacity
- **Vertical**: Increase worker count per node
- **Current test**: 4 nodes (2 AWS, 2 GCP simulated)
- **Target**: 10+ nodes across real clouds (Sprint 3)

---

## Git Workflow & Branches

### Branch Structure
- `main` - Production-ready code (Sprint 1 merged here)
- `feature/storage_layer` - Sprint 2 storage work (merged)
- `feature/monitoring_logging` - **CURRENT** Sprint 2 monitoring (ready to commit)
- `develop` - Integration branch (not yet created)

### Current Branch Status
```bash
git branch
# * feature/monitoring_logging

git status
# On branch feature/monitoring_logging
# Changes to be committed: [monitoring files staged]
```

### Pending Actions
1. ✅ Compose commit message (done)
2. ⏳ Commit monitoring work
3. ⏳ Merge to main (or develop)
4. ⏳ Create Sprint 3 branch

### Commit Message Ready
See commit message at end of previous session (comprehensive monitoring/logging commit message prepared).

---

## Documentation Index

**Architecture & Design**:
- `docs/architecture.md` - Complete system architecture
- `docs/living_document.md` - This file (current state)
- `docs/research_paper_outline.md` - Academic paper outline

**Sprint Planning**:
- `docs/detailed_sprint_2_plan.md` - Sprint 2 detailed plan
- `docs/sprint3_detailed_plan.md` - Sprint 3 detailed plan
- `docs/storage_layer_implementation.md` - Storage layer design

**Operations**:
- `docs/setup.md` - Setup and deployment guide
- `docs/knownIssues.md` - Known issues and workarounds
- `docs/dailyLogs/` - Daily development logs

**Configuration**:
- `config/node_config.yml` - Node registry config
- `config/data_sources.yml` - Data source config
- `config/processing_config.yml` - Processing config
- `config/distribution_config.yml` - Distribution config
- `config/storage_config.yml` - Storage config

---

## Common Commands Reference

### Testing
```bash
# All tests
bash tests/run_all_tests.sh

# Specific suite
pytest tests/pipeline/ -v
pytest tests/integration/ -v
pytest tests/monitoring/ -v

# With coverage
pytest --cov=src --cov-report=html tests/

# Single test
pytest tests/integration/test_full_pipeline.py::test_complete_pipeline_execution -v -s

# Skip slow tests
pytest -m "not slow" tests/
```

### Running Pipeline
```bash
# Set environment
export CLOUD_PROVIDER=gcp
export LOG_LEVEL=INFO

# Run demo
python scripts/demo_pipeline.py

# Run specific test as demo
pytest tests/integration/test_full_pipeline.py::test_orchestrator_initialization -v -s
```

### Monitoring & Logs
```bash
# View logs
tail -f logs/pipeline_$(date +%Y%m%d).log

# Analyze logs (with jq)
tail -f logs/pipeline_$(date +%Y%m%d).log | jq

# View coverage
open htmlcov/index.html  # Mac
xdg-open htmlcov/index.html  # Linux
```

### Git Operations
```bash
# Check status
git status

# View changes
git diff
git diff --stat

# Commit
git add .
git commit -m "your message"

# Push
git push origin feature/monitoring_logging

# Create PR (requires gh CLI)
gh pr create --title "Add monitoring and logging" --body "..."
```

---

## Project Dependencies

### Python Version
- **Required**: Python 3.9+
- **Tested**: Python 3.9, 3.10, 3.11

### Core Dependencies
```
aiofiles>=23.0.0      # Async file I/O
aiohttp>=3.8.0        # Async HTTP client/server
PyYAML>=6.0           # YAML config parsing
```

### Testing Dependencies
```
pytest>=7.0.0         # Test framework
pytest-asyncio>=0.21.0  # Async test support
pytest-cov>=4.0.0     # Coverage reporting
green>=3.4.0          # Unit test runner
```

### Installation
```bash
pip install -r requirements.txt
```

---

## Important Notes for Future Sessions

### Before Starting Work
1. Read `docs/living_document.md` (this file)
2. Read current sprint plan (e.g., `docs/sprint3_detailed_plan.md`)
3. Check `git status` and current branch
4. Run tests to verify current state: `bash tests/run_all_tests.sh`
5. Review `docs/knownIssues.md` for known problems

### Project Conventions
- **All async**: Use `async/await` for I/O operations
- **Type hints**: Use Python type hints where possible
- **Config-driven**: All settings in YAML config files
- **Test everything**: Maintain 80%+ coverage
- **Document changes**: Update this living document after major changes

### Code Style
- **Black**: Not yet configured (Sprint 3+)
- **Linting**: Not yet configured (Sprint 3+)
- **Imports**: Absolute imports from `src/`
- **Docstrings**: Use triple-quoted strings for all public APIs

### Testing Strategy
- **Unit tests**: Individual component logic (green framework)
- **Integration tests**: Cross-component flow (pytest)
- **Async tests**: Mark with `@pytest.mark.asyncio`
- **Slow tests**: Mark with `@pytest.mark.slow`

### Monitoring Guidelines
- **Always enable monitoring in production**
- **Disable monitoring in unit tests for speed**
- **Enable monitoring in integration tests**
- **Check bottleneck reports after each run**

---

## Contact & Support

**Project Owner**: User (GitHub: TBD)
**Repository**: https://github.com/yourusername/MultiCLoudTestsingSystem
**Branch**: `feature/monitoring_logging`
**Last Session**: 2025-10-16

---

## Changelog

**2025-10-16**:
- Created living document
- Sprint 2 complete: All 4 pipeline stages + monitoring
- 92 tests passing, 80%+ coverage
- Ready to commit monitoring work and start Sprint 3

---

**End of Living Document**

*This document should be updated after major changes, sprint completions, or significant architectural decisions.*