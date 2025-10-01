# Day 15-16: Cloud-Agnostic Data Ingestion Engine Implementation

## 🎯 **Design Goal**
One ingestion function that automatically detects which cloud it's running on and pulls from the appropriate data source. No duplicate code for each cloud provider.

---

## 📁 **Configuration Structure**

### **config/data_sources.yml**
```yaml
# Data source configuration for each cloud provider
data_sources:
  aws:
    type: "s3"
    bucket: "ml-training-data-aws"
    region: "us-east-1"
    # For testing: local directory simulating S3
    local_simulation: "./test_data/aws_s3_simulation"
    
  gcp:
    type: "gcs"
    bucket: "ml-training-data-gcp"
    region: "us-central1"
    # For testing: local directory simulating GCS
    local_simulation: "./test_data/gcp_gcs_simulation"
    
  azure:
    type: "blob"
    container: "ml-training-data-azure"
    region: "eastus"
    # For testing: local directory simulating Azure Blob
    local_simulation: "./test_data/azure_blob_simulation"

# Ingestion settings
ingestion:
  chunk_size_mb: 100
  max_concurrent_chunks: 10
  retry_attempts: 3
  retry_delay_seconds: 5
  
# For Sprint 2: use local simulation instead of real cloud storage
use_local_simulation: true
```

---

## 🔧 **Implementation**

