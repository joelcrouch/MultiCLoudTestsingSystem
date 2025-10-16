# Multi-Cloud Data Pipeline - Setup Guide

## Quick Start

Get the pipeline running in under 5 minutes!

### Prerequisites

- **Python 3.9+**
- **2GB+ free disk space**
- **Git**

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/MultiCLoudTestsingSystem
cd MultiCLoudTestsingSystem

# Install dependencies
pip install -r requirements.txt

# Verify installation
python -c "import asyncio, aiofiles, yaml; print('✅ All dependencies installed')"
```

### Run Your First Pipeline

```bash
# Set environment
export CLOUD_PROVIDER=gcp

# Run a simple pipeline test
python -m pytest tests/integration/test_full_pipeline.py::test_orchestrator_initialization -v
```

---

## Detailed Setup

### 1. Python Environment Setup

#### Using venv (Recommended)

```bash
# Create virtual environment
python3.9 -m venv venv

# Activate (Linux/Mac)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

#### Using conda

```bash
# Create conda environment
conda create -n multicloud python=3.9

# Activate
conda activate multicloud

# Install dependencies
pip install -r requirements.txt
```

### 2. Dependencies

**Required packages** (from `requirements.txt`):

```
aiofiles>=23.0.0
aiohttp>=3.8.0
PyYAML>=6.0
pytest>=7.0.0
pytest-asyncio>=0.21.0
pytest-cov>=4.0.0
green>=3.4.0
```

**Install specific versions**:
```bash
pip install aiofiles==23.2.1 aiohttp==3.9.1 PyYAML==6.0.1
```

### 3. Directory Structure

The system expects the following structure:

```
MultiCLoudTestsingSystem/
├── src/
│   ├── pipeline/
│   │   ├── ingestion_engine.py
│   │   ├── processing_workers.py
│   │   ├── distribution_coordinator.py
│   │   ├── storage_manager.py
│   │   └── pipeline_orchestrator.py
│   ├── monitoring/
│   │   ├── pipeline_monitor.py
│   │   ├── pipeline_logger.py
│   │   └── status_dashboard.py
│   ├── coordination/         # From Sprint 1
│   ├── communication/        # From Sprint 1
│   ├── auth/                 # From Sprint 1
│   └── config/               # From Sprint 1
├── config/
│   ├── node_config.yml
│   ├── data_sources.yml
│   ├── processing_config.yml
│   ├── distribution_config.yml
│   └── storage_config.yml
├── tests/
│   ├── pipeline/
│   ├── integration/
│   └── monitoring/
├── test_data/               # Auto-created during tests
├── storage/                 # Auto-created during operation
└── logs/                    # Auto-created for logging
```

### 4. Configuration

#### Basic Configuration

Create/verify configuration files in `config/` directory:

**Data Sources** (`config/data_sources.yml`):
```yaml
use_local_simulation: true

data_sources:
  aws:
    type: s3_simulation
    local_simulation: ./test_data/aws_s3_simulation

  gcp:
    type: gcs_simulation
    local_simulation: ./test_data/gcp_gcs_simulation

  azure:
    type: blob_simulation
    local_simulation: ./test_data/azure_blob_simulation

ingestion:
  chunk_size_mb: 100
  max_concurrent_chunks: 10
  retry_attempts: 3
  retry_delay_seconds: 5
```

**Storage** (`config/storage_config.yml`):
```yaml
storage:
  backends:
    local:
      enabled: true
      base_path: "./storage/data"
      max_size_gb: 100

  integrity:
    verify_on_write: true
    verify_on_read: true
    checksum_algorithm: "md5"
    store_metadata: true

  cleanup:
    enable_auto_cleanup: true
    retention_days: 30

  performance:
    max_concurrent_writes: 20

use_local_storage: true
```

#### Advanced Configuration

See individual config files for advanced options:
- **Processing**: Worker pool size, load balancing
- **Distribution**: Replication factor, placement strategy
- **Node Registry**: Node addresses, health check intervals

### 5. Test Data Setup

#### Auto-Generated Test Data

Tests automatically create test data in `test_data/`. For manual testing:

```python
from pathlib import Path

# Create test data directories
for cloud in ['aws_s3_simulation', 'gcp_gcs_simulation']:
    test_dir = Path(f'./test_data/{cloud}')
    test_dir.mkdir(parents=True, exist_ok=True)

    # Create sample file
    test_file = test_dir / 'sample_data.dat'
    test_file.write_bytes(b'test data' * 100000)  # ~900KB
```

