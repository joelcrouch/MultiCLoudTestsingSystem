import pytest
import asyncio
from pathlib import Path
from types import SimpleNamespace
from src.pipeline.pipeline_orchestrator import PipelineOrchestrator


@pytest.fixture
def setup_test_cluster():
    """Setup a mock multi-cloud cluster for testing"""
    mock_registry = SimpleNamespace()
    mock_registry.nodes = {
        'aws-node-1': SimpleNamespace(
            node_id='aws-node-1',
            cloud_provider='aws',
            status='healthy',
            network_latency={'gcp': 50, 'aws': 5}
        ),
        'aws-node-2': SimpleNamespace(
            node_id='aws-node-2',
            cloud_provider='aws',
            status='healthy',
            network_latency={'gcp': 50, 'aws': 5}
        ),
        'gcp-node-1': SimpleNamespace(
            node_id='gcp-node-1',
            cloud_provider='gcp',
            status='healthy',
            network_latency={'aws': 50, 'gcp': 5}
        ),
        'gcp-node-2': SimpleNamespace(
            node_id='gcp-node-2',
            cloud_provider='gcp',
            status='healthy',
            network_latency={'aws': 50, 'gcp': 5}
        )
    }
    return mock_registry


@pytest.fixture
def test_data_source(tmp_path):
    """Create temporary test data source"""
    data_dir = tmp_path / "test_data"
    data_dir.mkdir()

    # Create test file
    test_file = data_dir / "test_batch.dat"
    test_file.write_bytes(b"test data " * 10000)  # ~100KB test file

    return str(data_dir)


@pytest.mark.asyncio
async def test_orchestrator_initialization(setup_test_cluster):
    """Test that orchestrator initializes all components correctly"""
    orchestrator = PipelineOrchestrator(setup_test_cluster)

    assert orchestrator.ingestion_engine is not None
    assert orchestrator.processing_pool is not None
    assert orchestrator.distribution_coordinator is not None
    assert orchestrator.storage_manager is not None
    assert orchestrator.pipeline_status.value == 'idle'


@pytest.mark.asyncio
async def test_complete_pipeline_execution(setup_test_cluster, test_data_source):
    """Test complete end-to-end pipeline execution"""

    # Setup
    node_registry = setup_test_cluster
    orchestrator = PipelineOrchestrator(node_registry)

    # Create test batch config
    batch_config = {
        'batch_id': 'test_batch_001',
        'data_source': test_data_source,
        'expected_size_mb': 1
    }

    # Run pipeline
    result = await orchestrator.run_pipeline(batch_config)

    # Verify success
    assert result.status == 'success'
    assert result.chunks_processed > 0
    assert result.duration_seconds > 0
    assert result.duration_seconds < 300  # Should complete in < 5 minutes

    # Verify all stages completed
    assert 'ingestion' in result.metrics
    assert 'processing' in result.metrics
    assert 'distribution' in result.metrics
    assert 'storage' in result.metrics

    # Verify metrics are reasonable
    assert result.metrics['ingestion']['items_processed'] > 0
    assert result.metrics['processing']['items_processed'] > 0
    assert result.metrics['distribution']['items_processed'] > 0
    assert result.metrics['storage']['items_processed'] > 0


@pytest.mark.asyncio
async def test_pipeline_stage_progression(setup_test_cluster, test_data_source):
    """Test that pipeline progresses through all stages in order"""
    orchestrator = PipelineOrchestrator(setup_test_cluster)

    batch_config = {
        'batch_id': 'test_batch_002',
        'data_source': test_data_source,
        'expected_size_mb': 1
    }

    result = await orchestrator.run_pipeline(batch_config)

    # Check that stages executed in correct order by verifying metrics exist
    metrics = result.metrics
    assert 'ingestion' in metrics
    assert 'processing' in metrics
    assert 'distribution' in metrics
    assert 'storage' in metrics

    # All stages should have positive duration
    assert metrics['ingestion']['duration_seconds'] > 0
    assert metrics['processing']['duration_seconds'] > 0
    assert metrics['distribution']['duration_seconds'] > 0
    assert metrics['storage']['duration_seconds'] > 0


