import unittest
from unittest.mock import patch, MagicMock
import os

from src.auth.cloud_auth_manager import UnifiedAuthManager

class TestUnifiedAuthManager(unittest.TestCase):

    def setUp(self):
        """Set up a new UnifiedAuthManager for each test."""
        self.auth_manager = UnifiedAuthManager()

    def test_initialization(self):
        """Test that the UnifiedAuthManager initializes correctly."""
        self.assertIsInstance(self.auth_manager, UnifiedAuthManager)
        self.assertEqual(self.auth_manager.credentials, {})
        self.assertEqual(self.auth_manager.clients, {})
        self.assertEqual(self.auth_manager.failure_log, [])

    @patch('boto3.Session')
    def test_setup_aws_credentials_success(self, mock_boto3_session):
        """Test successful AWS credential setup."""
        # Mock the boto3 session and client
        mock_session_instance = MagicMock()
        mock_sts_client = MagicMock()
        mock_sts_client.get_caller_identity.return_value = {
            'UserId': 'test-user',
            'Account': 'test-account',
            'Arn': 'arn:aws:iam::test-account:user/test-user'
        }
        mock_session_instance.client.return_value = mock_sts_client
        mock_boto3_session.return_value = mock_session_instance

        result = self.auth_manager.setup_aws_credentials()

        self.assertTrue(result)
        self.assertIn('aws', self.auth_manager.credentials)
        self.assertEqual(self.auth_manager.credentials['aws'].provider, 'aws')
        self.assertEqual(len(self.auth_manager.failure_log), 0)

    @patch('boto3.Session', side_effect=Exception("AWS auth error"))
    def test_setup_aws_credentials_failure(self, mock_boto3_session):
        """Test failed AWS credential setup."""
        result = self.auth_manager.setup_aws_credentials()

        self.assertFalse(result)
        self.assertNotIn('aws', self.auth_manager.credentials)
        self.assertEqual(len(self.auth_manager.failure_log), 1)
        failure = self.auth_manager.failure_log[0]
        self.assertEqual(failure['type'], 'AWS_AUTH_FAILED')
        self.assertEqual(failure['details'], 'AWS auth error')

    @patch('google.oauth2.service_account.Credentials.from_service_account_file')
    @patch.dict(os.environ, {'GOOGLE_APPLICATION_CREDENTIALS': 'fake_path.json'})
    def test_setup_gcp_credentials_success(self, mock_from_service_account_file):
        """Test successful GCP credential setup."""
        mock_credentials = MagicMock()
        mock_from_service_account_file.return_value = mock_credentials

        result = self.auth_manager.setup_gcp_credentials()

        self.assertTrue(result)
        self.assertIn('gcp', self.auth_manager.credentials)
        self.assertEqual(self.auth_manager.credentials['gcp'].provider, 'gcp')
        self.assertEqual(len(self.auth_manager.failure_log), 0)

    @patch('google.oauth2.service_account.Credentials.from_service_account_file', side_effect=Exception("GCP auth error"))
    @patch.dict(os.environ, {'GOOGLE_APPLICATION_CREDENTIALS': 'fake_path.json'})
    def test_setup_gcp_credentials_failure(self, mock_from_service_account_file):
        """Test failed GCP credential setup."""
        result = self.auth_manager.setup_gcp_credentials()

        self.assertFalse(result)
        self.assertNotIn('gcp', self.auth_manager.credentials)
        self.assertEqual(len(self.auth_manager.failure_log), 1)
        failure = self.auth_manager.failure_log[0]
        self.assertEqual(failure['type'], 'GCP_AUTH_FAILED')
        self.assertEqual(failure['details'], 'GCP auth error')

if __name__ == '__main__':
    unittest.main()
