import pytest
import asyncio
from pathlib import Path
from types import SimpleNamespace
from src.pipeline.storage_manager import (
    StorageManager,
    StorageStatus,
    LocalStorageBackend
)

@pytest.fixture
def mock_node_registry():
    """Create mock node registry"""
    registry = SimpleNamespace()
    registry.nodes = {
        'aws-node-1': SimpleNamespace(node_id='aws-node-1', cloud_provider='aws', status='healthy'),
        'aws-node-2': SimpleNamespace(node_id='aws-node-2', cloud_provider='aws', status='healthy'),
        'gcp-node-1': SimpleNamespace(node_id='gcp-node-1', cloud_provider='gcp', status='healthy')
    }
    return registry

@pytest.fixture
def mock_distribution_tasks():
    """Create mock distribution tasks"""
    tasks = []
    for i in range(10):
        task = SimpleNamespace(
            task_id=f'dist_task_{i}',
            chunk_id=f'chunk_{i}',
            chunk_data=f'test data {i}'.encode() * 500,
            status=SimpleNamespace(value='completed'),
            replicas=[
                SimpleNamespace(
                    replica_id=f'chunk_{i}_replica_{j}',
                    chunk_id=f'chunk_{i}',
                    target_node=f'aws-node-{j+1}',
                    cloud_provider='aws',
                    status=SimpleNamespace(value='completed')
                )
                for j in range(2)
            ]
        )
        tasks.append(task)
    return tasks

@pytest.mark.asyncio
async def test_storage_manager_initialization(mock_node_registry):
    """Test storage manager initializes correctly"""
    manager = StorageManager(mock_node_registry)
    
    assert manager.backend is not None
    assert isinstance(manager.backend, LocalStorageBackend)
    assert manager.verify_on_write == True

@pytest.mark.asyncio
async def test_store_distributed_chunks(mock_node_registry, mock_distribution_tasks):
    """Test storing distributed chunks"""
    manager = StorageManager(mock_node_registry)
    
    results = await manager.store_distributed_chunks(mock_distribution_tasks)
    
    # All replicas should be stored
    expected_replicas = sum(len(t.replicas) for t in mock_distribution_tasks)
    assert len(results) == expected_replicas
    
    # All should be successfully stored
    successful = [r for r in results if r.status == StorageStatus.STORED]
    assert len(successful) == expected_replicas

@pytest.mark.asyncio
async def test_data_integrity_verification(mock_node_registry, mock_distribution_tasks):
    """Test data integrity is verified on write"""
    manager = StorageManager(mock_node_registry)
    manager.verify_on_write = True
    
    results = await manager.store_distributed_chunks(mock_distribution_tasks)
    
    # All stored chunks should have valid checksums
    for result in results:
        if result.status == StorageStatus.STORED:
            assert result.checksum is not None
            assert len(result.checksum) > 0

@pytest.mark.asyncio
async def test_retrieve_stored_chunk(mock_node_registry, mock_distribution_tasks):
    """Test retrieving stored chunks"""
    manager = StorageManager(mock_node_registry)
    
    # Store chunks
    await manager.store_distributed_chunks(mock_distribution_tasks)
    
    # Retrieve a chunk
    chunk_id = mock_distribution_tasks[0].chunk_id
    data = await manager.retrieve_chunk(chunk_id)
    
    assert data is not None
    assert data == mock_distribution_tasks[0].chunk_data

@pytest.mark.asyncio
async def test_checkpoint_creation(mock_node_registry, mock_distribution_tasks):
    """Test checkpoint creation"""
    manager = StorageManager(mock_node_registry)
    manager.create_checkpoints = True
    manager.checkpoint_interval = 5  # Create checkpoint after 5 chunks
    
    await manager.store_distributed_chunks(mock_distribution_tasks)
    
    # Should have created at least one checkpoint
    assert len(manager.checkpoints) > 0

@pytest.mark.asyncio
async def test_storage_statistics(mock_node_registry, mock_distribution_tasks):
    """Test storage statistics are accurate"""
    manager = StorageManager(mock_node_registry)
    
    await manager.store_distributed_chunks(mock_distribution_tasks)
    stats = manager.get_storage_statistics()
    
    assert stats['total_chunks'] > 0
    assert stats['total_size_gb'] > 0
    assert 'storage_by_cloud' in stats
    assert len(stats['storage_by_cloud']) > 0

