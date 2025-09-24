from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio
import aiohttp
import numpy as np
import time

class NodeStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    UNKNOWN = "unknown"

@dataclass
class NodeInfo:
    node_id: str
    cloud_provider: str
    region: str
    instance_type: str
    public_ip: str
    roles: List[str]
    status: NodeStatus
    last_heartbeat: datetime
    private_ip: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

class MultiCloudNodeRegistry:
    def __init__(self):
        self.nodes: Dict[str, NodeInfo] = {}
        self.failure_log: List[Dict] = []
        self.latency_history: Dict[str, List[float]] = {}

    async def register_node(self, node_info: NodeInfo):
        """Register a new node in the cluster"""
        self.nodes[node_info.node_id] = node_info
        # In a real implementation, we would broadcast this to other nodes.
        print(f"Node {node_info.node_id} registered.")

    async def start_health_monitoring(self):
        """Start continuous health check loop"""
        while True:
            await self.perform_health_checks()
            await asyncio.sleep(5.0)  # 5-second intervals initially

    async def perform_health_checks(self):
        """Check health of all registered nodes"""
        tasks = []
        for node_id in list(self.nodes.keys()):
            node = self.nodes.get(node_id)
            if node:
                task = asyncio.create_task(
                    self.check_node_health(node)
                )
                tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            node_id = list(self.nodes.keys())[i]
            if isinstance(result, Exception):
                node = self.nodes.get(node_id)
                if node:
                    await self.handle_health_check_failure(node, result)

    async def check_node_health(self, node: NodeInfo):
        """Perform health check on individual node"""
        start_time = time.time()

        try:
            timeout = self.calculate_adaptive_timeout(node)
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"http://{node.public_ip}:8081/health",
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as response:
                    latency = (time.time() - start_time) * 1000  # ms

                    if response.status == 200:
                        node.status = NodeStatus.HEALTHY
                        node.last_heartbeat = datetime.now()
                        self.record_latency(node.cloud_provider, latency)
                    else:
                        raise aiohttp.ClientResponseError(
                            request_info=response.request_info,
                            history=response.history,
                            status=response.status,
                            message="Health check failed"
                        )

        except asyncio.TimeoutError:
            await self.handle_timeout_failure(node, (time.time() - start_time) * 1000)
        except aiohttp.ClientError as e:
            await self.handle_network_failure(node, e)
        except Exception as e:
            await self.handle_unexpected_failure(node, e)

    def calculate_adaptive_timeout(self, node: NodeInfo) -> float:
        """Calculate timeout based on historical latency - CRITICAL FOR SUCCESS"""
        history = self.get_latency_history(node.cloud_provider)
        if not history or len(history) < 10:
            return 5.0  # 5-second default

        p95_latency = np.percentile(history, 95)  # latency is in ms
        adaptive_timeout = max(1.0, (p95_latency * 3.0) / 1000)  # 3x P95 latency, min 1s

        return adaptive_timeout

    def get_latency_history(self, cloud_provider: str) -> List[float]:
        """Returns the latency history for a given cloud provider."""
        return self.latency_history.get(cloud_provider, [])

    def record_latency(self, cloud_provider: str, latency: float):
        """Records latency for a given cloud provider."""
        if cloud_provider not in self.latency_history:
            self.latency_history[cloud_provider] = []
        self.latency_history[cloud_provider].append(latency)
        # Keep the last 100 samples
        self.latency_history[cloud_provider] = self.latency_history[cloud_provider][-100:]

    async def get_available_nodes(self) -> List[NodeInfo]:
        """
        Returns a list of currently healthy and available nodes.
        """
        healthy_nodes = [
            node for node_id, node in self.nodes.items()
            if node.status == NodeStatus.HEALTHY
        ]
        return healthy_nodes

    async def handle_health_check_failure(self, node: NodeInfo, error: Exception):
        """Handles a failure in the health check."""
        if isinstance(error, asyncio.TimeoutError):
            await self.handle_timeout_failure(node, 0) # Duration is unknown here
        elif isinstance(error, aiohttp.ClientError):
            await self.handle_network_failure(node, error)
        else:
            await self.handle_unexpected_failure(node, error)

    async def handle_timeout_failure(self, node: NodeInfo, actual_duration: float):
        """Document and handle timeout failures"""
        node.status = NodeStatus.DEGRADED
        failure_detail = {
            'timestamp': datetime.now(),
            'failure_type': 'HEALTH_CHECK_TIMEOUT',
            'node_id': node.node_id,
            'cloud_provider': node.cloud_provider,
            'expected_timeout': self.calculate_adaptive_timeout(node),
            'actual_duration_ms': actual_duration,
            'sprint': 1,
            'hypothesis_impact': 'Challenges basic HTTP communication assumption'
        }
        self.failure_log.append(failure_detail)
        print(f"DOCUMENTED FAILURE: Timeout on {node.node_id} "
              f"({actual_duration:.2f}ms vs {failure_detail['expected_timeout'] * 1000:.2f}ms expected)")

    async def handle_network_failure(self, node: NodeInfo, error: aiohttp.ClientError):
        """Handle generic network failures."""
        node.status = NodeStatus.DEGRADED
        # Log failure for research
        failure_detail = {
            'timestamp': datetime.now(),
            'failure_type': 'NETWORK_ERROR',
            'node_id': node.node_id,
            'cloud_provider': node.cloud_provider,
            'error_details': str(error),
            'sprint': 1
        }
        self.failure_log.append(failure_detail)

    async def handle_unexpected_failure(self, node: NodeInfo, error: Exception):
        """Handle other unexpected failures."""
        node.status = NodeStatus.FAILED
        # Log failure for research
        failure_detail = {
            'timestamp': datetime.now(),
            'failure_type': 'UNEXPECTED_ERROR',
            'node_id': node.node_id,
            'cloud_provider': node.cloud_provider,
            'error_details': str(error),
            'sprint': 1
        }
        self.failure_log.append(failure_detail)