### **src/pipeline/ingestion_engine.py**
```python
import os
import asyncio
import hashlib
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass
import yaml
import aiofiles

@dataclass
class DataChunk:
    chunk_id: str
    source_file: str
    chunk_index: int
    size_bytes: int
    checksum: str
    source_cloud: str
    data: Optional[bytes] = None

class CloudDetector:
    """Automatically detect which cloud this node is running on"""
    
    @staticmethod
    def detect_cloud_provider():
        """
        Detect cloud provider by checking instance metadata
        For Sprint 2 testing: use environment variable
        """
        # Check environment variable first (for testing)
        cloud_env = os.environ.get('CLOUD_PROVIDER', '').lower()
        if cloud_env in ['aws', 'gcp', 'azure']:
            return cloud_env
            
        # Try to detect from instance metadata (production)
        # AWS check
        try:
            import requests
            response = requests.get(
                'http://169.254.169.254/latest/meta-data/instance-id',
                timeout=1
            )
            if response.status_code == 200:
                return 'aws'
        except:
            pass
            
        # GCP check
        try:
            response = requests.get(
                'http://metadata.google.internal/computeMetadata/v1/instance/id',
                headers={'Metadata-Flavor': 'Google'},
                timeout=1
            )
            if response.status_code == 200:
                return 'gcp'
        except:
            pass
            
        # Azure check
        try:
            response = requests.get(
                'http://169.254.169.254/metadata/instance?api-version=2021-02-01',
                headers={'Metadata': 'true'},
                timeout=1
            )
            if response.status_code == 200:
                return 'azure'
        except:
            pass
        
        # Default for local development
        return 'local'

class DataSourceAdapter:
    """Abstract adapter for different cloud storage types"""
    
    def __init__(self, cloud_provider: str, config: Dict, use_simulation: bool = True):
        self.cloud_provider = cloud_provider
        self.config = config
        self.use_simulation = use_simulation
        
    async def list_files(self) -> List[str]:
        """List all files in the data source"""
        if self.use_simulation:
            return await self._list_files_local_simulation()
        else:
            return await self._list_files_cloud()
    
    async def read_file(self, file_path: str) -> bytes:
        """Read file contents"""
        if self.use_simulation:
            return await self._read_file_local_simulation(file_path)
        else:
            return await self._read_file_cloud(file_path)
    
    async def _list_files_local_simulation(self) -> List[str]:
        """List files from local simulation directory"""
        sim_dir = Path(self.config.get('local_simulation', './test_data'))
        
        if not sim_dir.exists():
            print(f"⚠️  Simulation directory {sim_dir} doesn't exist, creating it...")
            sim_dir.mkdir(parents=True, exist_ok=True)
            return []
        
        # Find all files recursively
        files = []
        for file_path in sim_dir.rglob('*'):
            if file_path.is_file():
                # Return relative path from simulation root
                relative_path = file_path.relative_to(sim_dir)
                files.append(str(relative_path))
        
        return files
    
    async def _read_file_local_simulation(self, file_path: str) -> bytes:
        """Read file from local simulation directory"""
        sim_dir = Path(self.config.get('local_simulation', './test_data'))
        full_path = sim_dir / file_path
        
        if not full_path.exists():
            raise FileNotFoundError(f"File {file_path} not found in {sim_dir}")
        
        async with aiofiles.open(full_path, 'rb') as f:
            return await f.read()
    
    async def _list_files_cloud(self) -> List[str]:
        """List files from actual cloud storage (future Sprint 3)"""
        # This will be implemented in Sprint 3 when testing with real cloud storage
        raise NotImplementedError("Cloud storage access not yet implemented")
    
    async def _read_file_cloud(self, file_path: str) -> bytes:
        """Read file from actual cloud storage (future Sprint 3)"""
        # This will be implemented in Sprint 3 when testing with real cloud storage
        raise NotImplementedError("Cloud storage access not yet implemented")

class DataIngestionEngine:
    """
    Cloud-agnostic data ingestion engine
    Automatically detects cloud and uses appropriate data source
    """
    
    def __init__(self, node_registry, config_path: str = 'config/data_sources.yml'):
        self.node_registry = node_registry  # From Sprint 1
        
        # Load configuration
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Detect which cloud this node is running on
        self.current_cloud = CloudDetector.detect_cloud_provider()
        print(f"🌐 Detected cloud provider: {self.current_cloud}")
        
        # Get configuration for this cloud
        if self.current_cloud not in self.config['data_sources']:
            raise ValueError(f"No configuration found for cloud provider: {self.current_cloud}")
        
        self.cloud_config = self.config['data_sources'][self.current_cloud]
        
        # Create data source adapter for this cloud
        self.data_source = DataSourceAdapter(
            self.current_cloud,
            self.cloud_config,
            use_simulation=self.config.get('use_local_simulation', True)
        )
        
        # Ingestion settings
        ingestion_config = self.config.get('ingestion', {})
        self.chunk_size_mb = ingestion_config.get('chunk_size_mb', 100)
        self.max_concurrent_chunks = ingestion_config.get('max_concurrent_chunks', 10)
        self.retry_attempts = ingestion_config.get('retry_attempts', 3)
        self.retry_delay_seconds = ingestion_config.get('retry_delay_seconds', 5)
        
        print(f"📥 Ingestion engine initialized for {self.current_cloud}")
        print(f"   Chunk size: {self.chunk_size_mb}MB")
        print(f"   Data source: {self.cloud_config.get('local_simulation', 'cloud storage')}")
    
    async def ingest_batch(self, file_pattern: str = '*') -> List[DataChunk]:
        """
        Main ingestion entry point
        
        Steps:
        1. List files from cloud-specific data source
        2. Chunk large files into manageable pieces
        3. Distribute chunks to other nodes for processing
        """
        print(f"\n📥 Starting data ingestion from {self.current_cloud}...")
        
        # Step 1: List available files
        available_files = await self.data_source.list_files()
        print(f"   Found {len(available_files)} files in data source")
        
        if not available_files:
            print(f"   ⚠️  No files found! Check your data source configuration.")
            return []
        
        # Step 2: Chunk all files
        all_chunks = []
        for file_path in available_files:
            print(f"   Processing file: {file_path}")
            chunks = await self.chunk_file(file_path)
            all_chunks.extend(chunks)
            print(f"   Created {len(chunks)} chunks from {file_path}")
        
        print(f"\n✅ Ingestion complete: {len(all_chunks)} total chunks created")
        
        # Step 3: Distribute chunks to nodes for processing
        await self.distribute_chunks_to_nodes(all_chunks)
        
        return all_chunks
    
    async def chunk_file(self, file_path: str) -> List[DataChunk]:
        """
        Split a file into chunks of specified size
        """
        # Read the entire file
        file_data = await self.data_source.read_file(file_path)
        file_size = len(file_data)
        
        # Calculate chunk size in bytes
        chunk_size_bytes = self.chunk_size_mb * 1024 * 1024
        
        # If file is smaller than chunk size, return as single chunk
        if file_size <= chunk_size_bytes:
            chunk = DataChunk(
                chunk_id=f"{file_path}_chunk_0",
                source_file=file_path,
                chunk_index=0,
                size_bytes=file_size,
                checksum=self._calculate_checksum(file_data),
                source_cloud=self.current_cloud,
                data=file_data
            )
            return [chunk]
        
        # Split into multiple chunks
        chunks = []
        num_chunks = (file_size + chunk_size_bytes - 1) // chunk_size_bytes  # Ceiling division
        
        for i in range(num_chunks):
            start = i * chunk_size_bytes
            end = min((i + 1) * chunk_size_bytes, file_size)
            chunk_data = file_data[start:end]
            
            chunk = DataChunk(
                chunk_id=f"{file_path}_chunk_{i}",
                source_file=file_path,
                chunk_index=i,
                size_bytes=len(chunk_data),
                checksum=self._calculate_checksum(chunk_data),
                source_cloud=self.current_cloud,
                data=chunk_data
            )
            chunks.append(chunk)
        
        return chunks
    
    async def distribute_chunks_to_nodes(self, chunks: List[DataChunk]):
        """
        Distribute chunks across available nodes using Sprint 1's node registry
        """
        print(f"\n🌐 Distributing {len(chunks)} chunks to cluster nodes...")
        
        # Get all healthy nodes from Sprint 1's node registry
        available_nodes = [
            node for node in self.node_registry.nodes.values()
            if node.status == 'healthy'  # Assuming NodeStatus enum from Sprint 1
        ]
        
        if not available_nodes:
            raise RuntimeError("No healthy nodes available for chunk distribution!")
        
        print(f"   Available nodes: {len(available_nodes)}")
        for node in available_nodes:
            print(f"   - {node.node_id} ({node.cloud_provider})")
        
        # Simple round-robin distribution for now
        # (Sprint 3 will add intelligent placement algorithms)
        node_assignments = {}
        for i, chunk in enumerate(chunks):
            target_node = available_nodes[i % len(available_nodes)]
            
            if target_node.node_id not in node_assignments:
                node_assignments[target_node.node_id] = []
            
            node_assignments[target_node.node_id].append(chunk)
        
        # Send chunks to nodes
        distribution_tasks = []
        for node_id, assigned_chunks in node_assignments.items():
            task = self._send_chunks_to_node(node_id, assigned_chunks)
            distribution_tasks.append(task)
        
        # Execute distribution in parallel
        results = await asyncio.gather(*distribution_tasks, return_exceptions=True)
        
        # Check for failures
        failures = [r for r in results if isinstance(r, Exception)]
        if failures:
            print(f"   ⚠️  {len(failures)} distribution failures occurred")
            for failure in failures:
                print(f"      Error: {failure}")
        
        successful = len(results) - len(failures)
        print(f"✅ Distribution complete: {successful}/{len(node_assignments)} nodes received chunks")
    
    async def _send_chunks_to_node(self, node_id: str, chunks: List[DataChunk]):
        """
        Send chunks to a specific node with retry logic
        """
        node = self.node_registry.nodes.get(node_id)
        if not node:
            raise ValueError(f"Node {node_id} not found in registry")
        
        # Try to send with retries
        for attempt in range(self.retry_attempts):
            try:
                # In Sprint 2: simulate sending by storing locally
                # In Sprint 3: actually send over network
                await self._simulate_chunk_transfer(node, chunks)
                
                print(f"   ✅ Sent {len(chunks)} chunks to {node_id}")
                return True
                
            except Exception as e:
                if attempt < self.retry_attempts - 1:
                    print(f"   ⚠️  Retry {attempt + 1}/{self.retry_attempts} for {node_id}: {e}")
                    await asyncio.sleep(self.retry_delay_seconds)
                else:
                    print(f"   ❌ Failed to send chunks to {node_id} after {self.retry_attempts} attempts")
                    raise
    
    async def _simulate_chunk_transfer(self, node, chunks: List[DataChunk]):
        """
        Simulate chunk transfer for Sprint 2 testing
        In Sprint 3, this will be replaced with actual network transfer
        """
        # Create a directory to simulate receiving chunks
        receive_dir = Path(f"./received_chunks/{node.node_id}")
        receive_dir.mkdir(parents=True, exist_ok=True)
        
        for chunk in chunks:
            # Write chunk to simulate transfer
            chunk_file = receive_dir / f"{chunk.chunk_id}.chunk"
            async with aiofiles.open(chunk_file, 'wb') as f:
                await f.write(chunk.data)
        
        # Simulate network delay
        await asyncio.sleep(0.1)  # 100ms simulated transfer time
    
    @staticmethod
    def _calculate_checksum(data: bytes) -> str:
        """Calculate MD5 checksum for data integrity"""
        return hashlib.md5(data).hexdigest()

# Example usage
async def main():
    # This would normally come from Sprint 1
    from types import SimpleNamespace
    
    # Mock node registry for testing
    mock_registry = SimpleNamespace()
    mock_registry.nodes = {
        'aws-node-1': SimpleNamespace(
            node_id='aws-node-1',
            cloud_provider='aws',
            status='healthy'
        ),
        'gcp-node-1': SimpleNamespace(
            node_id='gcp-node-1',
            cloud_provider='gcp',
            status='healthy'
        )
    }
    
    # Set which cloud this node is running on
    os.environ['CLOUD_PROVIDER'] = 'gcp'  # Simulate running on GCP
    
    # Create ingestion engine
    engine = DataIngestionEngine(mock_registry)
    
    # Ingest data
    chunks = await engine.ingest_batch()
    
    print(f"\n📊 Ingestion Summary:")
    print(f"   Total chunks: {len(chunks)}")
    print(f"   Source cloud: {engine.current_cloud}")

if __name__ == '__main__':
    asyncio.run(main())
```

