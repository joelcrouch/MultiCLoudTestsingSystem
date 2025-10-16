import pytest
import time
from pathlib import Path
from types import SimpleNamespace
from src.monitoring.pipeline_monitor import PipelineMonitor
from src.monitoring.pipeline_logger import PipelineLogger
from src.monitoring.status_dashboard import StatusDashboard


class TestPipelineMonitor:
    """Test pipeline performance monitoring"""

    def test_monitor_initialization(self):
        """Test monitor initializes correctly"""
        monitor = PipelineMonitor()
        assert monitor is not None
        assert len(monitor.metrics) == 0
        assert len(monitor.pipeline_runs) == 0

    def test_track_stage_performance(self):
        """Test tracking stage performance metrics"""
        monitor = PipelineMonitor()
        monitor.start_pipeline_run('test_run')

        monitor.track_stage_performance('ingestion', duration=2.5, items_processed=100)

        assert 'ingestion' in monitor.metrics
        assert len(monitor.metrics['ingestion']) == 1

        metrics = monitor.metrics['ingestion'][0]
        assert metrics.stage_name == 'ingestion'
        assert metrics.duration_seconds == 2.5
        assert metrics.items_processed == 100

    def test_detect_bottlenecks(self):
        """Test bottleneck detection"""
        monitor = PipelineMonitor()
        monitor.start_pipeline_run('test_run')

        # Simulate stages with one bottleneck
        monitor.track_stage_performance('ingestion', duration=2.0, items_processed=100)
        monitor.track_stage_performance('processing', duration=10.0, items_processed=100)  # Bottleneck
        monitor.track_stage_performance('distribution', duration=3.0, items_processed=100)
        monitor.track_stage_performance('storage', duration=2.0, items_processed=100)

        monitor.complete_pipeline_run('success', total_duration=17.0)

        bottlenecks = monitor.detect_bottlenecks()

        assert len(bottlenecks) > 0
        assert bottlenecks[0].stage_name == 'processing'
        assert bottlenecks[0].percentage_of_total > 50

    def test_generate_performance_report(self):
        """Test performance report generation"""
        monitor = PipelineMonitor()
        monitor.start_pipeline_run('test_run')

        monitor.track_stage_performance('ingestion', duration=2.5, items_processed=100)
        monitor.track_stage_performance('processing', duration=8.2, items_processed=100)

        monitor.complete_pipeline_run('success', total_duration=10.7)

        report = monitor.generate_performance_report()

        assert 'PIPELINE PERFORMANCE REPORT' in report
        assert 'test_run' in report
        assert 'ingestion' in report.lower()
        assert 'processing' in report.lower()

    def test_get_stage_statistics(self):
        """Test getting stage statistics"""
        monitor = PipelineMonitor()
        monitor.start_pipeline_run('run1')

        # Run multiple times
        for i in range(3):
            monitor.track_stage_performance('ingestion', duration=2.0 + i*0.5, items_processed=100)

        stats = monitor.get_stage_statistics('ingestion')

        assert stats['total_runs'] == 3
        assert 'duration' in stats
        assert stats['duration']['min'] == 2.0
        assert stats['duration']['max'] == 3.0

    def test_get_overall_statistics(self):
        """Test overall pipeline statistics"""
        monitor = PipelineMonitor()

        # Simulate multiple runs
        for i in range(3):
            monitor.start_pipeline_run(f'run_{i}')
            monitor.track_stage_performance('ingestion', duration=2.0, items_processed=100)
            monitor.complete_pipeline_run('success', total_duration=10.0)

        stats = monitor.get_overall_statistics()

        assert stats['total_runs'] == 3
        assert stats['successful_runs'] == 3
        assert stats['success_rate'] == 1.0


class TestPipelineLogger:
    """Test structured logging"""

    @pytest.fixture
    def logger(self, tmp_path):
        """Create logger with temporary log directory"""
        log_dir = tmp_path / "logs"
        return PipelineLogger(log_dir=str(log_dir))

    def test_logger_initialization(self, logger):
        """Test logger initializes correctly"""
        assert logger is not None
        assert logger.logger is not None

    def test_log_pipeline_events(self, logger):
        """Test logging pipeline events"""
        logger.log_pipeline_start('test_run', {'batch_id': 'test'})
        logger.log_stage_start('ingestion')
        logger.log_stage_complete('ingestion', duration=2.5, items_processed=100, success_rate=1.0)
        logger.log_pipeline_complete('test_run', 'success', duration=10.0, chunks_processed=100)

        # Verify log file was created
        log_file = Path(logger.get_log_file_path())
        assert log_file.exists()

    def test_log_error_event(self, logger):
        """Test logging error events"""
        logger.log_error_event('NetworkError', 'Connection timeout', context={'node': 'aws-node-1'})

        log_file = Path(logger.get_log_file_path())
        assert log_file.exists()

    def test_log_performance_metric(self, logger):
        """Test logging performance metrics"""
        logger.log_performance_metric('throughput', 150.5, unit='MB/s')

        log_file = Path(logger.get_log_file_path())
        assert log_file.exists()

    def test_analyze_logs(self, logger):
        """Test log analysis"""
        # Generate some log entries
        logger.log_pipeline_start('test_run', {'batch_id': 'test'})
        logger.info('test_event', 'Test message')
        logger.error('error_event', 'Test error')

        # Analyze
        analysis = logger.analyze_logs()

        assert 'total_entries' in analysis
        assert analysis['total_entries'] > 0
        assert 'by_level' in analysis

    def test_set_context(self, logger):
        """Test setting log context"""
        logger.set_context('run_123', 'processing')

        assert logger.current_run_id == 'run_123'
        assert logger.current_stage == 'processing'


