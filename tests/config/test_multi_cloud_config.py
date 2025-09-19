import unittest
import os
import yaml

from src.config.multi_cloud_config import ConfigurationManager, SystemConfig, CloudProviderConfig

class TestConfigurationManager(unittest.TestCase):

    def setUp(self):
        self.valid_config_path = 'tests/config/valid_config.yml'
        self.invalid_config_path = 'tests/config/invalid_config.yml'
        self.incomplete_config_path = 'tests/config/incomplete_config.yml'
        self.non_existent_config_path = 'tests/config/non_existent_config.yml'

    def test_load_configuration_success(self):
        """Test successful loading of a valid configuration file."""
        config_manager = ConfigurationManager(config_path=self.valid_config_path)
        self.assertIsInstance(config_manager.config, SystemConfig)
        self.assertEqual(config_manager.config.cluster_name, 'test_cluster')
        self.assertIn('aws', config_manager.config.cloud_providers)
        self.assertIsInstance(config_manager.config.cloud_providers['aws'], CloudProviderConfig)

    def test_load_configuration_file_not_found(self):
        """Test that FileNotFoundError is raised for a non-existent file."""
        with self.assertRaises(FileNotFoundError):
            ConfigurationManager(config_path=self.non_existent_config_path)

    def test_load_configuration_invalid_yaml(self):
        """Test that YAMLError is raised for a malformed YAML file."""
        with self.assertRaises(yaml.YAMLError):
            ConfigurationManager(config_path=self.invalid_config_path)

    def test_load_configuration_incomplete(self):
        """Test that ValueError is raised for a configuration with missing keys."""
        with self.assertRaises(ValueError):
            ConfigurationManager(config_path=self.incomplete_config_path)

if __name__ == '__main__':
    unittest.main()