---

## 🧪 **Testing Setup**

### **Test Data Structure**
```bash
# Create test data directories simulating cloud storage
test_data/
├── aws_s3_simulation/
│   ├── training_batch_1.dat  # 500MB test file
│   ├── training_batch_2.dat  # 300MB test file
│   └── validation_data.dat   # 100MB test file
│
├── gcp_gcs_simulation/
│   ├── training_batch_3.dat  # 600MB test file
│   └── training_batch_4.dat  # 400MB test file
│
└── azure_blob_simulation/
    └── training_batch_5.dat  # 200MB test file
```

### **Test Script: tests/test_ingestion_engine.py**
```python
import pytest
import os
import asyncio
from pathlib import Path
from src.pipeline.ingestion_engine import DataIngestionEngine, CloudDetector

@pytest.fixture
def setup_test_data():
    """Create test data files"""
    # Create simulation directories
    test_dirs = {
        'aws': Path('./test_data/aws_s3_simulation'),
        'gcp': Path('./test_data/gcp_gcs_simulation'),
        'azure': Path('./test_data/azure_blob_simulation')
    }
    
    for cloud, dir_path in test_dirs.items():
        dir_path.mkdir(parents=True, exist_ok=True)
        
        # Create a test file with some data
        test_file = dir_path / f'{cloud}_test_data.txt'
        with open(test_file, 'wb') as f:
            # Write 150MB of test data (will create 2 chunks at 100MB chunk size)
            f.write(b'X' * (150 * 1024 * 1024))
    
    yield test_dirs
    
    # Cleanup after tests
    import shutil
    for dir_path in test_dirs.values():
        if dir_path.exists():
            shutil.rmtree(dir_path.parent)

def test_cloud_detection():
    """Test automatic cloud detection"""
    # Test with environment variable
    os.environ['CLOUD_PROVIDER'] = 'gcp'
    assert CloudDetector.detect_cloud_provider() == 'gcp'
    
    os.environ['CLOUD_PROVIDER'] = 'aws'
    assert CloudDetector.detect_cloud_provider() == 'aws'

@pytest.mark.asyncio
async def test_ingestion_from_gcp(setup_test_data, mock_node_registry):
    """Test ingestion when running on GCP node"""
    os.environ['CLOUD_PROVIDER'] = 'gcp'
    
    engine = DataIngestionEngine(mock_node_registry)
    
    # Should automatically use GCP data source
    assert engine.current_cloud == 'gcp'
    assert 'gcp_gcs_simulation' in engine.cloud_config['local_simulation']
    
    # Ingest data
    chunks = await engine.ingest_batch()
    
    # Should have created chunks from 150MB file
    assert len(chunks) == 2  # 150MB / 100MB chunk size = 2 chunks
    assert all(chunk.source_cloud == 'gcp' for chunk in chunks)

@pytest.mark.asyncio
async def test_ingestion_from_aws(setup_test_data, mock_node_registry):
    """Test ingestion when running on AWS node"""
    os.environ['CLOUD_PROVIDER'] = 'aws'
    
    engine = DataIngestionEngine(mock_node_registry)
    
    # Should automatically use AWS data source
    assert engine.current_cloud == 'aws'
    assert 'aws_s3_simulation' in engine.cloud_config['local_simulation']
    
    # Ingest data
    chunks = await engine.ingest_batch()
    
    assert len(chunks) == 2
    assert all(chunk.source_cloud == 'aws' for chunk in chunks)

@pytest.mark.asyncio
async def test_chunk_distribution(setup_test_data, mock_node_registry):
    """Test chunks are distributed across nodes"""
    os.environ['CLOUD_PROVIDER'] = 'gcp'
    
    engine = DataIngestionEngine(mock_node_registry)
    chunks = await engine.ingest_batch()
    
    # Check that received_chunks directory was created for each node
    for node_id in mock_node_registry.nodes.keys():
        receive_dir = Path(f'./received_chunks/{node_id}')
        assert receive_dir.exists()
        
        # Should have some chunks
        chunk_files = list(receive_dir.glob('*.chunk'))
        assert len(chunk_files) > 0
```

