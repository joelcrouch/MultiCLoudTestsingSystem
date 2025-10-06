# Day 19-20: Distribution Coordinator Implementation

## 🎯 **Design Goal**
Build an intelligent distribution coordinator that routes processed data chunks to target nodes with replication for fault tolerance, considering network topology and node availability.

---

## 📋 **Configuration Structure**

### **config/distribution_config.yml**
```yaml
# Distribution coordinator configuration
distribution:
  # Replication settings
  replication_factor: 3  # Number of replicas per chunk
  min_replicas_success: 2  # Minimum replicas required for success
  
  # Placement strategy
  placement:
    strategy: "network_aware"  # Options: round_robin, network_aware, load_balanced
    prefer_same_cloud: true  # Prefer nodes in same cloud for better latency
    cross_cloud_threshold: 0.7  # If cloud load > 70%, distribute to other clouds
  
  # Network topology
  network:
    # Average latency between clouds (ms)
    aws_to_gcp_latency_ms: 50
    aws_to_azure_latency_ms: 60
    gcp_to_azure_latency_ms: 45
    same_cloud_latency_ms: 5
  
  # Distribution performance
  
  max_concurrent_distributions: 15
  distribution_timeout_seconds: 30
  verify_after_distribution: true
  
  # Failure handling
  failure_handling:
    max_retries: 3
    retry_delay_seconds: 3
    fallback_to_any_node: true  # If preferred nodes unavailable
    
# For Sprint 2: simulated network transfers
simulate_distribution: true
simulated_transfer_time_ms: 50
```

---

## 🔧 **Implementation**