#### Large-Scale Test Data

For 1GB+ tests:

```bash
# Create 1GB test file
python scripts/generate_test_data.py --size 1024 --output test_data/large_dataset/
```

---

## Running the System

### Option 1: Run Tests (Recommended for First Time)

```bash
# Run all tests
bash tests/run_all_tests.sh

# Run specific test suites
pytest tests/pipeline/ -v
pytest tests/integration/ -v
pytest tests/monitoring/ -v

# Run with coverage
pytest --cov=src --cov-report=html tests/
```

### Option 2: Run Pipeline Directly

```python
import asyncio
from types import SimpleNamespace
from src.pipeline.pipeline_orchestrator import PipelineOrchestrator

# Setup mock node registry (or use real Sprint 1 registry)
mock_registry = SimpleNamespace()
mock_registry.nodes = {
    'aws-node-1': SimpleNamespace(
        node_id='aws-node-1',
        cloud_provider='aws',
        status='healthy',
        network_latency={'gcp': 50, 'aws': 5}
    ),
    'gcp-node-1': SimpleNamespace(
        node_id='gcp-node-1',
        cloud_provider='gcp',
        status='healthy',
        network_latency={'aws': 50, 'gcp': 5}
    )
}

# Create orchestrator
orchestrator = PipelineOrchestrator(mock_registry, enable_monitoring=True)

# Configure batch
batch_config = {
    'batch_id': 'demo_batch_001',
    'data_source': './test_data/gcp_gcs_simulation',
    'expected_size_mb': 10
}

# Run pipeline
async def main():
    result = await orchestrator.run_pipeline(batch_config)
    print(f"Result: {result.status}")
    print(f"Duration: {result.duration_seconds:.2f}s")
    print(f"Chunks processed: {result.chunks_processed}")

asyncio.run(main())
```

### Option 3: Use Demo Script

```bash
# Run the demo
python scripts/demo_pipeline.py
```

---

## Environment Variables

### Required
- `CLOUD_PROVIDER`: Set to `aws`, `gcp`, `azure`, or `local`

### Optional
- `PYTHONPATH`: Set to `.` for imports (auto-set by test runner)
- `LOG_LEVEL`: `DEBUG`, `INFO`, `WARNING`, `ERROR` (default: `INFO`)

### Example
```bash
export CLOUD_PROVIDER=gcp
export LOG_LEVEL=DEBUG
python -m pytest tests/integration/test_full_pipeline.py -v
```

---

## Monitoring & Logs

### Viewing Logs

```bash
# View latest pipeline log
tail -f logs/pipeline_$(date +%Y%m%d).log

# View with JSON formatting (requires jq)
tail -f logs/pipeline_$(date +%Y%m%d).log | jq

# Analyze logs
python -c "from src.monitoring.pipeline_logger import PipelineLogger; \
           logger = PipelineLogger(); \
           print(logger.analyze_logs())"
```

### Viewing Dashboard

The dashboard displays automatically during pipeline execution. To view manually:

```python
from src.monitoring.status_dashboard import StatusDashboard
from src.pipeline.pipeline_orchestrator import PipelineOrchestrator

dashboard = StatusDashboard()
orchestrator = PipelineOrchestrator(node_registry)

# Display status
dashboard.display_pipeline_status(orchestrator)

# Display compact status
dashboard.display_compact_status(orchestrator)

# Display node health
dashboard.display_node_status(node_registry)
```

### Performance Reports

After each pipeline run, a performance report is automatically generated:

```
================================================================================
📊 PIPELINE PERFORMANCE REPORT
================================================================================
Run ID: test_batch_001
Status: success
Total Duration: 18.50s

📈 STAGE-BY-STAGE BREAKDOWN:
--------------------------------------------------------------------------------

INGESTION:
  Duration: 2.50s (13.5% of total)
  Items Processed: 100
  Throughput: 40.00 items/sec

PROCESSING:
  Duration: 8.20s (44.3% of total)
  Items Processed: 100
  Throughput: 12.20 items/sec

🔍 BOTTLENECK ANALYSIS:
--------------------------------------------------------------------------------

🟡 PROCESSING
  Duration: 8.20s
  Percentage: 44.3%
  Severity: moderate
  Recommendation: WARNING: processing is using 44% of pipeline time. Consider optimization.
```

