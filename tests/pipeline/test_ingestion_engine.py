import unittest
import asyncio
import os
import subprocess # NEW IMPORT
import time # NEW IMPORT
import json # NEW IMPORT
from datetime import datetime # NEW IMPORT
from unittest.mock import AsyncMock, patch

from src.pipeline.ingestion_engine import DataIngestionEngine
from src.coordination.node_registry import MultiCloudNodeRegistry, NodeInfo, NodeStatus
from src.config.multi_cloud_config import SystemConfig, CloudProviderConfig

class TestDataIngestionEngine(unittest.TestCase):
    def setUp(self):
        # Setup a mock node registry and config for testing
        self.mock_registry = AsyncMock(spec=MultiCloudNodeRegistry)
        self.mock_config = AsyncMock(spec=SystemConfig)

        # Configure mock_config attributes
        self.mock_config.data_sources = ["s3://test-bucket/data/", "file:///tmp/test_data/"]
        self.mock_config.chunk_size_mb = 1
        self.mock_config.ingestion_retry_attempts = 3
        self.mock_config.node_id = "test-local-node"

        # Configure mock_registry methods
        self.mock_registry.get_available_nodes.return_value = [] # Default empty
        self.mock_registry.calculate_adaptive_timeout.return_value = 5.0 # NEW: Return a fixed timeout

        self.engine = DataIngestionEngine(self.mock_registry, self.mock_config)
        self.receiver_output_file = "/tmp/test_receiver_output.jsonl" # NEW

    def tearDown(self):
        if os.path.exists(self.receiver_output_file):
            os.remove(self.receiver_output_file)

    def test_chunk_large_file_success(self):
        async def _test():
            # Create a dummy file for testing
            test_file_path = "/tmp/test_large_file.bin"
            with open(test_file_path, "wb") as f:
                f.write(os.urandom(5 * 1024 * 1024)) # 5MB file

            chunks = await self.engine.chunk_large_file(test_file_path, 1) # 1MB chunks
            self.assertEqual(len(chunks), 5)
            self.assertEqual(len(chunks[0]), 1 * 1024 * 1024)

            os.remove(test_file_path)
        asyncio.run(_test())

    def test_chunk_large_file_not_found(self):
        async def _test():
            chunks = await self.engine.chunk_large_file("/tmp/non_existent_file.bin", 1)
            self.assertEqual(len(chunks), 0)
        asyncio.run(_test())

    def test_ingest_batch_local_integration(self):
        async def _test():
            # Ensure receiver output file is clean
            if os.path.exists(self.receiver_output_file):
                os.remove(self.receiver_output_file)

            # Start receiver in a subprocess
            env = os.environ.copy()
            env["RECEIVER_OUTPUT_FILE"] = self.receiver_output_file
            receiver_process = subprocess.Popen(
                ["python3", "-m", "src.receiver"],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            # Give receiver time to start up
            time.sleep(2)

            try:
                # Configure mock registry for the engine
                mock_node_aws = NodeInfo(
                    node_id="mock-aws-node-1",
                    cloud_provider="aws",
                    region="us-east-1",
                    instance_type="t4g.nano",
                    public_ip="127.0.0.1",
                    roles=["worker"],
                    status=NodeStatus.HEALTHY,
                    last_heartbeat=datetime.now()
                )
                self.mock_registry.get_available_nodes.return_value = [mock_node_aws]
                self.mock_registry.nodes = {node.node_id: node for node in self.mock_registry.get_available_nodes.return_value}

                # Create a dummy file for ingestion
                test_file_path = "/tmp/test_ingest_batch_file.bin"
                file_size_mb = 2
                with open(test_file_path, "wb") as f:
                    f.write(os.urandom(file_size_mb * 1024 * 1024)) # 2MB file

                batch_config = {"file_path": test_file_path}
                await self.engine.ingest_batch(batch_config)

                os.remove(test_file_path)

                # Read received data from the receiver's output file
                received_chunks = []
                with open(self.receiver_output_file, "r") as f:
                    for line in f:
                        received_chunks.append(json.loads(line))

                self.assertEqual(len(received_chunks), file_size_mb) # Expect 2 chunks
                for chunk_info in received_chunks:
                    self.assertEqual(chunk_info["sender_id"], self.mock_config.node_id)
                    self.assertEqual(chunk_info["message_type"], "data_chunk")
                    self.assertEqual(chunk_info["chunk_data_len"], self.mock_config.chunk_size_mb * 1024 * 1024)

            finally:
                receiver_process.terminate()
                receiver_process.wait()
        asyncio.run(_test())
