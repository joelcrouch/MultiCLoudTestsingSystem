import asyncio
import time
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict

from src.pipeline.ingestion_engine import DataIngestionEngine
from src.pipeline.processing_workers import ProcessingWorkerPool
from src.pipeline.distribution_coordinator import DistributionCoordinator
from src.pipeline.storage_manager import StorageManager
from src.monitoring.pipeline_monitor import PipelineMonitor
from src.monitoring.pipeline_logger import PipelineLogger
from src.monitoring.status_dashboard import StatusDashboard


class PipelineStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class PipelineResult:
    status: str
    duration_seconds: float = 0.0
    chunks_processed: int = 0
    metrics: Optional[Dict] = None
    error: Optional[str] = None


class PipelineMetrics:
    """Track metrics across all pipeline stages"""

    def __init__(self):
        self.stage_metrics = defaultdict(dict)
        self.stage_timings = {}

    def record_stage(self, stage_name: str, items_processed: int, duration: float = 0.0):
        """Record stage completion metrics"""
        self.stage_metrics[stage_name] = {
            'items_processed': items_processed,
            'duration_seconds': duration,
            'success_rate': 1.0 if items_processed > 0 else 0.0
        }
        self.stage_timings[stage_name] = duration

    def get_summary(self) -> Dict:
        """Get summary of all metrics"""
        return dict(self.stage_metrics)

    def get_stage_breakdown(self) -> Dict:
        """Get timing breakdown by stage"""
        return self.stage_timings