---

## Troubleshooting

### Common Issues

#### 1. Import Errors

**Problem**: `ModuleNotFoundError: No module named 'src'`

**Solution**:
```bash
export PYTHONPATH=.
# Or run with: PYTHONPATH=. python your_script.py
```

#### 2. Test Data Not Found

**Problem**: `Found 0 files in data source`

**Solution**:
```bash
# Ensure test data directories exist
mkdir -p test_data/gcp_gcs_simulation
echo "test data" > test_data/gcp_gcs_simulation/sample.dat
```

#### 3. Permission Errors

**Problem**: `PermissionError: [Errno 13] Permission denied: 'storage/data'`

**Solution**:
```bash
# Ensure storage directories are writable
chmod -R 755 storage/ logs/
```

#### 4. Async Warnings

**Problem**: `RuntimeWarning: coroutine was never awaited`

**Solution**: Ensure you're using `asyncio.run()` or `await` for async functions:
```python
# Wrong
result = orchestrator.run_pipeline(config)

# Correct
result = await orchestrator.run_pipeline(config)
# Or
result = asyncio.run(orchestrator.run_pipeline(config))
```

#### 5. Test Failures

**Problem**: Tests fail with "stale chunk files"

**Solution**:
```bash
# Clean up test artifacts
rm -rf test_data/ storage/ received_chunks/
bash tests/run_all_tests.sh
```

---

## Performance Tuning

### For Faster Testing

```yaml
# config/processing_config.yml
processing:
  max_workers_per_node: 2  # Reduce for tests
  simulation_mode: true

# config/distribution_config.yml
distribution:
  replication_factor: 2  # Reduce from 3
  simulation_mode: true
```

### For Production Performance

```yaml
# config/processing_config.yml
processing:
  max_workers_per_node: 8  # Increase for production
  simulation_mode: false

# config/distribution_config.yml
distribution:
  replication_factor: 3
  max_concurrent_distributions: 25  # Increase concurrency
```

### For Large Datasets

```yaml
# config/data_sources.yml
ingestion:
  chunk_size_mb: 50  # Smaller chunks = more parallelism
  max_concurrent_chunks: 20

# config/storage_config.yml
storage:
  performance:
    max_concurrent_writes: 50
```

---

## Development Workflow

### Running Tests During Development

```bash
# Quick test (unit tests only)
pytest tests/pipeline/ -v

# Full test (all suites)
bash tests/run_all_tests.sh

# Watch mode (requires pytest-watch)
ptw tests/pipeline/ -- -v

# Specific test
pytest tests/integration/test_full_pipeline.py::test_complete_pipeline_execution -v -s
```

### Code Coverage

```bash
# Generate coverage report
pytest --cov=src --cov-report=html tests/

# View in browser
open htmlcov/index.html  # Mac
xdg-open htmlcov/index.html  # Linux
```

### Debugging

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Or set environment variable
export LOG_LEVEL=DEBUG
```

---

## Next Steps

1. **Run the test suite**: `bash tests/run_all_tests.sh`
2. **Review architecture**: See `docs/architecture.md`
3. **Check known issues**: See `docs/known_issues.md`
4. **Run the demo**: `python scripts/demo_pipeline.py`
5. **Read Sprint 3 plan**: For performance optimization and real cloud deployment

---

## Getting Help

### Resources
- Architecture documentation: `docs/architecture.md`
- API documentation: Coming in Sprint 3
- Research paper: `docs/research_paper_outline.md`

### Common Commands Reference

```bash
# Setup
pip install -r requirements.txt

# Test
bash tests/run_all_tests.sh
pytest tests/ -v

# Run pipeline
export CLOUD_PROVIDER=gcp
python scripts/demo_pipeline.py

# View logs
tail -f logs/pipeline_$(date +%Y%m%d).log

# Clean up
rm -rf storage/ logs/ test_data/ htmlcov/ .pytest_cache/
```

---

## System Requirements

### Minimum
- Python 3.9+
- 2GB RAM
- 2GB disk space
- Single core

### Recommended
- Python 3.9+
- 8GB RAM
- 10GB disk space
- 4+ cores for parallel testing

### For 1GB+ Datasets
- 16GB RAM
- 50GB disk space
- Fast SSD storage