---

## ✅ **Acceptance Criteria Verification**

### **1. Can ingest 1GB+ files efficiently (target: <5 minutes)**
```python
# Performance test
@pytest.mark.asyncio
async def test_large_file_ingestion_performance(mock_node_registry):
    """Test 1GB file ingestion performance"""
    import time
    
    os.environ['CLOUD_PROVIDER'] = 'gcp'
    engine = DataIngestionEngine(mock_node_registry)
    
    start_time = time.time()
    chunks = await engine.ingest_batch()
    duration = time.time() - start_time
    
    assert duration < 300  # Less than 5 minutes
    print(f"Ingested {len(chunks)} chunks in {duration:.2f} seconds")
```

### **2. Chunks distributed evenly across available nodes**
```python
# Distribution balance test
@pytest.mark.asyncio
async def test_even_chunk_distribution(mock_node_registry):
    """Test chunks distributed evenly"""
    os.environ['CLOUD_PROVIDER'] = 'gcp'
    engine = DataIngestionEngine(mock_node_registry)
    
    chunks = await engine.ingest_batch()
    
    # Count chunks per node
    from collections import Counter
    receive_dir = Path('./received_chunks')
    chunks_per_node = {}
    
    for node_dir in receive_dir.iterdir():
        if node_dir.is_dir():
            chunk_count = len(list(node_dir.glob('*.chunk')))
            chunks_per_node[node_dir.name] = chunk_count
    
    # Check distribution is roughly even
    avg = sum(chunks_per_node.values()) / len(chunks_per_node)
    for count in chunks_per_node.values():
        assert abs(count - avg) / avg < 0.3  # Within 30% of average
```

