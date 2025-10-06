import asyncio
import aiofiles
import hashlib
import json
import shutil
import time
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional
import yaml


class StorageStatus(Enum):
    PENDING="pending"
    STORED="stored"
    FAILED="failed"
    VERIFIED="verified"

@dataclass
class StoredChunk:
    chunk_id: str
    storage_path: str
    checksum: str
    size_bytes: int
    stored_at: str
    node_id: str
    cloud_provider: str
    replicas: List[str]  # Paths to all replicas
    status: StorageStatus = StorageStatus.PENDING
    metadata: Optional[Dict] = None

    def to_dict(self)->Dict:
        data=asdict(self)
        data['status']=self.status.value
        return data
    

@dataclass
class StorageCheckpoint:
    checkpoint_id: str
    timestamp: str
    chunks_stored: int
    total_size_bytes: int
    chunks: List[str]  # List of chunk_ids in this checkpoint

class StorageBackend:
    """base class for storage bakckends"""
    def __init__(self, config: Dict):
        self.config = config
    
    async def write(self, path: str, data: bytes) -> bool:
        raise NotImplementedError()
    
    async def read(self, path: str) -> bytes:
        raise NotImplementedError()
    
    async def exists(self, path: str) -> bool:
        raise NotImplementedError()
    
    async def delete(self, path: str) -> bool:
        raise NotImplementedError()
    
    async def list_files(self, prefix: str) -> List[str]:
        raise NotImplementedError()
    
class LocalStorageBackend(StorageBackend):
    def __init__(self, config: Dict):
        super().__init__(config)
        self.base_path = Path(config.get('base_path', './storage/data'))
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    async def write(self, path: str, data: bytes) -> bool:
        """Write data to local filesystem"""
        full_path = self.base_path / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            async with aiofiles.open(full_path, 'wb') as f:
                await f.write(data)
            return True
        except Exception as e:
            print(f"   ❌ Write failed: {path}: {e}")
            return False
    
    async def read(self, path: str) -> bytes:
        """Read data from local filesystem"""
        full_path = self.base_path / path
        
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        
        async with aiofiles.open(full_path, 'rb') as f:
            return await f.read()
    
    async def exists(self, path: str) -> bool:
        """Check if file exists"""
        full_path = self.base_path / path
        return full_path.exists()
    
    async def delete(self, path: str) -> bool:
        """Delete file"""
        full_path = self.base_path / path
        
        try:
            if full_path.exists():
                full_path.unlink()
            return True
        except Exception as e:
            print(f"   ⚠️  Delete failed: {path}: {e}")
            return False
    
    async def list_files(self, prefix: str = "") -> List[str]:
        """List files with given prefix"""
        search_path = self.base_path / prefix if prefix else self.base_path
        
        if not search_path.exists():
            return []
        
        files = []
        for file_path in search_path.rglob('*'):
            if file_path.is_file():
                relative_path = file_path.relative_to(self.base_path)
                files.append(str(relative_path))
        
        return files
    
    def get_storage_stats(self) -> Dict:
        """Get storage usage statistics"""
        total_size = 0
        file_count = 0
        
        for file_path in self.base_path.rglob('*'):
            if file_path.is_file():
                total_size += file_path.stat().st_size
                file_count += 1
        
        return {
            'total_size_bytes': total_size,
            'total_size_gb': total_size / (1024**3),
            'file_count': file_count,
            'base_path': str(self.base_path)
        }
    

#Cloud storage backends in s3? i think why not now?


