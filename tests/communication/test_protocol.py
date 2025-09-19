import unittest
from unittest.mock import patch, AsyncMock
import asyncio
from datetime import datetime

from src.communication.protocol import CrossCloudCommunicationProtocol
from src.coordination.node_registry import MultiCloudNodeRegistry, NodeInfo, NodeStatus

class TestCrossCloudCommunicationProtocol(unittest.TestCase):

    def setUp(self):
        self.registry = MultiCloudNodeRegistry()
        self.protocol = CrossCloudCommunicationProtocol('test-sender', self.registry)
        self.target_node = NodeInfo(
            node_id='test-target',
            cloud_provider='aws',
            region='us-east-1',
            instance_type='t2.micro',
            public_ip='4.3.2.1',
            roles=['worker'],
            status=NodeStatus.HEALTHY,
            last_heartbeat=datetime.now()
        )
        asyncio.run(self.registry.register_node(self.target_node))

    @patch('aiohttp.ClientSession.post')
    def test_send_message_success(self, mock_post):
        async def run_test():
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_post.return_value.__aenter__.return_value = mock_response

            result = await self.protocol.send_message('test-target', 'test_message', {'data': 'test'})

            self.assertTrue(result)
            mock_post.assert_called_once()
        asyncio.run(run_test())

    @patch('aiohttp.ClientSession.post', side_effect=asyncio.TimeoutError)
    def test_send_message_timeout(self, mock_post):
        async def run_test():
            with patch.object(self.protocol, 'handle_communication_timeout', new_callable=AsyncMock) as mock_handle_timeout:
                result = await self.protocol.send_message('test-target', 'test_message', {'data': 'test'})

                self.assertFalse(result)
                mock_post.assert_called_once()
                mock_handle_timeout.assert_called_once()
        asyncio.run(run_test())

    @patch('aiohttp.ClientSession.post')
    def test_send_message_rate_limit(self, mock_post):
        async def run_test():
            mock_response = AsyncMock()
            mock_response.status = 429
            mock_response.headers = {'Retry-After': '60'}
            mock_post.return_value.__aenter__.return_value = mock_response

            with patch.object(self.protocol, 'handle_rate_limit_response', new_callable=AsyncMock) as mock_handle_rate_limit:
                result = await self.protocol.send_message('test-target', 'test_message', {'data': 'test'})

                self.assertFalse(result)
                mock_post.assert_called_once()
                mock_handle_rate_limit.assert_called_once()
        asyncio.run(run_test())

    def test_send_message_unknown_node(self):
        async def run_test():
            with self.assertRaises(ValueError):
                await self.protocol.send_message('unknown-node', 'test_message', {'data': 'test'})
        asyncio.run(run_test())

if __name__ == '__main__':
    unittest.main()