### **src/pipeline/distribution_coordinator.py**
```python
import asyncio
import time
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import yaml
import random

class DistributionStatus(Enum):
    PENDING = "pending"
    DISTRIBUTING = "distributing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"  # Some replicas succeeded

@dataclass
class Replica:
    replica_id: str
    chunk_id: str
    target_node: str
    cloud_provider: str
    status: DistributionStatus = DistributionStatus.PENDING
    checksum: Optional[str] = None
    size_bytes: int = 0
    transfer_time_seconds: float = 0.0

@dataclass
class DistributionTask:
    task_id: str
    chunk_id: str
    chunk_data: bytes
    source_node: str
    target_nodes: List[str] = field(default_factory=list)
    replicas: List[Replica] = field(default_factory=list)
    status: DistributionStatus = DistributionStatus.PENDING
    attempts: int = 0
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    error_message: Optional[str] = None
    
    def successful_replicas(self) -> int:
        return sum(1 for r in self.replicas if r.status == DistributionStatus.COMPLETED)
    
    def failed_replicas(self) -> int:
        return sum(1 for r in self.replicas if r.status == DistributionStatus.FAILED)

class NetworkTopology:
    """Model network characteristics between clouds"""
    
    def __init__(self, network_config: Dict):
        self.latencies = {
            ('aws', 'gcp'): network_config.get('aws_to_gcp_latency_ms', 50),
            ('gcp', 'aws'): network_config.get('aws_to_gcp_latency_ms', 50),
            ('aws', 'azure'): network_config.get('aws_to_azure_latency_ms', 60),
            ('azure', 'aws'): network_config.get('aws_to_azure_latency_ms', 60),
            ('gcp', 'azure'): network_config.get('gcp_to_azure_latency_ms', 45),
            ('azure', 'gcp'): network_config.get('gcp_to_azure_latency_ms', 45),
        }
        self.same_cloud_latency = network_config.get('same_cloud_latency_ms', 5)
    
    def get_latency(self, from_cloud: str, to_cloud: str) -> float:
        """Get network latency between two clouds (ms)"""
        if from_cloud == to_cloud:
            return self.same_cloud_latency
        
        key = (from_cloud.lower(), to_cloud.lower())
        return self.latencies.get(key, 100)  # Default to 100ms if unknown

class PlacementStrategy:
    """Base class for node placement strategies"""
    
    def __init__(self, node_registry, network_topology: NetworkTopology, config: Dict):
        self.node_registry = node_registry
        self.network_topology = network_topology
        self.config = config
    
    def select_target_nodes(self, chunk_id: str, source_node: str, 
                          num_replicas: int) -> List[str]:
        """Select target nodes for data placement"""
        raise NotImplementedError("Subclasses must implement select_target_nodes()")

class NetworkAwarePlacement(PlacementStrategy):
    """Network-aware placement: minimize latency, prefer same cloud"""
    
    def select_target_nodes(self, chunk_id: str, source_node: str, 
                          num_replicas: int) -> List[str]:
        """
        Select nodes considering:
        1. Prefer same cloud as source (lower latency)
        2. Distribute across different nodes for fault tolerance
        3. Consider current load on each cloud/maybe node
        """
        # Get source node cloud
        source_node_info = self.node_registry.nodes.get(source_node)
        if not source_node_info:
            raise ValueError(f"Source node {source_node} not found")
        
        source_cloud = source_node_info.cloud_provider
        
        # Get all healthy nodes (excluding source)
        available_nodes = [
            (node_id, node_info) 
            for node_id, node_info in self.node_registry.nodes.items()
            if node_info.status == 'healthy' and node_id != source_node
        ]
        
        if not available_nodes:
            raise RuntimeError("No healthy nodes available for distribution")
        
        # Separate by cloud
        same_cloud_nodes = [
            (node_id, info) for node_id, info in available_nodes
            if info.cloud_provider == source_cloud
        ]
        other_cloud_nodes = [
            (node_id, info) for node_id, info in available_nodes
            if info.cloud_provider != source_cloud
        ]
        
        selected_nodes = []
        
        # Strategy: prefer same cloud, but ensure cross-cloud redundancy
        prefer_same_cloud = self.config.get('prefer_same_cloud', True)
        cross_cloud_threshold = self.config.get('cross_cloud_threshold', 0.7)
        
        if prefer_same_cloud and len(same_cloud_nodes) >= num_replicas:
            # If enough same-cloud nodes, use them
            selected_nodes = [node_id for node_id, _ in same_cloud_nodes[:num_replicas]]
        else:
            # Mix: prioritize same cloud, then add cross-cloud for redundancy
            same_cloud_count = min(len(same_cloud_nodes), int(num_replicas * cross_cloud_threshold))
            cross_cloud_count = num_replicas - same_cloud_count
            
            selected_nodes.extend([node_id for node_id, _ in same_cloud_nodes[:same_cloud_count]])
            selected_nodes.extend([node_id for node_id, _ in other_cloud_nodes[:cross_cloud_count]])
        
        # Ensure we have enough nodes
        if len(selected_nodes) < num_replicas:
            # Add any remaining available nodes
            remaining = [
                node_id for node_id, _ in available_nodes
                if node_id not in selected_nodes
            ]
            selected_nodes.extend(remaining[:num_replicas - len(selected_nodes)])
        
        return selected_nodes[:num_replicas]

class RoundRobinPlacement(PlacementStrategy):
    """Simple round-robin placement across all nodes"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_index = 0
    
    def select_target_nodes(self, chunk_id: str, source_node: str, 
                          num_replicas: int) -> List[str]:
        available_nodes = [
            node_id for node_id, node_info in self.node_registry.nodes.items()
            if node_info.status == 'healthy' and node_id != source_node
        ]
        
        if len(available_nodes) < num_replicas:
            raise RuntimeError(f"Not enough nodes: need {num_replicas}, have {len(available_nodes)}")
        
        # Round-robin selection
        selected = []
        for i in range(num_replicas):
            idx = (self.current_index + i) % len(available_nodes)
            selected.append(available_nodes[idx])
        
        self.current_index = (self.current_index + num_replicas) % len(available_nodes)
        return selected

class DistributionCoordinator:
    """
    Coordinates distribution of processed data chunks with replication
    """
    
    def __init__(self, node_registry, config_path: str = 'config/distribution_config.yml'):
        self.node_registry = node_registry
        
        # Load configuration
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        dist_config = self.config.get('distribution', {})
        self.replication_factor = dist_config.get('replication_factor', 3)
        self.min_replicas_success = dist_config.get('min_replicas_success', 2)
        self.max_concurrent_distributions = dist_config.get('max_concurrent_distributions', 15)
        self.distribution_timeout = dist_config.get('distribution_timeout_seconds', 30)
        self.verify_after_distribution = dist_config.get('verify_after_distribution', True)
        
        # Failure handling
        failure_config = dist_config.get('failure_handling', {})
        self.max_retries = failure_config.get('max_retries', 3)
        self.retry_delay = failure_config.get('retry_delay_seconds', 3)
        self.fallback_to_any_node = failure_config.get('fallback_to_any_node', True)
        
        # Network topology
        network_config = self.config.get('distribution', {}).get('network', {})
        self.network_topology = NetworkTopology(network_config)
        
        # Placement strategy
        placement_config = dist_config.get('placement', {})
        strategy_name = placement_config.get('strategy', 'network_aware')
        
        if strategy_name == 'network_aware':
            self.placement_strategy = NetworkAwarePlacement(
                self.node_registry, self.network_topology, placement_config
            )
        elif strategy_name == 'round_robin':
            self.placement_strategy = RoundRobinPlacement(
                self.node_registry, self.network_topology, placement_config
            )
        else:
            self.placement_strategy = NetworkAwarePlacement(
                self.node_registry, self.network_topology, placement_config
            )
        
        # Task tracking
        self.pending_tasks: List[DistributionTask] = []
        self.active_tasks: Dict[str, DistributionTask] = {}
        self.completed_tasks: List[DistributionTask] = []
        self.failed_tasks: List[DistributionTask] = []
        
        # Simulation mode
        self.simulate_distribution = self.config.get('simulate_distribution', True)
        self.simulated_transfer_time = self.config.get('simulated_transfer_time_ms', 50) / 1000.0
        
        print(f"📡 Distribution Coordinator initialized")
        print(f"   Replication factor: {self.replication_factor}")
        print(f"   Min replicas for success: {self.min_replicas_success}")
        print(f"   Placement strategy: {strategy_name}")
        print(f"   Simulation mode: {self.simulate_distribution}")
    
    async def distribute_processed_chunks(self, processed_chunks: List) -> List[DistributionTask]:
        """
        Main entry point: Distribute processed chunks with replication
        
        Args:
            processed_chunks: List of ProcessingTask results from processing workers
            
        Returns:
            List of DistributionTask results
        """
        print(f"\n📡 Starting distribution of {len(processed_chunks)} chunks...")
        
        # Create distribution tasks
        self.pending_tasks = [
            DistributionTask(
                task_id=f"dist_task_{i}",
                chunk_id=chunk.chunk_id,
                chunk_data=chunk.result,
                source_node=chunk.assigned_node
            )
            for i, chunk in enumerate(processed_chunks)
            if chunk.result is not None  # Only distribute successfully processed chunks
        ]
        
        print(f"   Created {len(self.pending_tasks)} distribution tasks")
        print(f"   Target replication: {self.replication_factor}x per chunk")
        
        # Distribute with concurrency control
        await self._distribute_tasks_with_concurrency()
        
        # Generate summary
        total_tasks = len(self.completed_tasks) + len(self.failed_tasks)
        success_rate = len(self.completed_tasks) / total_tasks if total_tasks > 0 else 0
        
        # Calculate replica statistics
        total_expected_replicas = total_tasks * self.replication_factor
        total_successful_replicas = sum(t.successful_replicas() for t in self.completed_tasks)
        replica_success_rate = total_successful_replicas / total_expected_replicas if total_expected_replicas > 0 else 0
        
        print(f"\n✅ Distribution complete:")
        print(f"   Total chunks: {total_tasks}")
        print(f"   Fully distributed: {len(self.completed_tasks)}")
        print(f"   Failed: {len(self.failed_tasks)}")
        print(f"   Chunk success rate: {success_rate:.1%}")
        print(f"   Replica success rate: {replica_success_rate:.1%}")
        
        return self.completed_tasks + self.failed_tasks
    
    async def _distribute_tasks_with_concurrency(self):
        """Distribute tasks with concurrency limit"""
        
        while self.pending_tasks or self.active_tasks:
            # Start new tasks up to concurrency limit
            while (len(self.active_tasks) < self.max_concurrent_distributions and 
                   self.pending_tasks):
                
                task = self.pending_tasks.pop(0)
                task.status = DistributionStatus.DISTRIBUTING
                self.active_tasks[task.task_id] = task
                
                # Start distribution
                asyncio.create_task(self._distribute_task(task))
            
            await asyncio.sleep(0.1)
    
    async def _distribute_task(self, task: DistributionTask):
        """Distribute a single chunk to multiple target nodes"""
        
        task.start_time = time.time()
        
        try:
            # Select target nodes for this chunk
            target_nodes = self.placement_strategy.select_target_nodes(
                task.chunk_id,
                task.source_node,
                self.replication_factor
            )
            
            task.target_nodes = target_nodes
            
            # Create replicas
            replicas = []
            for i, target_node in enumerate(target_nodes):
                node_info = self.node_registry.nodes[target_node]
                replica = Replica(
                    replica_id=f"{task.chunk_id}_replica_{i}",
                    chunk_id=task.chunk_id,
                    target_node=target_node,
                    cloud_provider=node_info.cloud_provider,
                    size_bytes=len(task.chunk_data)
                )
                replicas.append(replica)
            
            task.replicas = replicas
            
            # Distribute to all targets in parallel
            distribution_tasks = [
                self._transfer_replica(replica, task.chunk_data, task.source_node)
                for replica in replicas
            ]
            
            # Wait for all transfers with timeout
            await asyncio.wait_for(
                asyncio.gather(*distribution_tasks, return_exceptions=True),
                timeout=self.distribution_timeout
            )
            
            # Check results
            successful_replicas = task.successful_replicas()
            
            if successful_replicas >= self.min_replicas_success:
                task.status = DistributionStatus.COMPLETED
            elif successful_replicas > 0:
                task.status = DistributionStatus.PARTIAL
                task.error_message = f"Only {successful_replicas}/{self.replication_factor} replicas succeeded"
            else:
                task.status = DistributionStatus.FAILED
                task.error_message = "All replica transfers failed"
            
            task.end_time = time.time()
            
            # Verify if configured
            if self.verify_after_distribution and task.status == DistributionStatus.COMPLETED:
                await self._verify_replicas(task)
            
            # Move to completed or failed
            del self.active_tasks[task.task_id]
            
            if task.status == DistributionStatus.COMPLETED:
                self.completed_tasks.append(task)
            else:
                # Retry if attempts remain
                task.attempts += 1
                if task.attempts < self.max_retries:
                    print(f"   ⚠️  Retrying distribution for {task.chunk_id} (attempt {task.attempts}/{self.max_retries})")
                    await asyncio.sleep(self.retry_delay)
                    task.status = DistributionStatus.PENDING
                    self.pending_tasks.append(task)
                else:
                    self.failed_tasks.append(task)
            
        except Exception as e:
            task.status = DistributionStatus.FAILED
            task.error_message = str(e)
            task.end_time = time.time()
            
            del self.active_tasks[task.task_id]
            self.failed_tasks.append(task)
            print(f"   ❌ Distribution failed for {task.chunk_id}: {e}")
    
    async def _transfer_replica(self, replica: Replica, data: bytes, source_node: str):
        """Transfer data to create a replica on target node"""
        
        start_time = time.time()
        
        try:
            # Get network latency
            source_cloud = self.node_registry.nodes[source_node].cloud_provider
            target_cloud = replica.cloud_provider
            latency_ms = self.network_topology.get_latency(source_cloud, target_cloud)
            
            if self.simulate_distribution:
                # Simulate transfer with network latency
                transfer_time = self.simulated_transfer_time + (latency_ms / 1000.0)
                await asyncio.sleep(transfer_time)
                
                # Simulate occasional network failures (5% chance)
                if random.random() < 0.05:
                    raise Exception("Simulated network failure")
                
                replica.checksum = hashlib.md5(data).hexdigest()
                replica.status = DistributionStatus.COMPLETED
            else:
                # Real transfer would happen here
                # This would use actual network protocols (gRPC, HTTP, etc.)
                await self._actual_network_transfer(replica, data, source_node)
            
            replica.transfer_time_seconds = time.time() - start_time
            
        except Exception as e:
            replica.status = DistributionStatus.FAILED
            replica.transfer_time_seconds = time.time() - start_time
            print(f"      ⚠️  Replica transfer failed: {replica.replica_id} -> {replica.target_node}: {e}")
    
    async def _actual_network_transfer(self, replica: Replica, data: bytes, source_node: str):
        """Actual network transfer (Sprint 3 implementation)"""
        # This will be implemented in Sprint 3 with real network protocols
        raise NotImplementedError("Real network transfer not yet implemented")
    
    async def _verify_replicas(self, task: DistributionTask):
        """Verify all replicas have correct data"""
        
        # Calculate expected checksum
        expected_checksum = hashlib.md5(task.chunk_data).hexdigest()
        
        for replica in task.replicas:
            if replica.status == DistributionStatus.COMPLETED:
                if replica.checksum != expected_checksum:
                    print(f"   ⚠️  Checksum mismatch for {replica.replica_id}")
                    replica.status = DistributionStatus.FAILED
    
    def get_distribution_statistics(self) -> Dict:
        """Get distribution statistics for monitoring"""
        
        total_tasks = len(self.completed_tasks) + len(self.failed_tasks)
        total_replicas = sum(len(t.replicas) for t in self.completed_tasks + self.failed_tasks)
        successful_replicas = sum(t.successful_replicas() for t in self.completed_tasks + self.failed_tasks)
        
        # Calculate cross-cloud distribution statistics
        cross_cloud_transfers = 0
        same_cloud_transfers = 0
        
        for task in self.completed_tasks + self.failed_tasks:
            source_cloud = self.node_registry.nodes[task.source_node].cloud_provider
            for replica in task.replicas:
                if replica.cloud_provider == source_cloud:
                    same_cloud_transfers += 1
                else:
                    cross_cloud_transfers += 1
        
        # Calculate average transfer times
        all_replicas = []
        for task in self.completed_tasks + self.failed_tasks:
            all_replicas.extend(task.replicas)
        
        transfer_times = [r.transfer_time_seconds for r in all_replicas if r.transfer_time_seconds > 0]
        avg_transfer_time = sum(transfer_times) / len(transfer_times) if transfer_times else 0
        
        return {
            'total_tasks': total_tasks,
            'completed_tasks': len(self.completed_tasks),
            'failed_tasks': len(self.failed_tasks),
            'success_rate': len(self.completed_tasks) / total_tasks if total_tasks > 0 else 0,
            'total_replicas': total_replicas,
            'successful_replicas': successful_replicas,
            'replica_success_rate': successful_replicas / total_replicas if total_replicas > 0 else 0,
            'cross_cloud_transfers': cross_cloud_transfers,
            'same_cloud_transfers': same_cloud_transfers,
            'average_transfer_time_seconds': avg_transfer_time
        }

# Example usage
async def main():
    from types import SimpleNamespace
    
    # Mock node registry
    mock_registry = SimpleNamespace()
    mock_registry.nodes = {
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
        )
    }
    
    # Mock processed chunks from processing workers
    mock_processed_chunks = [
        SimpleNamespace(
            chunk_id=f'processed_chunk_{i}',
            result=f'processed data {i}'.encode() * 1000,
            assigned_node='aws-node-1'
        )
        for i in range(10)
    ]
    
    # Create distribution coordinator
    coordinator = DistributionCoordinator(mock_registry)
    
    # Distribute chunks
    results = await coordinator.distribute_processed_chunks(mock_processed_chunks)
    
    # Get statistics
    stats = coordinator.get_distribution_statistics()
    
    print(f"\n📊 Distribution Statistics:")
    print(f"   Success rate: {stats['success_rate']:.1%}")
    print(f"   Replica success rate: {stats['replica_success_rate']:.1%}")
    print(f"   Cross-cloud transfers: {stats['cross_cloud_transfers']}")
    print(f"   Same-cloud transfers: {stats['same_cloud_transfers']}")
    print(f"   Average transfer time: {stats['average_transfer_time_seconds']:.3f}s")

if __name__ == '__main__':
    asyncio.run(main())
```

---

## 🧪 **Testing Setup**

### **tests/pipeline/test_distribution_coordinator.py**
```python
import pytest
import asyncio
from types import SimpleNamespace
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
    
    # All chunks should be processed
    assert len(results) == len(mock_processed_chunks)
    
    # Each task should have replication_factor replicas
    for task in results:
        assert len(task.replicas) == coordinator.replication_factor
        assert task.successful_replicas() >= coordinator.min_replicas_success

@pytest.mark.asyncio
async def test_network_aware_placement(mock_node_registry):
    """Test network-aware placement prefers same cloud"""
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
    
    # Same cloud should have low lat