class StorageManager:
    """
    Manages persistent storage of distributed data chunks
    """
    
    def __init__(self, node_registry, config_path: str = 'config/storage_config.yml'):
        self.node_registry = node_registry
        
        # Load configuration
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        storage_config = self.config.get('storage', {})
        
        # Initialize storage backend
        if self.config.get('use_local_storage', True):
            backend_config = storage_config.get('backends', {}).get('local', {})
            self.backend = LocalStorageBackend(backend_config)
        else:
            # Cloud storage backends (Sprint 3)
            raise NotImplementedError("Cloud storage backends not yet implemented")
        
        # Data organization settings
        org_config = storage_config.get('organization', {})
        self.partition_by = org_config.get('partition_by', 'date')
        self.create_checkpoints = org_config.get('create_checkpoints', True)
        self.checkpoint_interval = org_config.get('checkpoint_interval_chunks', 1000)
        
        # Integrity settings
        integrity_config = storage_config.get('integrity', {})
        self.verify_on_write = integrity_config.get('verify_on_write', True)
        self.verify_on_read = integrity_config.get('verify_on_read', True)
        self.checksum_algorithm = integrity_config.get('checksum_algorithm', 'md5')
        self.store_metadata = integrity_config.get('store_metadata', True)
        
        # Cleanup settings
        cleanup_config = storage_config.get('cleanup', {})
        self.enable_auto_cleanup = cleanup_config.get('enable_auto_cleanup', True)
        self.retention_days = cleanup_config.get('retention_days', 30)
        self.compress_old_data = cleanup_config.get('compress_old_data', True)
        self.compression_age_days = cleanup_config.get('compression_age_days', 7)
        
        # Performance settings
        perf_config = storage_config.get('performance', {})
        self.max_concurrent_writes = perf_config.get('max_concurrent_writes', 20)
        
        # Tracking
        self.stored_chunks: List[StoredChunk] = []
        self.checkpoints: List[StorageCheckpoint] = []
        self.metadata_path = Path('./storage/metadata')
        self.metadata_path.mkdir(parents=True, exist_ok=True)
        
        print(f"💾 Storage Manager initialized")
        print(f"   Backend: {type(self.backend).__name__}")
        print(f"   Partition by: {self.partition_by}")
        print(f"   Checkpoints: {self.create_checkpoints}")
        print(f"   Auto cleanup: {self.enable_auto_cleanup}")
    
    async def store_distributed_chunks(self, distribution_tasks: List) -> List[StoredChunk]:
        """
        Main entry point: Store distributed chunks persistently
        
        Args:
            distribution_tasks: List of DistributionTask results from coordinator
            
        Returns:
            List of StoredChunk results
        """
        print(f"\n💾 Starting storage of {len(distribution_tasks)} distributed chunks...")
        
        # Filter successful distributions
        successful_tasks = [
            task for task in distribution_tasks
            if hasattr(task, 'status') and task.status.value == 'completed'
        ]
        
        print(f"   {len(successful_tasks)} chunks successfully distributed")
        print(f"   Processing {sum(len(t.replicas) for t in successful_tasks)} total replicas")
        
        # Store all replicas with concurrency control
        storage_results = await self._store_replicas_with_concurrency(successful_tasks)
        
        # Create checkpoint if configured
        if self.create_checkpoints and len(self.stored_chunks) % self.checkpoint_interval == 0:
            await self._create_checkpoint()
        
        # Run cleanup if enabled
        if self.enable_auto_cleanup:
            await self._run_cleanup()
        
        # Generate summary
        total_stored = len([c for c in storage_results if c.status == StorageStatus.STORED])
        total_failed = len([c for c in storage_results if c.status == StorageStatus.FAILED])
        
        print(f"\n✅ Storage complete:")
        print(f"   Successfully stored: {total_stored}")
        print(f"   Failed: {total_failed}")
        print(f"   Total storage: {self._calculate_total_storage_size():.2f} GB")
        
        return storage_results
    
    async def _store_replicas_with_concurrency(self, distribution_tasks: List) -> List[StoredChunk]:
        """Store all replicas with concurrency control"""
        
        # Create storage tasks for all replicas
        storage_tasks = []
        for dist_task in distribution_tasks:
            for replica in dist_task.replicas:
                if replica.status.value == 'completed':
                    storage_tasks.append(
                        self._store_replica(dist_task, replica)
                    )
        
        # Execute with concurrency limit
        semaphore = asyncio.Semaphore(self.max_concurrent_writes)
        
        async def bounded_store(task):
            async with semaphore:
                return await task
        
        results = await asyncio.gather(
            *[bounded_store(task) for task in storage_tasks],
            return_exceptions=True
        )
        
        # Filter out exceptions
        stored_chunks = [r for r in results if isinstance(r, StoredChunk)]
        
        return stored_chunks
    
    async def _store_replica(self, dist_task, replica) -> StoredChunk:
        """Store a single replica"""
        
        try:
            # Generate storage path based on partition strategy
            storage_path = self._generate_storage_path(replica)
            
            # Get data from distribution task
            data = dist_task.chunk_data
            
            # Calculate checksum
            checksum = self._calculate_checksum(data)
            
            # Write to storage
            success = await self.backend.write(storage_path, data)
            
            if not success:
                raise Exception("Write operation failed")
            
            # Verify if configured
            if self.verify_on_write:
                await self._verify_stored_data(storage_path, data, checksum)
            
            # Create stored chunk record
            stored_chunk = StoredChunk(
                chunk_id=replica.chunk_id,
                storage_path=storage_path,
                checksum=checksum,
                size_bytes=len(data),
                stored_at=datetime.now().isoformat(),
                node_id=replica.target_node,
                cloud_provider=replica.cloud_provider,
                replicas=[storage_path],
                status=StorageStatus.STORED,
                metadata={
                    'replica_id': replica.replica_id,
                    'source_task': dist_task.task_id
                }
            )
            
            # Store metadata if configured
            if self.store_metadata:
                await self._store_metadata(stored_chunk)
            
            self.stored_chunks.append(stored_chunk)
            
            return stored_chunk
            
        except Exception as e:
            print(f"   ❌ Storage failed for {replica.replica_id}: {e}")
            return StoredChunk(
                chunk_id=replica.chunk_id,
                storage_path="",
                checksum="",
                size_bytes=0,
                stored_at=datetime.now().isoformat(),
                node_id=replica.target_node,
                cloud_provider=replica.cloud_provider,
                replicas=[],
                status=StorageStatus.FAILED,
                metadata={'error': str(e)}
            )
    
    def _generate_storage_path(self, replica) -> str:
        """Generate storage path based on partition strategy"""
        
        if self.partition_by == 'date':
            # Partition by date: YYYY/MM/DD/chunk_id
            now = datetime.now()
            return f"{now.year}/{now.month:02d}/{now.day:02d}/{replica.replica_id}.dat"
        
        elif self.partition_by == 'cloud':
            # Partition by cloud provider
            return f"{replica.cloud_provider}/{replica.replica_id}.dat"
        
        elif self.partition_by == 'node':
            # Partition by node
            return f"{replica.target_node}/{replica.replica_id}.dat"
        
        else:
            # Default: flat structure
            return f"{replica.replica_id}.dat"
    
    def _calculate_checksum(self, data: bytes) -> str:
        """Calculate checksum for data integrity"""
        if self.checksum_algorithm == 'md5':
            return hashlib.md5(data).hexdigest()
        elif self.checksum_algorithm == 'sha256':
            return hashlib.sha256(data).hexdigest()
        else:
            return hashlib.md5(data).hexdigest()
    
    async def _verify_stored_data(self, path: str, original_data: bytes, expected_checksum: str):
        """Verify stored data matches original"""
        
        # Read back the data
        stored_data = await self.backend.read(path)
        
        # Calculate checksum
        actual_checksum = self._calculate_checksum(stored_data)
        
        # Compare
        if actual_checksum != expected_checksum:
            raise Exception(f"Checksum mismatch: expected {expected_checksum}, got {actual_checksum}")
        
        # Verify data matches
        if stored_data != original_data:
            raise Exception("Data mismatch after storage")
    
    async def _store_metadata(self, stored_chunk: StoredChunk):
        """Store chunk metadata separately"""
        
        metadata_file = self.metadata_path / f"{stored_chunk.chunk_id}.json"
        
        async with aiofiles.open(metadata_file, 'w') as f:
            await f.write(json.dumps(stored_chunk.to_dict(), indent=2))
    
    async def _create_checkpoint(self):
        """Create a checkpoint of current storage state"""
        
        checkpoint_id = f"checkpoint_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        checkpoint = StorageCheckpoint(
            checkpoint_id=checkpoint_id,
            timestamp=datetime.now().isoformat(),
            chunks_stored=len(self.stored_chunks),
            total_size_bytes=sum(c.size_bytes for c in self.stored_chunks),
            chunks=[c.chunk_id for c in self.stored_chunks]
        )
        
        self.checkpoints.append(checkpoint)
        
        # Save checkpoint to disk
        checkpoint_file = self.metadata_path / f"{checkpoint_id}.json"
        async with aiofiles.open(checkpoint_file, 'w') as f:
            await f.write(json.dumps(asdict(checkpoint), indent=2))
        
        print(f"   📸 Checkpoint created: {checkpoint_id}")
    
    async def _run_cleanup(self):
        """Run cleanup of old data"""
        
        # Get cutoff date for retention
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        
        # Find old chunks
        old_chunks = [
            chunk for chunk in self.stored_chunks
            if datetime.fromisoformat(chunk.stored_at) < cutoff_date
        ]
        
        if old_chunks:
            print(f"   🧹 Cleaning up {len(old_chunks)} old chunks...")
            
            for chunk in old_chunks:
                try:
                    # Delete from storage
                    await self.backend.delete(chunk.storage_path)
                    
                    # Remove from tracking
                    self.stored_chunks.remove(chunk)
                    
                except Exception as e:
                    print(f"   ⚠️  Cleanup failed for {chunk.chunk_id}: {e}")
    
    def _calculate_total_storage_size(self) -> float:
        """Calculate total storage size in GB"""
        total_bytes = sum(c.size_bytes for c in self.stored_chunks)
        return total_bytes / (1024**3)
    
    async def retrieve_chunk(self, chunk_id: str) -> Optional[bytes]:
        """Retrieve a stored chunk by ID"""
        
        # Find chunk in stored chunks
        chunk = next((c for c in self.stored_chunks if c.chunk_id == chunk_id), None)
        
        if not chunk:
            print(f"   ⚠️  Chunk not found: {chunk_id}")
            return None
        
        try:
            # Read from storage
            data = await self.backend.read(chunk.storage_path)
            
            # Verify if configured
            if self.verify_on_read:
                actual_checksum = self._calculate_checksum(data)
                if actual_checksum != chunk.checksum:
                    print(f"   ❌ Checksum mismatch on read: {chunk_id}")
                    return None
            
            return data
            
        except Exception as e:
            print(f"   ❌ Retrieval failed for {chunk_id}: {e}")
            return None
    
    def get_storage_statistics(self) -> Dict:
        """Get storage statistics"""
        
        # Get backend stats
        backend_stats = {}
        if hasattr(self.backend, 'get_storage_stats'):
            backend_stats = self.backend.get_storage_stats()
        
        # Calculate statistics by cloud
        by_cloud = {}
        for chunk in self.stored_chunks:
            cloud = chunk.cloud_provider
            if cloud not in by_cloud:
                by_cloud[cloud] = {'count': 0, 'size_bytes': 0}
            by_cloud[cloud]['count'] += 1
            by_cloud[cloud]['size_bytes'] += chunk.size_bytes
        
        return {
            'total_chunks': len(self.stored_chunks),
            'total_size_gb': self._calculate_total_storage_size(),
            'checkpoints_created': len(self.checkpoints),
            'storage_by_cloud': by_cloud,
            'backend_stats': backend_stats,
            'successful_stores': len([c for c in self.stored_chunks if c.status == StorageStatus.STORED]),
            'failed_stores': len([c for c in self.stored_chunks if c.status == StorageStatus.FAILED])
        }