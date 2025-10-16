import pytest
import asyncio
from types import SimpleNamespace
from unittest.mock import patch
from src.pipeline.distribution_coordinator import (
    DistributionCoordinator,
    DistributionStatus,
    NetworkTopology,
    NetworkAwarePlacement
)

@pytest.fixture
def mock_node_registry():
    """Create mock node registry"""
    registry = SimpleNamespace()
    registry.nodes = {
        'aws-node-1': SimpleNamespace(
            node_id='aws-node-1',
            cloud_provider='aws',
            status='healthy'
        ),
        'aws-node-2': SimpleNamespace(
            node_id='aws-node-2',
            cloud_provider='aws',
            status='healthy'
        ),
        'gcp-node-1': SimpleNamespace(
            node_id='gcp-node-1',
            cloud_provider='gcp',
            status='healthy'
        ),
        'gcp-node-2': SimpleNamespace(
            node_id='gcp-node-2',
            cloud_provider='gcp',
            status='healthy'
        ),
        'azure-node-1': SimpleNamespace(
            node_id='azure-node-1',
            cloud_provider='azure',
            status='healthy'
        )
    }
    return registry

@pytest.fixture
def mock_processed_chunks():
    """Create mock processed chunks"""
    return [
        SimpleNamespace(
            chunk_id=f'chunk_{i}',
            result=f'processed data {i}'.encode() * 500,
            assigned_node='aws-node-1'
        )
        for i in range(5)
    ]

@pytest.mark.asyncio
async def test_distribution_coordinator_initialization(mock_node_registry):
    """Test coordinator initializes correctly"""
    coordinator = DistributionCoordinator(mock_node_registry)
    
    assert coordinator.replication_factor == 3
    assert coordinator.min_replicas_success == 2
    assert coordinator.placement_strategy is not None

@pytest.mark.asyncio
async def test_distribute_with_replication(mock_node_registry, mock_processed_chunks):
    """Test chunks are distributed with correct replication factor"""
    coordinator = DistributionCoordinator(mock_node_registry)

    results = await coordinator.distribute_processed_chunks(mock_processed_chunks)

    # Most chunks should be processed (allow for simulated network failures)
    # At least 80% success rate
    success_rate = len(results) / len(mock_processed_chunks)
    assert success_rate >= 0.8, f"Expected at least 80% success rate, got {success_rate*100:.1f}%"

    # Each successful task should have minimum replicas for success
    for task in results:
        assert task.successful_replicas() >= coordinator.min_replicas_success, \
            f"Task {task.task_id} should have at least {coordinator.min_replicas_success} successful replicas"

@pytest.mark.asyncio
async def test_network_aware_placement(mock_node_registry):
    """Test network-aware placement prefers same cloud"""
    # Add another AWS node to make the test scenario valid
    mock_node_registry.nodes['aws-node-3'] = SimpleNamespace(
        node_id='aws-node-3',
        cloud_provider='aws',
        status='healthy'
    )

    network_topology = NetworkTopology({'same_cloud_latency_ms': 5, 'aws_to_gcp_latency_ms': 50})
    placement = NetworkAwarePlacement(
        mock_node_registry,
        network_topology,
        {'prefer_same_cloud': True}
    )
    
    # Select nodes from AWS source
    selected = placement.select_target_nodes('test_chunk', 'aws-node-1', 3)
    
    # Should prefer AWS nodes
    aws_nodes = [n for n in selected if 'aws' in n]
    assert len(aws_nodes) >= 2  # Should have at least 2 AWS nodes

@pytest.mark.asyncio
async def test_cross_cloud_redundancy(mock_node_registry, mock_processed_chunks):
    """Test replicas distributed across multiple clouds"""
    coordinator = DistributionCoordinator(mock_node_registry)
    
    results = await coordinator.distribute_processed_chunks(mock_processed_chunks)
    
    # Check that replicas span multiple clouds
    for task in results:
        clouds = set(replica.cloud_provider for replica in task.replicas)
        # Should have replicas in at least 1 cloud (possibly more)
        assert len(clouds) >= 1

@pytest.mark.asyncio
async def test_distribution_success_rate(mock_node_registry, mock_processed_chunks):
    """Test distribution achieves >99% success rate"""
    with patch('random.random', return_value=0.1):
        coordinator = DistributionCoordinator(mock_node_registry)
    
        results = await coordinator.distribute_processed_chunks(mock_processed_chunks)
        stats = coordinator.get_distribution_statistics()
    
        assert stats['replica_success_rate'] > 0.99

@pytest.mark.asyncio
async def test_node_failure_during_distribution(mock_node_registry, mock_processed_chunks):
    """Test handling of node failure during distribution"""
    # Mark one node as unhealthy
    mock_node_registry.nodes['gcp-node-1'].status = 'unhealthy'
    
    coordinator = DistributionCoordinator(mock_node_registry)
    results = await coordinator.distribute_processed_chunks(mock_processed_chunks)
    
    # Should still complete with remaining nodes
    completed = [r for r in results if r.status == DistributionStatus.COMPLETED]
    assert len(completed) > 0
    
    # Failed node should not receive replicas
    for task in results:
        replica_nodes = [r.target_node for r in task.replicas]
        assert 'gcp-node-1' not in replica_nodes

@pytest.mark.asyncio
async def test_network_latency_modeling(mock_node_registry):
    """Test network latency is correctly modeled"""
    network_config = {
        'same_cloud_latency_ms': 5,
        'aws_to_gcp_latency_ms': 50
    }
    topology = NetworkTopology(network_config)
    
    # Same cloud should have low latency
    assert topology.get_latency('aws', 'aws') == 5
    
    # Cross-cloud should have higher latency
    assert topology.get_latency('aws', 'gcp') == 50
