from dataclasses import dataclass
from typing import Any, Dict, Optional
import json
import asyncio
import aiohttp
from datetime import datetime
import time

from src.coordination.node_registry import MultiCloudNodeRegistry, NodeInfo

@dataclass
class Message:
    sender_id: str
    recipient_id: str
    message_type: str
    payload: Dict[str, Any]
    timestamp: datetime
    message_id: str

class CrossCloudCommunicationProtocol:
    def __init__(self, node_id: str, registry: MultiCloudNodeRegistry):
        self.node_id = node_id
        self.registry = registry
        self.message_handlers = {}
        self.failure_log = []

    async def send_message(self, target_node_id: str, message_type: str, payload: Dict):
        """Send message to another node with failure tracking"""
        target_node = self.registry.nodes.get(target_node_id)
        if not target_node:
            raise ValueError(f"Unknown target node: {target_node_id}")

        message = Message(
            sender_id=self.node_id,
            recipient_id=target_node_id,
            message_type=message_type,
            payload=payload,
            timestamp=datetime.now(),
            message_id=f"{self.node_id}_{int(time.time() * 1000)}"
        )

        return await self._send_http_message(target_node, message)

    async def _send_http_message(self, target_node: NodeInfo, message: Message):
        """Send HTTP message with comprehensive failure tracking"""
        start_time = time.time()

        try:
            timeout_duration = self.registry.calculate_adaptive_timeout(target_node)
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"http://{target_node.public_ip}:8080/message",
                    json=message.__dict__,
                    timeout=aiohttp.ClientTimeout(total=timeout_duration)
                ) as response:

                    duration = time.time() - start_time

                    if response.status == 200:
                        return True
                    elif response.status == 429:  # Rate limited
                        await self.handle_rate_limit_response(target_node, response)
                        return False
                    else:
                        await self.handle_http_error(target_node, response.status, duration)
                        return False

        except asyncio.TimeoutError:
            await self.handle_communication_timeout(target_node, time.time() - start_time)
            return False
        except Exception as e:
            await self.handle_communication_error(target_node, e)
            return False

    async def handle_rate_limit_response(self, target_node: NodeInfo, response):
        """Handle API rate limiting - CRITICAL FAILURE WE EXPECT"""
        retry_after = response.headers.get('Retry-After', '60')

        failure_detail = {
            'timestamp': datetime.now(),
            'failure_type': 'API_RATE_LIMIT_HIT',
            'target_node': target_node.node_id,
            'cloud_provider': target_node.cloud_provider,
            'retry_after': retry_after,
            'sprint': 1,
            'root_cause': 'Aggressive health checking or message sending exceeded API limits',
            'hypothesis_impact': 'Invalidates assumption about unlimited API access'
        }
        self.failure_log.append(failure_detail)
        print(f"DOCUMENTED FAILURE: Rate limit hit on {target_node.cloud_provider}")

    async def handle_http_error(self, target_node: NodeInfo, status: int, duration: float):
        # Log HTTP errors
        pass

    async def handle_communication_timeout(self, target_node: NodeInfo, duration: float):
        # Log communication timeouts
        pass

    async def handle_communication_error(self, target_node: NodeInfo, error: Exception):
        # Log other communication errors
        pass
