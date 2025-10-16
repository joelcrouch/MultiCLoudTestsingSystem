import logging
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Any


class PipelineLogger:
    """
    Structured JSON logging for pipeline events

    Features:
    - JSON-formatted logs for easy parsing
    - Multiple log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - Stage-specific logging
    - Error tracking with stack traces
    - Performance metrics logging
    """

    def __init__(self, log_dir: str = 'logs', log_level: str = 'INFO'):
        """
        Initialize pipeline logger

        Args:
            log_dir: Directory to store log files
            log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Create logger
        self.logger = logging.getLogger('pipeline')
        self.logger.setLevel(getattr(logging, log_level.upper()))

        # Remove existing handlers
        self.logger.handlers.clear()

        # File handler for JSON logs
        log_file = self.log_dir / f"pipeline_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter('%(message)s'))
        self.logger.addHandler(file_handler)

        # Console handler for human-readable logs
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        )
        self.logger.addHandler(console_handler)

        # Track current context
        self.current_run_id = None
        self.current_stage = None

        print(f"📝 Pipeline Logger initialized (logs: {log_file})")

    def set_context(self, run_id: str, stage: Optional[str] = None):
        """Set current execution context"""
        self.current_run_id = run_id
        self.current_stage = stage

    def _create_log_entry(
        self,
        event: str,
        level: str,
        message: str,
        **kwargs
    ) -> Dict:
        """Create structured log entry"""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'level': level,
            'event': event,
            'message': message,
        }

        # Add context
        if self.current_run_id:
            entry['run_id'] = self.current_run_id
        if self.current_stage:
            entry['stage'] = self.current_stage

        # Add any additional fields
        entry.update(kwargs)

        return entry

    def _log(self, level: str, event: str, message: str, **kwargs):
        """Internal log method"""
        entry = self._create_log_entry(event, level, message, **kwargs)
        log_line = json.dumps(entry)

        # Log to appropriate level
        log_method = getattr(self.logger, level.lower())
        log_method(log_line)

    def info(self, event: str, message: str, **kwargs):
        """Log info level message"""
        self._log('INFO', event, message, **kwargs)

    def debug(self, event: str, message: str, **kwargs):
        """Log debug level message"""
        self._log('DEBUG', event, message, **kwargs)

    def warning(self, event: str, message: str, **kwargs):
        """Log warning level message"""
        self._log('WARNING', event, message, **kwargs)

    def error(self, event: str, message: str, error: Optional[Exception] = None, **kwargs):
        """Log error level message"""
        if error:
            kwargs['error_type'] = type(error).__name__
            kwargs['error_message'] = str(error)

        self._log('ERROR', event, message, **kwargs)

    def critical(self, event: str, message: str, **kwargs):
        """Log critical level message"""
        self._log('CRITICAL', event, message, **kwargs)

    def log_pipeline_start(self, run_id: str, batch_config: Dict):
        """Log pipeline execution start"""
        self.set_context(run_id)
        self.info(
            event='pipeline_start',
            message=f'Pipeline execution started: {run_id}',
            batch_id=batch_config.get('batch_id'),
            data_source=batch_config.get('data_source'),
            expected_size_mb=batch_config.get('expected_size_mb')
        )

    def log_pipeline_complete(
        self,
        run_id: str,
        status: str,
        duration: float,
        chunks_processed: int
    ):
        """Log pipeline execution completion"""
        self.info(
            event='pipeline_complete',
            message=f'Pipeline execution completed: {status}',
            run_id=run_id,
            status=status,
            duration_seconds=duration,
            chunks_processed=chunks_processed
        )

    def log_stage_start(self, stage_name: str):
        """Log pipeline stage start"""
        self.current_stage = stage_name
        self.info(
            event='stage_start',
            message=f'Stage started: {stage_name}',
            stage=stage_name
        )

    def log_stage_complete(
        self,
        stage_name: str,
        duration: float,
        items_processed: int,
        success_rate: float
    ):
        """Log pipeline stage completion"""
        self.info(
            event='stage_complete',
            message=f'Stage completed: {stage_name}',
            stage=stage_name,
            duration_seconds=duration,
            items_processed=items_processed,
            success_rate=success_rate
        )

    def log_error_event(
        self,
        error_type: str,
        error_message: str,
        context: Optional[Dict] = None
    ):
        """Log an error event"""
        self.error(
            event='error_occurred',
            message=f'{error_type}: {error_message}',
            error_type=error_type,
            context=context or {}
        )

    def log_performance_metric(
        self,
        metric_name: str,
        value: float,
        unit: str = "",
        metadata: Optional[Dict] = None
    ):
        """Log a performance metric"""
        self.debug(
            event='performance_metric',
            message=f'{metric_name}: {value} {unit}',
            metric_name=metric_name,
            value=value,
            unit=unit,
            metadata=metadata or {}
        )

    def log_node_event(
        self,
        node_id: str,
        event_type: str,
        message: str,
        **kwargs
    ):
        """Log a node-related event"""
        self.info(
            event=f'node_{event_type}',
            message=message,
            node_id=node_id,
            **kwargs
        )

    def log_data_transfer(
        self,
        source: str,
        destination: str,
        size_bytes: int,
        duration: float
    ):
        """Log a data transfer event"""
        throughput_mbps = (size_bytes / (1024*1024)) / duration if duration > 0 else 0

        self.debug(
            event='data_transfer',
            message=f'Data transfer: {source} → {destination}',
            source=source,
            destination=destination,
            size_bytes=size_bytes,
            duration_seconds=duration,
            throughput_mbps=throughput_mbps
        )

    def get_log_file_path(self) -> str:
        """Get current log file path"""
        return str(self.log_dir / f"pipeline_{datetime.now().strftime('%Y%m%d')}.log")

    def analyze_logs(self, log_file: Optional[str] = None) -> Dict:
        """
        Analyze log file and return summary statistics

        Args:
            log_file: Path to log file (uses today's log if not specified)

        Returns:
            Dictionary with log analysis
        """
        if not log_file:
            log_file = self.get_log_file_path()

        log_path = Path(log_file)
        if not log_path.exists():
            return {'error': 'Log file not found'}

        stats = {
            'total_entries': 0,
            'by_level': {'INFO': 0, 'DEBUG': 0, 'WARNING': 0, 'ERROR': 0, 'CRITICAL': 0},
            'by_event': {},
            'errors': [],
            'performance_metrics': []
        }

        with open(log_path, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    stats['total_entries'] += 1

                    # Count by level
                    level = entry.get('level', 'UNKNOWN')
                    if level in stats['by_level']:
                        stats['by_level'][level] += 1

                    # Count by event
                    event = entry.get('event', 'unknown')
                    stats['by_event'][event] = stats['by_event'].get(event, 0) + 1

                    # Collect errors
                    if level in ['ERROR', 'CRITICAL']:
                        stats['errors'].append({
                            'timestamp': entry.get('timestamp'),
                            'event': event,
                            'message': entry.get('message')
                        })

                    # Collect performance metrics
                    if event == 'performance_metric':
                        stats['performance_metrics'].append(entry)

                except json.JSONDecodeError:
                    continue

        return stats


# Example usage
if __name__ == '__main__':
    logger = PipelineLogger()

    # Log pipeline execution
    logger.log_pipeline_start('test_run_001', {
        'batch_id': 'batch_001',
        'data_source': './test_data',
        'expected_size_mb': 100
    })

    # Log stages
    logger.log_stage_start('ingestion')
    logger.log_stage_complete('ingestion', duration=2.5, items_processed=100, success_rate=1.0)

    logger.log_stage_start('processing')
    logger.log_stage_complete('processing', duration=8.2, items_processed=95, success_rate=0.95)

    # Log error
    logger.log_error_event('NetworkError', 'Connection timeout', context={'node': 'aws-node-1'})

    # Log performance metric
    logger.log_performance_metric('throughput', 150.5, unit='MB/s')

    # Complete pipeline
    logger.log_pipeline_complete('test_run_001', 'success', duration=18.5, chunks_processed=100)

    # Analyze logs
    analysis = logger.analyze_logs()
    print("\n📊 Log Analysis:")
    print(json.dumps(analysis, indent=2))