### **3. Graceful handling of node unavailability**
```python
# Failure handling test
@pytest.mark.asyncio
async def test_node_unavailable_during_ingestion(mock_node_registry):
    """Test handling of unavailable nodes"""
    # Mark one node as unhealthy
    mock_node_registry.nodes['aws-node-1'].status = 'unhealthy'
    
    os.environ['CLOUD_PROVIDER'] = 'gcp'
    engine = DataIngestionEngine(mock_node_registry)
    
    # Should still succeed with remaining healthy nodes
    chunks = await engine.ingest_batch()
    assert len(chunks) > 0
```

### **4. Basic retry logic for transient failures**
```python
# Retry logic test
@pytest.mark.asyncio
async def test_retry_on_transient_failure(mock_node_registry):
    """Test retry logic works"""
    os.environ['CLOUD_PROVIDER'] = 'gcp'
    engine = DataIngestionEngine(mock_node_registry)
    
    # Simulate transient failure (will be retried)
    with patch.object(engine, '_simulate_chunk_transfer', side_effect=[
        Exception("Simulated failure"),  # First attempt fails
        None  # Second attempt succeeds
    ]):
        chunks = await engine.ingest_batch()
        # Should succeed after retry
        assert len(chunks) > 0
```

This implementation gives you a clean, cloud-agnostic ingestion engine that's ready for Sprint 2 testing! 🚀