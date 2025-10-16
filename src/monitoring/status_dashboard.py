import time
from typing import Dict, Optional
from datetime import datetime


class StatusDashboard:
    """
    Real-time terminal-based status dashboard for pipeline monitoring

    Displays:
    - Pipeline status and current stage
    - Node health status
    - Throughput metrics
    - Progress indicators
    - ETA estimates
    """

    def __init__(self):
        self.last_update = None
        print("📺 Status Dashboard initialized")

    def display_pipeline_status(
        self,
        orchestrator,
        clear_screen: bool = False
    ):
        """
        Display real-time pipeline status

        Args:
            orchestrator: PipelineOrchestrator instance
            clear_screen: Whether to clear screen before displaying (for live updates)
        """
        if clear_screen:
            print("\033[2J\033[H")  # ANSI clear screen and move cursor to top

        # Get current status
        status = orchestrator.get_status()
        pipeline_status = status.get('status', 'unknown')
        current_stage = status.get('current_stage', 'none')
        current_batch = status.get('current_batch', 'none')

        # Get node health
        healthy_nodes = orchestrator.get_healthy_nodes()
        unhealthy_nodes = orchestrator.get_unhealthy_nodes()
        total_nodes = healthy_nodes + unhealthy_nodes

        # Build dashboard
        dashboard = []
        dashboard.append("╔" + "═"*78 + "╗")
        dashboard.append("║" + " "*20 + "PIPELINE STATUS DASHBOARD" + " "*33 + "║")
        dashboard.append("╠" + "═"*78 + "╣")

        # Status section
        status_icon = self._get_status_icon(pipeline_status)
        dashboard.append(f"║ Status: {status_icon} {pipeline_status.upper():<64} ║")
        dashboard.append(f"║ Current Stage: {current_stage:<59} ║")
        dashboard.append(f"║ Batch ID: {current_batch:<64} ║")
        dashboard.append("║" + " "*78 + "║")

        # Nodes section
        dashboard.append("║ CLUSTER HEALTH:" + " "*62 + "║")
        node_health_bar = self._create_health_bar(healthy_nodes, total_nodes)
        dashboard.append(f"║   {node_health_bar:<74} ║")
        dashboard.append(f"║   Healthy: {healthy_nodes}/{total_nodes} nodes" + " "*(62 - len(str(healthy_nodes)) - len(str(total_nodes))) + "║")

        if unhealthy_nodes > 0:
            dashboard.append(f"║   ⚠️  Unhealthy: {unhealthy_nodes} nodes" + " "*(57 - len(str(unhealthy_nodes))) + "║")

        dashboard.append("║" + " "*78 + "║")

        # Metrics section (if available)
        metrics = status.get('metrics', {})
        if metrics:
            dashboard.append("║ STAGE METRICS:" + " "*63 + "║")

            for stage_name in ['ingestion', 'processing', 'distribution', 'storage']:
                if stage_name in metrics:
                    stage_metrics = metrics[stage_name]
                    items = stage_metrics.get('items_processed', 0)
                    duration = stage_metrics.get('duration_seconds', 0)
                    success_rate = stage_metrics.get('success_rate', 0)

                    stage_display = f"{stage_name.capitalize():<15}"
                    items_display = f"Items: {items:<6}"
                    time_display = f"Time: {duration:.2f}s"
                    success_display = f"Success: {success_rate*100:.0f}%"

                    line = f"║   {stage_display} {items_display} {time_display:<12} {success_display:<13}║"
                    dashboard.append(line)

        dashboard.append("║" + " "*78 + "║")

        # Timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        dashboard.append(f"║ Last Updated: {timestamp:<62} ║")

        dashboard.append("╚" + "═"*78 + "╝")

        # Print dashboard
        print("\n".join(dashboard))

        self.last_update = time.time()

    def display_compact_status(self, orchestrator):
        """Display compact single-line status"""
        status = orchestrator.get_status()
        pipeline_status = status.get('status', 'unknown')
        current_stage = status.get('current_stage', 'none')
        healthy_nodes = orchestrator.get_healthy_nodes()
        total_nodes = healthy_nodes + orchestrator.get_unhealthy_nodes()

        status_icon = self._get_status_icon(pipeline_status)

        print(f"[{status_icon} {pipeline_status.upper()}] Stage: {current_stage} | Nodes: {healthy_nodes}/{total_nodes} healthy")

    def display_progress_bar(
        self,
        current: int,
        total: int,
        stage_name: str = "",
        width: int = 50
    ):
        """
        Display a progress bar for current stage

        Args:
            current: Current progress value
            total: Total value
            stage_name: Name of the stage
            width: Width of progress bar in characters
        """
        if total == 0:
            percentage = 0
        else:
            percentage = (current / total) * 100

        filled = int(width * current // total) if total > 0 else 0
        bar = "█" * filled + "░" * (width - filled)

        stage_text = f"{stage_name}: " if stage_name else ""
        print(f"\r{stage_text}|{bar}| {percentage:.1f}% ({current}/{total})", end="", flush=True)

    def display_throughput(
        self,
        items_processed: int,
        duration: float,
        unit: str = "items"
    ):
        """Display current throughput metrics"""
        if duration > 0:
            throughput_per_sec = items_processed / duration
            throughput_per_min = throughput_per_sec * 60
        else:
            throughput_per_sec = 0
            throughput_per_min = 0

        print(f"📊 Throughput: {throughput_per_sec:.2f} {unit}/sec ({throughput_per_min:.2f} {unit}/min)")

    def display_node_status(self, node_registry):
        """Display detailed node status table"""
        print("\n" + "="*80)
        print("🌐 NODE STATUS")
        print("="*80)

        if not hasattr(node_registry, 'nodes'):
            print("No nodes registered")
            return

        # Header
        print(f"{'Node ID':<20} {'Cloud':<10} {'Status':<12} {'Region':<20}")
        print("-"*80)

        # Node details
        for node_id, node in node_registry.nodes.items():
            cloud = getattr(node, 'cloud_provider', 'unknown')
            status = getattr(node, 'status', 'unknown')
            region = getattr(node, 'region', 'N/A')

            status_icon = "✅" if status == 'healthy' else "❌"

            print(f"{node_id:<20} {cloud:<10} {status_icon} {status:<10} {region:<20}")

        print("="*80)

    def _get_status_icon(self, status: str) -> str:
        """Get emoji icon for pipeline status"""
        icons = {
            'idle': '⏸️ ',
            'running': '🏃',
            'completed': '✅',
            'success': '✅',
            'failed': '❌',
            'error': '🔥'
        }
        return icons.get(status.lower(), '❓')

    def _create_health_bar(self, healthy: int, total: int, width: int = 30) -> str:
        """Create a visual health bar"""
        if total == 0:
            return "[" + "░"*width + "]"

        filled = int(width * healthy / total)
        percentage = (healthy / total) * 100

        # Color based on health percentage
        if percentage >= 80:
            fill_char = "█"  # Green (represented by full block)
        elif percentage >= 50:
            fill_char = "▓"  # Yellow (represented by medium shade)
        else:
            fill_char = "▒"  # Red (represented by light shade)

        bar = fill_char * filled + "░" * (width - filled)
        return f"[{bar}] {percentage:.0f}%"

    def clear_screen(self):
        """Clear the terminal screen"""
        print("\033[2J\033[H")


# Example usage
if __name__ == '__main__':
    from types import SimpleNamespace
    import time

    # Mock orchestrator for demo
    mock_registry = SimpleNamespace()
    mock_registry.nodes = {
        'aws-node-1': SimpleNamespace(
            node_id='aws-node-1',
            cloud_provider='aws',
            status='healthy',
            region='us-east-1'
        ),
        'aws-node-2': SimpleNamespace(
            node_id='aws-node-2',
            cloud_provider='aws',
            status='healthy',
            region='us-west-2'
        ),
        'gcp-node-1': SimpleNamespace(
            node_id='gcp-node-1',
            cloud_provider='gcp',
            status='healthy',
            region='us-central1'
        ),
        'gcp-node-2': SimpleNamespace(
            node_id='gcp-node-2',
            cloud_provider='gcp',
            status='unhealthy',
            region='us-east1'
        )
    }

    class MockOrchestrator:
        def __init__(self, node_registry):
            self.node_registry = node_registry
            self.pipeline_status = 'running'
            self.current_stage = 'processing'
            self.current_batch = {'batch_id': 'test_batch_001'}

        def get_status(self):
            return {
                'status': 'running',
                'current_stage': 'processing',
                'current_batch': 'test_batch_001',
                'metrics': {
                    'ingestion': {'items_processed': 100, 'duration_seconds': 2.5, 'success_rate': 1.0},
                    'processing': {'items_processed': 85, 'duration_seconds': 8.2, 'success_rate': 0.85},
                }
            }

        def get_healthy_nodes(self):
            return sum(1 for n in self.node_registry.nodes.values() if n.status == 'healthy')

        def get_unhealthy_nodes(self):
            return sum(1 for n in self.node_registry.nodes.values() if n.status != 'healthy')

    dashboard = StatusDashboard()
    orchestrator = MockOrchestrator(mock_registry)

    # Display dashboard
    dashboard.display_pipeline_status(orchestrator)

    print("\n")

    # Display node status
    dashboard.display_node_status(mock_registry)

    print("\n")

    # Display compact status
    dashboard.display_compact_status(orchestrator)

    print("\n")

    # Display progress bar
    for i in range(101):
        dashboard.display_progress_bar(i, 100, stage_name="Processing")
        time.sleep(0.02)

    print("\n")

    # Display throughput
    dashboard.display_throughput(1000, 5.5, unit="chunks")
