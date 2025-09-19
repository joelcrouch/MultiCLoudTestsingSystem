import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio
from datetime import datetime

from src.coordination.node_registry import MultiCloudNodeRegistry, NodeInfo, NodeStatus

class TestMultiCloudNodeRegistry(unittest.TestCase):

    def setUp(self):
        self.registry = MultiCloudNodeRegistry()
        self.loop = asyncio.get_event_loop()

    def test_initialization(self):
        self.assertEqual(self.registry.nodes, {})
        self.assertEqual(self.registry.failure_log, [])
        self.assertEqual(self.registry.latency_history, {})

    def test_register_node(self):
        node_info = NodeInfo(
            node_id='test-node-1',
            cloud_provider='aws',
            region='us-east-1',
            instance_type='t2.micro',
            public_ip='1.2.3.4',
            roles=['worker'],
            status=NodeStatus.HEALTHY,
            last_heartbeat=datetime.now()
        )
        self.loop.run_until_complete(self.registry.register_node(node_info))
        self.assertIn('test-node-1', self.registry.nodes)
        self.assertEqual(self.registry.nodes['test-node-1'], node_info)

    @patch('aiohttp.ClientSession.get')
    def test_check_node_health_success(self, mock_get):
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_get.return_value.__aenter__.return_value = mock_response

        node_info = NodeInfo(
            node_id='test-node-1',
            cloud_provider='aws',
            region='us-east-1',
            instance_type='t2.micro',
            public_ip='1.2.3.4',
            roles=['worker'],
            status=NodeStatus.UNKNOWN,
            last_heartbeat=datetime.now()
        )

        self.loop.run_until_complete(self.registry.check_node_health(node_info))

        self.assertEqual(node_info.status, NodeStatus.HEALTHY)
        self.assertGreater(len(self.registry.latency_history['aws']), 0)

    @patch('aiohttp.ClientSession.get', side_effect=asyncio.TimeoutError)
    def test_check_node_health_timeout(self, mock_get):
        node_info = NodeInfo(
            node_id='test-node-1',
            cloud_provider='aws',
            region='us-east-1',
            instance_type='t2.micro',
            public_ip='1.2.3.4',
            roles=['worker'],
            status=NodeStatus.HEALTHY,
            last_heartbeat=datetime.now()
        )

        self.loop.run_until_complete(self.registry.check_node_health(node_info))

        self.assertEqual(node_info.status, NodeStatus.DEGRADED)
        self.assertEqual(len(self.registry.failure_log), 1)
        self.assertEqual(self.registry.failure_log[0]['failure_type'], 'HEALTH_CHECK_TIMEOUT')

    def test_calculate_adaptive_timeout_default(self):
        node_info = NodeInfo(
            node_id='test-node-1',
            cloud_provider='aws',
            region='us-east-1',
            instance_type='t2.micro',
            public_ip='1.2.3.4',
            roles=['worker'],
            status=NodeStatus.UNKNOWN,
            last_heartbeat=datetime.now()
        )
        timeout = self.registry.calculate_adaptive_timeout(node_info)
        self.assertEqual(timeout, 5.0)

    def test_calculate_adaptive_timeout_with_history(self):
        node_info = NodeInfo(
            node_id='test-node-1',
            cloud_provider='aws',
            region='us-east-1',
            instance_type='t2.micro',
            public_ip='1.2.3.4',
            roles=['worker'],
            status=NodeStatus.UNKNOWN,
            last_heartbeat=datetime.now()
        )
        self.registry.latency_history['aws'] = [100, 110, 105, 115, 120, 95, 90, 130, 125, 118]
        timeout = self.registry.calculate_adaptive_timeout(node_info)
        # With the given history, p95 is around 128.75
        # (128.75 * 3) / 1000 = 0.38625. max(1.0, 0.38625) = 1.0
        # Let's adjust the history to get a value > 1
        self.registry.latency_history['aws'] = [400, 410, 405, 415, 420, 395, 390, 430, 425, 418]
        # p95 is around 428.75. (428.75 * 3) / 1000 = 1.28625
        timeout = self.registry.calculate_adaptive_timeout(node_info)
        self.assertAlmostEqual(timeout, 1.28625, places=2)

if __name__ == '__main__':
    unittest.main()
