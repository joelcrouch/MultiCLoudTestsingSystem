import asyncio
from typing import List, Dict, Any
from src.coordination.node_registry import MultiCloudNodeRegistry, NodeInfo
from src.config.multi_cloud_config import SystemConfig
from src.communication.protocol import CrossCloudCommunicationProtocol # NEW IMPORT

class DataIngestionEngine:
    """
    Manages data ingestion, chunking, and distribution across multi-cloud nodes.
    """
    def __init__(self, node_registry: MultiCloudNodeRegistry, config: SystemConfig):
        self.nodes = node_registry
        self.data_sources = config.data_sources
        self.chunk_size_mb = config.chunk_size_mb
        self.retry_attempts = config.ingestion_retry_attempts if hasattr(config, 'ingestion_retry_attempts') else 3
        self.communicator = CrossCloudCommunicationProtocol(node_id=config.node_id, registry=node_registry) # NEW

    async def ingest_batch(self, batch_config: Dict[str, Any]):
        """Ingest data batch with chunking and distribution."""
        file_path = batch_config.get("file_path")
        if not file_path:
            print("Error: 'file_path' not specified in batch_config.")
            return

        print(f"Starting ingestion for batch from {file_path}...")

        for attempt in range(self.retry_attempts):
            try:
                # 1. Chunk the large file
                chunks = await self.chunk_large_file(file_path, self.chunk_size_mb)
                if not chunks:
                    print(f"No chunks generated for {file_path}. Retrying...")
                    continue

                # 2. Distribute chunks to available nodes
                await self.distribute_chunks_to_nodes(chunks)

                print(f"Successfully ingested and distributed batch from {file_path}.")
                return # Success, exit loop

            except Exception as e:
                print(f"Ingestion attempt {attempt + 1} failed for {file_path}: {e}")
                if attempt < self.retry_attempts - 1:
                    print(f"Retrying ingestion for {file_path}...")
                    await asyncio.sleep(2 ** attempt) # Exponential backoff
                else:
                    print(f"All {self.retry_attempts} attempts failed for {file_path}.")
                    # Depending on error handling strategy, might raise or log a critical error

    async def chunk_large_file(self, file_path: str, chunk_size_mb: int) -> List[bytes]:
        """Split large files into manageable chunks."""
        chunks = []
        chunk_size_bytes = chunk_size_mb * 1024 * 1024  # Convert MB to bytes

        try:
            with open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(chunk_size_bytes)
                    if not chunk:
                        break  # End of file
                    chunks.append(chunk)
        except FileNotFoundError:
            print(f"Error: File not found at {file_path}")
            return []
        except Exception as e:
            print(f"An error occurred while chunking file {file_path}: {e}")
            return []
        return chunks

    async def distribute_chunks_to_nodes(self, chunks: List[bytes]):
        """Distribute data chunks to available nodes for processing."""
        if not chunks:
            print("No chunks to distribute.")
            return

        available_nodes = await self.nodes.get_available_nodes()

        if not available_nodes:
            print("No available nodes to distribute chunks to.")
            return

        node_count = len(available_nodes)
        if node_count == 0:
            print("No nodes available for distribution.")
            return

        for i, chunk in enumerate(chunks):
            target_node = available_nodes[i % node_count]
            print(f"Distributing chunk {i+1} to node: {target_node.node_id} ({target_node.public_ip})")
            await self._send_chunk_to_node(chunk, target_node)

    async def _send_chunk_to_node(self, chunk: bytes, node: NodeInfo):
        """Sends a chunk to a specific node using the communication protocol."""
        try:
            # The payload should be a dictionary. We'll put the chunk data inside.
            payload = {"chunk_data": chunk.decode('latin-1')} # Assuming chunk is bytes, decode to string for JSON
            await self.communicator.send_message(
                target_node_id=node.node_id,
                message_type="data_chunk",
                payload=payload
            )
            print(f"Chunk sent to {node.node_id}.")
        except Exception as e:
            print(f"Error sending chunk to {node.node_id}: {e}")