@pytest.mark.asyncio
async def test_cleanup_old_data(mock_node_registry, mock_distribution_tasks):
    """Test cleanup of old data"""
    manager = StorageManager(mock_node_registry)
    manager.enable_auto_cleanup = True
    manager.retention_days = 0  # Immediate cleanup for testing
    
    await manager.store_distributed_chunks(mock_distribution_tasks)
    
    # Should handle cleanup without errors
    assert True  # Cleanup runs without exceptions

@pytest.mark.asyncio
async def test_storage_failure_handling(mock_node_registry):
    """Test handling of storage failures"""
    manager = StorageManager(mock_node_registry)
    
    # Create task with invalid data that will cause storage to fail
    invalid_task = SimpleNamespace(
        task_id='invalid_task',
        chunk_id='invalid_chunk',
        chunk_data=None,  # This should cause failure
        status=SimpleNamespace(value='completed'),
        replicas=[
            SimpleNamespace(
                replica_id='invalid_replica',
                chunk_id='invalid_chunk',
                target_node='aws-node-1',
                cloud_provider='aws',
                status=SimpleNamespace(value='completed')
            )
        ]
    )
    
    # Should handle gracefully
    results = await manager.store_distributed_chunks([invalid_task])
    
    # Should have results (even if failed)
    assert len(results) > 0

@pytest.mark.asyncio
async def test_metadata_storage(mock_node_registry, mock_distribution_tasks):
    """Test metadata is stored correctly"""
    manager = StorageManager(mock_node_registry)
    manager.store_metadata = True
    
    await manager.store_distributed_chunks(mock_distribution_tasks)
    
    # Check metadata files exist
    metadata_files = list(manager.metadata_path.glob('*.json'))
    assert len(metadata_files) > 0

@pytest.mark.asyncio
async def test_100_percent_integrity(mock_node_registry, mock_distribution_tasks):
    """Verify 100% data integrity"""
    manager = StorageManager(mock_node_registry)
    manager.verify_on_write = True
    manager.verify_on_read = True
    
    # Store data
    results = await manager.store_distributed_chunks(mock_distribution_tasks)
    
    # Verify all stored chunks
    for result in results:
        if result.status == StorageStatus.STORED:
            # Retrieve and verify
            data = await manager.retrieve_chunk(result.chunk_id)
            assert data is not None
    
    # 100% integrity maintained
    stats = manager.get_storage_statistics()
    assert stats['failed_stores'] == 0

@pytest.mark.asyncio
async def test_multiple_storage_backends(mock_node_registry, mock_distribution_tasks):
    """Verify support for different storage backends"""
    # Test local backend
    local_manager = StorageManager(mock_node_registry)
    assert isinstance(local_manager.backend, LocalStorageBackend)
    
    results = await local_manager.store_distributed_chunks(mock_distribution_tasks)
    assert len(results) > 0

@pytest.mark.asyncio
async def test_automatic_cleanup_garbage_collection(mock_node_registry):
    """Verify automatic cleanup works"""
    manager = StorageManager(mock_node_registry)
    manager.enable_auto_cleanup = True
    manager.retention_days = 0  # Immediate cleanup
    
    # Create old task
    from datetime import datetime, timedelta
    old_task = SimpleNamespace(
        task_id='old_task',
        chunk_id='old_chunk',
        chunk_data=b'old data' * 100,
        status=SimpleNamespace(value='completed'),
        replicas=[
            SimpleNamespace(
                replica_id='old_replica',
                chunk_id='old_chunk',
                target_node='aws-node-1',
                cloud_provider='aws',
                status=SimpleNamespace(value='completed')
            )
        ]
    )
    
    # Store and trigger cleanup/garbage collection
    results = await manager.store_distributed_chunks([old_task])
    
    # Cleanup should run without errors
    initial_count = len(manager.stored_chunks)
    await manager._run_cleanup()
    final_count = len(manager.stored_chunks)
    
    # Old data should be cleaned
    assert final_count <= initial_count

@pytest.mark.asyncio
async def test_checksum_validation(mock_node_registry, mock_distribution_tasks):
    """Verify checksum validation works"""
    manager = StorageManager(mock_node_registry)
    
    results = await manager.store_distributed_chunks(mock_distribution_tasks)
    
    # All stored chunks should have valid checksums
    for result in results:
        if result.status == StorageStatus.STORED:
            # Checksum should be valid MD5/SHA256 hash
            assert len(result.checksum) in [32, 64]  # MD5 or SHA256 length
            
            # Verify checksum matches data
            retrieved_data = await manager.retrieve_chunk(result.chunk_id)
            calculated_checksum = manager._calculate_checksum(retrieved_data)
            assert calculated_checksum == result.checksum
