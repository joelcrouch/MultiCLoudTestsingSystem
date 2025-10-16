import time
from typing import Dict, List, Optional
from collections import defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class StageMetrics:
    """Metrics for a single pipeline stage"""
    stage_name: str
    duration_seconds: float
    items_processed: int
    success_rate: float
    throughput_items_per_sec: float
    start_time: str
    end_time: str
    errors: int = 0


@dataclass
class BottleneckReport:
    """Report of detected bottleneck"""
    stage_name: str
    duration_seconds: float
    percentage_of_total: float
    severity: str  # 'minor', 'moderate', 'severe'
    recommendation: str


class PipelineMonitor:
    """
    Monitors pipeline performance and detects bottlenecks

    Tracks:
    - Stage-by-stage performance metrics
    - Overall pipeline throughput
    - Bottleneck detection
    - Performance trends over time
    """

    def __init__(self):
        self.metrics: Dict[str, List[StageMetrics]] = defaultdict(list)
        self.alerts: List[str] = []
        self.pipeline_runs: List[Dict] = []
        self.current_run_id = None

        print("📊 Pipeline Monitor initialized")

    def start_pipeline_run(self, run_id: str):
        """Start tracking a new pipeline run"""
        self.current_run_id = run_id
        self.pipeline_runs.append({
            'run_id': run_id,
            'start_time': datetime.now().isoformat(),
            'stages': {},
            'status': 'running'
        })

    def track_stage_performance(
        self,
        stage_name: str,
        duration: float,
        items_processed: int,
        success: bool = True,
        errors: int = 0
    ):
        """
        Track performance metrics for a pipeline stage

        Args:
            stage_name: Name of the stage (ingestion, processing, etc.)
            duration: Duration in seconds
            items_processed: Number of items processed
            success: Whether stage completed successfully
            errors: Number of errors encountered
        """
        # Calculate metrics
        success_rate = 1.0 if success else 0.0
        throughput = items_processed / duration if duration > 0 else 0.0

        # Create metrics record
        stage_metrics = StageMetrics(
            stage_name=stage_name,
            duration_seconds=duration,
            items_processed=items_processed,
            success_rate=success_rate,
            throughput_items_per_sec=throughput,
            start_time=datetime.now().isoformat(),
            end_time=datetime.now().isoformat(),
            errors=errors
        )

        # Store in history
        self.metrics[stage_name].append(stage_metrics)

        # Add to current run
        if self.current_run_id and self.pipeline_runs:
            current_run = self.pipeline_runs[-1]
            current_run['stages'][stage_name] = asdict(stage_metrics)

    def complete_pipeline_run(self, status: str, total_duration: float):
        """Mark current pipeline run as complete"""
        if self.pipeline_runs:
            current_run = self.pipeline_runs[-1]
            current_run['status'] = status
            current_run['end_time'] = datetime.now().isoformat()
            current_run['total_duration'] = total_duration

    def detect_bottlenecks(self, run_id: Optional[str] = None) -> List[BottleneckReport]:
        """
        Identify performance bottlenecks in the pipeline

        Returns list of bottleneck reports sorted by severity
        """
        # Get the run to analyze (latest by default)
        if run_id:
            run = next((r for r in self.pipeline_runs if r['run_id'] == run_id), None)
        else:
            run = self.pipeline_runs[-1] if self.pipeline_runs else None

        if not run or 'stages' not in run:
            return []

        bottlenecks = []

        # Calculate total duration
        total_duration = sum(
            stage['duration_seconds']
            for stage in run['stages'].values()
        )

        if total_duration == 0:
            return []

        # Analyze each stage
        for stage_name, metrics in run['stages'].items():
            duration = metrics['duration_seconds']
            percentage = (duration / total_duration) * 100

            # Determine severity and generate recommendation
            if percentage > 50:
                severity = 'severe'
                recommendation = f"CRITICAL: {stage_name} is using >{percentage:.0f}% of pipeline time. Immediate optimization required."
            elif percentage > 35:
                severity = 'moderate'
                recommendation = f"WARNING: {stage_name} is using {percentage:.0f}% of pipeline time. Consider optimization."
            elif percentage > 25:
                severity = 'minor'
                recommendation = f"INFO: {stage_name} is using {percentage:.0f}% of pipeline time. Monitor for trends."
            else:
                continue  # Not a bottleneck

            bottleneck = BottleneckReport(
                stage_name=stage_name,
                duration_seconds=duration,
                percentage_of_total=percentage,
                severity=severity,
                recommendation=recommendation
            )

            bottlenecks.append(bottleneck)

        # Sort by severity (severe -> moderate -> minor) then by percentage
        severity_order = {'severe': 0, 'moderate': 1, 'minor': 2}
        bottlenecks.sort(key=lambda x: (severity_order[x.severity], -x.percentage_of_total))

        return bottlenecks

    def generate_performance_report(self, run_id: Optional[str] = None) -> str:
        """
        Generate a comprehensive performance analysis report

        Returns formatted string report
        """
        # Get the run to analyze
        if run_id:
            run = next((r for r in self.pipeline_runs if r['run_id'] == run_id), None)
        else:
            run = self.pipeline_runs[-1] if self.pipeline_runs else None

        if not run:
            return "No pipeline runs to report"

        report = []
        report.append("="*80)
        report.append("📊 PIPELINE PERFORMANCE REPORT")
        report.append("="*80)
        report.append(f"Run ID: {run['run_id']}")
        report.append(f"Status: {run['status']}")
        report.append(f"Start Time: {run['start_time']}")

        if 'end_time' in run:
            report.append(f"End Time: {run['end_time']}")

        if 'total_duration' in run:
            report.append(f"Total Duration: {run['total_duration']:.2f}s")

        report.append("")

        # Stage breakdown
        if 'stages' in run:
            report.append("📈 STAGE-BY-STAGE BREAKDOWN:")
            report.append("-" * 80)

            total_duration = sum(s['duration_seconds'] for s in run['stages'].values())

            for stage_name, metrics in run['stages'].items():
                duration = metrics['duration_seconds']
                items = metrics['items_processed']
                throughput = metrics['throughput_items_per_sec']
                percentage = (duration / total_duration * 100) if total_duration > 0 else 0

                report.append(f"\n{stage_name.upper()}:")
                report.append(f"  Duration: {duration:.2f}s ({percentage:.1f}% of total)")
                report.append(f"  Items Processed: {items}")
                report.append(f"  Throughput: {throughput:.2f} items/sec")

                if metrics.get('errors', 0) > 0:
                    report.append(f"  ⚠️  Errors: {metrics['errors']}")

        report.append("")

        # Bottleneck analysis
        bottlenecks = self.detect_bottlenecks(run_id)

        if bottlenecks:
            report.append("🔍 BOTTLENECK ANALYSIS:")
            report.append("-" * 80)

            for bottleneck in bottlenecks:
                icon = "🔴" if bottleneck.severity == 'severe' else "🟡" if bottleneck.severity == 'moderate' else "🟢"
                report.append(f"\n{icon} {bottleneck.stage_name.upper()}")
                report.append(f"  Duration: {bottleneck.duration_seconds:.2f}s")
                report.append(f"  Percentage: {bottleneck.percentage_of_total:.1f}%")
                report.append(f"  Severity: {bottleneck.severity}")
                report.append(f"  Recommendation: {bottleneck.recommendation}")
        else:
            report.append("✅ No significant bottlenecks detected")

        report.append("")
        report.append("="*80)

        return "\n".join(report)

    def get_stage_statistics(self, stage_name: str) -> Dict:
        """
        Get aggregate statistics for a specific stage across all runs

        Returns dict with min, max, avg, and trend data
        """
        if stage_name not in self.metrics or not self.metrics[stage_name]:
            return {}

        stage_metrics = self.metrics[stage_name]
        durations = [m.duration_seconds for m in stage_metrics]
        throughputs = [m.throughput_items_per_sec for m in stage_metrics]

        return {
            'stage_name': stage_name,
            'total_runs': len(stage_metrics),
            'duration': {
                'min': min(durations),
                'max': max(durations),
                'avg': sum(durations) / len(durations),
                'latest': durations[-1]
            },
            'throughput': {
                'min': min(throughputs),
                'max': max(throughputs),
                'avg': sum(throughputs) / len(throughputs),
                'latest': throughputs[-1]
            },
            'total_items_processed': sum(m.items_processed for m in stage_metrics),
            'total_errors': sum(m.errors for m in stage_metrics)
        }

    def get_overall_statistics(self) -> Dict:
        """Get overall pipeline statistics across all runs"""
        if not self.pipeline_runs:
            return {}

        completed_runs = [r for r in self.pipeline_runs if r['status'] == 'success']
        failed_runs = [r for r in self.pipeline_runs if r['status'] == 'failed']

        total_runs = len(self.pipeline_runs)
        success_rate = len(completed_runs) / total_runs if total_runs > 0 else 0

        durations = [r['total_duration'] for r in self.pipeline_runs if 'total_duration' in r]

        stats = {
            'total_runs': total_runs,
            'successful_runs': len(completed_runs),
            'failed_runs': len(failed_runs),
            'success_rate': success_rate,
        }

        if durations:
            stats['duration'] = {
                'min': min(durations),
                'max': max(durations),
                'avg': sum(durations) / len(durations)
            }

        return stats

    def clear_history(self):
        """Clear all stored metrics and history"""
        self.metrics.clear()
        self.alerts.clear()
        self.pipeline_runs.clear()
        self.current_run_id = None


# Example usage
if __name__ == '__main__':
    monitor = PipelineMonitor()

    # Simulate a pipeline run
    monitor.start_pipeline_run('test_run_001')

    monitor.track_stage_performance('ingestion', duration=2.5, items_processed=100)
    monitor.track_stage_performance('processing', duration=8.2, items_processed=100)
    monitor.track_stage_performance('distribution', duration=5.1, items_processed=100)
    monitor.track_stage_performance('storage', duration=2.7, items_processed=100)

    monitor.complete_pipeline_run('success', total_duration=18.5)

    # Generate report
    print(monitor.generate_performance_report())