class TestStatusDashboard:
    """Test status dashboard"""

    @pytest.fixture
    def mock_orchestrator(self):
        """Create mock orchestrator for testing"""
        mock_registry = SimpleNamespace()
        mock_registry.nodes = {
            'aws-node-1': SimpleNamespace(
                node_id='aws-node-1',
                cloud_provider='aws',
                status='healthy',
                region='us-east-1'
            ),
            'gcp-node-1': SimpleNamespace(
                node_id='gcp-node-1',
                cloud_provider='gcp',
                status='unhealthy',
                region='us-central1'
            )
        }

        class MockOrchestrator:
            def __init__(self, node_registry):
                self.node_registry = node_registry
                self.pipeline_status = 'running'
                self.current_stage = 'processing'
                self.current_batch = {'batch_id': 'test_batch'}

            def get_status(self):
                return {
                    'status': 'running',
                    'current_stage': 'processing',
                    'current_batch': 'test_batch',
                    'metrics': {
                        'ingestion': {'items_processed': 100, 'duration_seconds': 2.5, 'success_rate': 1.0}
                    }
                }

            def get_healthy_nodes(self):
                return sum(1 for n in self.node_registry.nodes.values() if n.status == 'healthy')

            def get_unhealthy_nodes(self):
                return sum(1 for n in self.node_registry.nodes.values() if n.status != 'healthy')

        return MockOrchestrator(mock_registry)

    def test_dashboard_initialization(self):
        """Test dashboard initializes correctly"""
        dashboard = StatusDashboard()
        assert dashboard is not None

    def test_display_pipeline_status(self, mock_orchestrator, capsys):
        """Test displaying pipeline status"""
        dashboard = StatusDashboard()
        dashboard.display_pipeline_status(mock_orchestrator)

        captured = capsys.readouterr()
        assert 'PIPELINE STATUS DASHBOARD' in captured.out
        assert 'running' in captured.out.lower()

    def test_display_compact_status(self, mock_orchestrator, capsys):
        """Test compact status display"""
        dashboard = StatusDashboard()
        dashboard.display_compact_status(mock_orchestrator)

        captured = capsys.readouterr()
        assert 'RUNNING' in captured.out
        assert 'processing' in captured.out

    def test_display_progress_bar(self, capsys):
        """Test progress bar display"""
        dashboard = StatusDashboard()
        dashboard.display_progress_bar(50, 100, stage_name="Test")

        captured = capsys.readouterr()
        assert '50.0%' in captured.out

    def test_display_throughput(self, capsys):
        """Test throughput display"""
        dashboard = StatusDashboard()
        dashboard.display_throughput(1000, 5.0, unit="chunks")

        captured = capsys.readouterr()
        assert 'Throughput' in captured.out
        assert 'chunks/sec' in captured.out

    def test_display_node_status(self, mock_orchestrator, capsys):
        """Test node status display"""
        dashboard = StatusDashboard()
        dashboard.display_node_status(mock_orchestrator.node_registry)

        captured = capsys.readouterr()
        assert 'NODE STATUS' in captured.out
        assert 'aws-node-1' in captured.out
        assert 'gcp-node-1' in captured.out


@pytest.mark.asyncio
async def test_integration_with_orchestrator(tmp_path):
    """Test monitoring integration with orchestrator"""
    from src.pipeline.pipeline_orchestrator import PipelineOrchestrator

    # Create test data
    data_dir = tmp_path / "test_data"
    data_dir.mkdir()
    test_file = data_dir / "test.dat"
    test_file.write_bytes(b"test data" * 1000)

    # Create mock registry
    mock_registry = SimpleNamespace()
    mock_registry.nodes = {
        'aws-node-1': SimpleNamespace(
            node_id='aws-node-1',
            cloud_provider='aws',
            status='healthy',
            network_latency={'gcp': 50, 'aws': 5}
        )
    }

    # Create orchestrator with monitoring enabled
    orchestrator = PipelineOrchestrator(mock_registry, enable_monitoring=True)

    assert orchestrator.monitor is not None
    assert orchestrator.logger is not None
    assert orchestrator.dashboard is not None

    # Run pipeline
    batch_config = {
        'batch_id': 'monitoring_test',
        'data_source': str(data_dir),
        'expected_size_mb': 1
    }

    result = await orchestrator.run_pipeline(batch_config)

    # Verify monitoring captured data
    assert len(orchestrator.monitor.pipeline_runs) > 0
    assert orchestrator.monitor.pipeline_runs[0]['run_id'] == 'monitoring_test'

    # Verify log file was created
    log_file = Path(orchestrator.logger.get_log_file_path())
    assert log_file.exists()
