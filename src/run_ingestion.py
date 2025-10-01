import asyncio
import os
from unittest.mock import AsyncMock # For local testing without real nodes

from src.config.multi_cloud_config import ConfigurationManager, SystemConfig
from src.coordination.node_registry import MultiCloudNodeRegistry, NodeInfo, NodeStatus
from src.pipeline.ingestion_engine import DataIngestionEngine

async def main():
    # 1. Load Configuration
    config_manager = ConfigurationManager(config_path='config/multi_cloud.yml')
    config = config_manager.config

    # 2. Instantiate Node Registry (Mocked for local testing)
    # In a real scenario, this would be a live registry of actual nodes
    mock_registry = AsyncMock(spec=MultiCloudNodeRegistry)

    # Add some mock healthy nodes for distribution testing
    mock_node_aws = NodeInfo(
        node_id="mock-aws-node-1",
        cloud_provider="aws",
        region="us-east-1",
        instance_type="t4g.nano",
        public_ip="127.0.0.1", # Localhost for testing
        roles=["worker"],
        status=NodeStatus.HEALTHY,
        last_heartbeat=datetime.now()
    )
    mock_node_gcp = NodeInfo(
        node_id="mock-gcp-node-1",
        cloud_provider="gcp",
        region="us-central1",
        instance_type="e2-micro",
        public_ip="127.0.0.1", # Localhost for testing
        roles=["worker"],
        status=NodeStatus.HEALTHY,
        last_heartbeat=datetime.now()
    )
    # 2. Instantiate Node Registry (REAL instance for local testing)
    real_registry = MultiCloudNodeRegistry() # Use a real registry

    # Add some mock healthy nodes for distribution testing
    mock_node_aws = NodeInfo(
        node_id="mock-aws-node-1",
        cloud_provider="aws",
        region="us-east-1",
        instance_type="t4g.nano",
        public_ip="127.0.0.1", # Localhost for testing
        roles=["worker"],
        status=NodeStatus.HEALTHY,
        last_heartbeat=datetime.now()
    )
    mock_node_gcp = NodeInfo(
        node_id="mock-gcp-node-1",
        cloud_provider="gcp",
        region="us-central1",
        instance_type="e2-micro",
        public_ip="127.0.0.1", # Localhost for testing
        roles=["worker"],
        status=NodeStatus.HEALTHY,
        last_heartbeat=datetime.now()
    )
    await real_registry.register_node(mock_node_aws) # Register mock nodes
    await real_registry.register_node(mock_node_gcp) # Register mock nodes

    # 3. Instantiate Data Ingestion Engine
    engine = DataIngestionEngine(node_registry=real_registry, config=config) # Pass real registry

    # 4. Create a dummy file for ingestion
    test_file_path = "/tmp/dummy_data_for_ingestion.bin"
    file_size_mb = 5
    with open(test_file_path, "wb") as f:
        f.write(os.urandom(file_size_mb * 1024 * 1024)) # 5MB file

    print(f"Created dummy file: {test_file_path} ({file_size_mb}MB)")

    # 5. Run the ingestion batch
    batch_config = {"file_path": test_file_path}
    await engine.ingest_batch(batch_config)

    # Clean up dummy file
    os.remove(test_file_path)
    print(f"Cleaned up dummy file: {test_file_path}")

if __name__ == "__main__":
    from datetime import datetime # Import here to avoid circular dependency with NodeInfo
    asyncio.run(main())