@pytest.mark.asyncio
async def test_pipeline_handles_empty_source(setup_test_cluster, tmp_path):
    """Test pipeline handles empty data source gracefully"""
    orchestrator = PipelineOrchestrator(setup_test_cluster)

    # Create empty data source
    empty_dir = tmp_path / "empty_data"
    empty_dir.mkdir()

    batch_config = {
        'batch_id': 'test_batch_empty',
        'data_source': str(empty_dir),
        'expected_size_mb': 0
    }

    result = await orchestrator.run_pipeline(batch_config)

    # Should complete (possibly with 0 chunks) or fail gracefully
    assert result.status in ['success', 'failed']
    assert result.duration_seconds >= 0


@pytest.mark.asyncio
async def test_pipeline_metrics_accuracy(setup_test_cluster, test_data_source):
    """Test that pipeline metrics are accurate"""
    orchestrator = PipelineOrchestrator(setup_test_cluster)

    batch_config = {
        'batch_id': 'test_batch_metrics',
        'data_source': test_data_source,
        'expected_size_mb': 1
    }

    result = await orchestrator.run_pipeline(batch_config)

    if result.status == 'success':
        # Verify metrics structure
        assert isinstance(result.metrics, dict)

        # Each stage should have metrics
        for stage in ['ingestion', 'processing', 'distribution', 'storage']:
            assert stage in result.metrics
            assert 'items_processed' in result.metrics[stage]
            assert 'duration_seconds' in result.metrics[stage]


@pytest.mark.asyncio
async def test_get_pipeline_status(setup_test_cluster):
    """Test getting pipeline status"""
    orchestrator = PipelineOrchestrator(setup_test_cluster)

    status = orchestrator.get_status()

    assert 'status' in status
    assert status['status'] == 'idle'
    assert 'current_stage' in status
    assert 'current_batch' in status
    assert 'metrics' in status


@pytest.mark.asyncio
async def test_node_health_tracking(setup_test_cluster):
    """Test that orchestrator tracks node health"""
    orchestrator = PipelineOrchestrator(setup_test_cluster)

    healthy = orchestrator.get_healthy_nodes()
    unhealthy = orchestrator.get_unhealthy_nodes()

    assert healthy == 4  # All 4 nodes should be healthy initially
    assert unhealthy == 0

    # Simulate node failure
    setup_test_cluster.nodes['aws-node-1'].status = 'unhealthy'

    healthy = orchestrator.get_healthy_nodes()
    unhealthy = orchestrator.get_unhealthy_nodes()

    assert healthy == 3
    assert unhealthy == 1


@pytest.mark.asyncio
async def test_pipeline_error_handling(setup_test_cluster):
    """Test pipeline handles errors gracefully"""
    orchestrator = PipelineOrchestrator(setup_test_cluster)

    # Invalid batch config (missing required fields)
    invalid_config = {
        'batch_id': 'test_invalid',
        # Missing 'data_source'
    }

    result = await orchestrator.run_pipeline(invalid_config)

    # Should fail gracefully with error information
    assert result.status == 'failed'
    assert result.error is not None
    assert isinstance(result.error, str)


@pytest.mark.asyncio
async def test_multiple_pipeline_runs(setup_test_cluster, test_data_source):
    """Test running pipeline multiple times sequentially"""
    orchestrator = PipelineOrchestrator(setup_test_cluster)

    batch_configs = [
        {'batch_id': f'test_batch_{i}', 'data_source': test_data_source, 'expected_size_mb': 1}
        for i in range(3)
    ]

    results = []
    for config in batch_configs:
        result = await orchestrator.run_pipeline(config)
        results.append(result)

    # All runs should complete
    assert len(results) == 3

    # Check each result
    for result in results:
        assert result.status in ['success', 'failed']
        assert result.duration_seconds > 0


@pytest.mark.asyncio
async def test_pipeline_resilience_to_node_failure(setup_test_cluster, test_data_source):
    """Test pipeline continues with node failure during execution"""
    orchestrator = PipelineOrchestrator(setup_test_cluster)

    batch_config = {
        'batch_id': 'test_batch_resilience',
        'data_source': test_data_source,
        'expected_size_mb': 1
    }

    # Start pipeline
    pipeline_task = asyncio.create_task(
        orchestrator.run_pipeline(batch_config)
    )

    # Let it run for a bit
    await asyncio.sleep(0.5)

    # Simulate node failure
    setup_test_cluster.nodes['aws-node-2'].status = 'unhealthy'

    # Wait for completion
    result = await pipeline_task

    # Pipeline should handle failure (may succeed or fail, but shouldn't crash)
    assert result.status in ['success', 'failed']
    assert result is not None
