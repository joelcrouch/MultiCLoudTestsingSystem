from dataclasses import dataclass
from typing import Dict, List
import yaml
import os
from datetime import datetime

@dataclass
class CloudProviderConfig:
    name: str
    region: str
    instance_type: str
    max_nodes: int
    api_rate_limit: int
    network_timeout_base: float

@dataclass
class SystemConfig:
    cluster_name: str
    cloud_providers: Dict[str, CloudProviderConfig]
    heartbeat_interval: float
    failure_detection_threshold: int
    replication_factor: int

class ConfigurationManager:
    def __init__(self, config_path: str = 'config/multi_cloud.yml'):
        self.config_path = config_path
        self.failure_log: List[Dict] = []
        self.config: SystemConfig = self.load_configuration()

    def load_configuration(self) -> SystemConfig:
        """Load configuration with validation"""
        try:
            with open(self.config_path, 'r') as f:
                config_data = yaml.safe_load(f)
            return self.validate_configuration(config_data)
        except FileNotFoundError as e:
            self.log_config_failure('CONFIG_FILE_NOT_FOUND', str(e))
            raise e
        except yaml.YAMLError as e:
            self.log_config_failure('CONFIG_YAML_ERROR', str(e))
            raise e

    def validate_configuration(self, config_data: Dict) -> SystemConfig:
        """Validate the structure and types of the configuration data."""
        # Basic validation, can be expanded with a schema library like Pydantic
        required_keys = ['cluster_name', 'cloud_providers', 'heartbeat_interval', 'failure_detection_threshold', 'replication_factor']
        for key in required_keys:
            if key not in config_data:
                raise ValueError(f"Missing required configuration key: {key}")
        
        provider_configs = {}
        for name, pc in config_data['cloud_providers'].items():
            provider_configs[name] = CloudProviderConfig(**pc)

        return SystemConfig(
            cluster_name=config_data['cluster_name'],
            cloud_providers=provider_configs,
            heartbeat_interval=config_data['heartbeat_interval'],
            failure_detection_threshold=config_data['failure_detection_threshold'],
            replication_factor=config_data['replication_factor']
        )

    def log_config_failure(self, failure_type: str, details: str):
        """Log configuration-related failures."""
        self.failure_log.append({
            'timestamp': datetime.now(),
            'type': failure_type,
            'details': details,
            'sprint': 1,
            'component': 'configuration'
        })