class PipelineOrchestrator:
    """
    Coordinates complete end-to-end pipeline execution
    Ingestion -> Processing -> Distribution -> Storage
    """

    def __init__(self, node_registry, config_dir='config/', enable_monitoring=True):
        self.node_registry = node_registry

        # Initialize all pipeline stages
        self.ingestion_engine = DataIngestionEngine(node_registry)
        self.processing_pool = ProcessingWorkerPool(node_registry)
        self.distribution_coordinator = DistributionCoordinator(node_registry)
        self.storage_manager = StorageManager(node_registry)

        # Pipeline state tracking
        self.pipeline_status = PipelineStatus.IDLE
        self.current_batch = None
        self.current_stage = None
        self.metrics = PipelineMetrics()

        # Initialize monitoring components
        self.enable_monitoring = enable_monitoring
        if self.enable_monitoring:
            self.monitor = PipelineMonitor()
            self.logger = PipelineLogger()
            self.dashboard = StatusDashboard()
        else:
            self.monitor = None
            self.logger = None
            self.dashboard = None

        print(f"🎭 Pipeline Orchestrator initialized")
        print(f"   All 4 stages ready: Ingestion → Processing → Distribution → Storage")
        if self.enable_monitoring:
            print(f"   Monitoring: ENABLED (metrics, logging, dashboard)")

    async def run_pipeline(self, batch_config: Dict) -> PipelineResult:
        """
        Execute complete pipeline: Ingestion -> Processing -> Distribution -> Storage

        Args:
            batch_config: Configuration for the batch, must include:
                - batch_id: Unique identifier for this batch
                - data_source: Path to data source or source configuration
                - expected_size_mb: Expected size in MB (optional)

        Returns:
            PipelineResult with status, metrics, and timing information
        """
        print(f"\n{'='*60}")
        print(f"Starting Pipeline Execution")
        print(f"Batch: {batch_config.get('batch_id', 'unknown')}")
        print(f"{'='*60}\n")

        start_time = time.time()
        run_id = batch_config.get('batch_id', f'run_{int(time.time())}')

        self.pipeline_status = PipelineStatus.RUNNING
        self.current_batch = batch_config

        # Start monitoring
        if self.enable_monitoring:
            self.monitor.start_pipeline_run(run_id)
            self.logger.log_pipeline_start(run_id, batch_config)
            self.dashboard.display_compact_status(self)

        try:
            # Stage 1: Data Ingestion
            print("STAGE 1: Data Ingestion")
            self.current_stage = "ingestion"
            stage_start = time.time()

            if self.enable_monitoring:
                self.logger.log_stage_start('ingestion')

            ingested_chunks = await self.ingestion_engine.ingest_batch(
                custom_source_path=batch_config['data_source']
            )

            stage_duration = time.time() - stage_start
            self.metrics.record_stage('ingestion', len(ingested_chunks), stage_duration)

            if self.enable_monitoring:
                self.monitor.track_stage_performance('ingestion', stage_duration, len(ingested_chunks))
                self.logger.log_stage_complete('ingestion', stage_duration, len(ingested_chunks), 1.0)

            print(f"✅ Ingestion complete: {len(ingested_chunks)} chunks in {stage_duration:.2f}s")

            # Stage 2: Processing
            print("\nSTAGE 2: Processing")
            self.current_stage = "processing"
            stage_start = time.time()

            if self.enable_monitoring:
                self.logger.log_stage_start('processing')

            processed_chunks = await self.processing_pool.process_chunks(
                ingested_chunks
            )

            stage_duration = time.time() - stage_start
            self.metrics.record_stage('processing', len(processed_chunks), stage_duration)

            if self.enable_monitoring:
                self.monitor.track_stage_performance('processing', stage_duration, len(processed_chunks))
                self.logger.log_stage_complete('processing', stage_duration, len(processed_chunks), 1.0)

            print(f"✅ Processing complete: {len(processed_chunks)} chunks in {stage_duration:.2f}s")

            # Stage 3: Distribution
            print("\nSTAGE 3: Distribution")
            self.current_stage = "distribution"
            stage_start = time.time()

            if self.enable_monitoring:
                self.logger.log_stage_start('distribution')

            distributed_chunks = await self.distribution_coordinator.distribute_processed_chunks(
                processed_chunks
            )

            stage_duration = time.time() - stage_start
            self.metrics.record_stage('distribution', len(distributed_chunks), stage_duration)

            if self.enable_monitoring:
                self.monitor.track_stage_performance('distribution', stage_duration, len(distributed_chunks))
                self.logger.log_stage_complete('distribution', stage_duration, len(distributed_chunks), 1.0)

            print(f"✅ Distribution complete: {len(distributed_chunks)} chunks in {stage_duration:.2f}s")

            # Stage 4: Storage
            print("\nSTAGE 4: Storage")
            self.current_stage = "storage"
            stage_start = time.time()

            if self.enable_monitoring:
                self.logger.log_stage_start('storage')

            stored_chunks = await self.storage_manager.store_distributed_chunks(
                distributed_chunks
            )

            stage_duration = time.time() - stage_start
            self.metrics.record_stage('storage', len(stored_chunks), stage_duration)

            if self.enable_monitoring:
                self.monitor.track_stage_performance('storage', stage_duration, len(stored_chunks))
                self.logger.log_stage_complete('storage', stage_duration, len(stored_chunks), 1.0)

            print(f"✅ Storage complete: {len(stored_chunks)} replicas in {stage_duration:.2f}s")

            # Calculate final metrics
            duration = time.time() - start_time
            self.pipeline_status = PipelineStatus.COMPLETED

            # Complete monitoring
            if self.enable_monitoring:
                self.monitor.complete_pipeline_run('success', duration)
                self.logger.log_pipeline_complete(run_id, 'success', duration, len(ingested_chunks))

                # Generate and display performance report
                print("\n" + self.monitor.generate_performance_report())

            print(f"\n{'='*60}")
            print(f"Pipeline Execution Complete")
            print(f"Total Duration: {duration:.2f}s")
            print(f"Chunks Processed: {len(ingested_chunks)}")
            print(f"{'='*60}\n")

            return PipelineResult(
                status='success',
                duration_seconds=duration,
                chunks_processed=len(ingested_chunks),
                metrics=self.metrics.get_summary()
            )

        except Exception as e:
            self.pipeline_status = PipelineStatus.FAILED
            duration = time.time() - start_time

            # Log failure
            if self.enable_monitoring:
                self.monitor.complete_pipeline_run('failed', duration)
                self.logger.log_pipeline_complete(run_id, 'failed', duration, 0)
                self.logger.log_error_event(
                    error_type=type(e).__name__,
                    error_message=str(e),
                    context={'stage': self.current_stage}
                )

            print(f"\n{'='*60}")
            print(f"❌ Pipeline Failed")
            print(f"Error: {e}")
            print(f"Failed at stage: {self.current_stage}")
            print(f"Duration before failure: {duration:.2f}s")
            print(f"{'='*60}\n")

            return PipelineResult(
                status='failed',
                duration_seconds=duration,
                error=str(e),
                metrics=self.metrics.get_summary()
            )

    def get_status(self) -> Dict:
        """Get current pipeline status"""
        return {
            'status': self.pipeline_status.value,
            'current_stage': self.current_stage,
            'current_batch': self.current_batch.get('batch_id') if self.current_batch else None,
            'metrics': self.metrics.get_summary()
        }

    def get_healthy_nodes(self) -> int:
        """Count healthy nodes"""
        if not hasattr(self.node_registry, 'nodes'):
            return 0
        return sum(1 for node in self.node_registry.nodes.values()
                  if hasattr(node, 'status') and node.status == 'healthy')

    def get_unhealthy_nodes(self) -> int:
        """Count unhealthy nodes"""
        if not hasattr(self.node_registry, 'nodes'):
            return 0
        return sum(1 for node in self.node_registry.nodes.values()
                  if hasattr(node, 'status') and node.status != 'healthy')


# Example usage
async def main():
    """Example of running the pipeline orchestrator"""
    from types import SimpleNamespace

    # Mock node registry
    mock_registry = SimpleNamespace()
    mock_registry.nodes = {
        'aws-node-1': SimpleNamespace(
            node_id='aws-node-1',
            cloud_provider='aws',
            status='healthy',
            network_latency={'gcp': 50}
        ),
        'aws-node-2': SimpleNamespace(
            node_id='aws-node-2',
            cloud_provider='aws',
            status='healthy',
            network_latency={'gcp': 50}
        ),
        'gcp-node-1': SimpleNamespace(
            node_id='gcp-node-1',
            cloud_provider='gcp',
            status='healthy',
            network_latency={'aws': 50}
        )
    }

    # Create orchestrator
    orchestrator = PipelineOrchestrator(mock_registry)

    # Configure test batch
    batch_config = {
        'batch_id': 'test_batch_001',
        'data_source': './test_data/sample_data',
        'expected_size_mb': 100
    }

    # Run pipeline
    result = await orchestrator.run_pipeline(batch_config)

    # Display results
    print(f"\n📊 Final Results:")
    print(f"   Status: {result.status}")
    print(f"   Duration: {result.duration_seconds:.2f}s")
    print(f"   Chunks: {result.chunks_processed}")
    print(f"   Metrics: {result.metrics}")


if __name__ == '__main__':
    asyncio.run(main())
