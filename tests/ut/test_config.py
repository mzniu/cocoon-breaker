"""
Unit tests for config module
"""
import os
import pytest
import tempfile
import yaml
from pathlib import Path
from src.config import Config, get_config, reload_config


class TestConfig:
    """Test Config class"""
    
    def test_load_default_config(self):
        """Test loading with default values when no config file exists"""
        config = Config("nonexistent.yaml")
        
        # Check default values
        assert config.server.host == "127.0.0.1"
        assert config.server.port == 8000
        assert config.server.debug is False
        
        assert config.subscriptions.max_keywords == 5
        assert config.schedule.default_time == "08:00"
        assert config.output.format == "html"
        assert config.llm.provider == "deepseek"
        assert config.database.path == "./data/cocoon.db"
    
    def test_load_from_yaml_file(self):
        """Test loading configuration from YAML file"""
        # Create temporary config file
        config_data = {
            'server': {
                'host': '0.0.0.0',
                'port': 9000,
                'debug': True
            },
            'subscriptions': {
                'max_keywords': 10,
                'default_keywords': ['test1', 'test2']
            },
            'llm': {
                'provider': 'deepseek',
                'model': 'deepseek-reasoner',
                'timeout': 60
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as f:
            yaml.dump(config_data, f)
            temp_config_path = f.name
        
        try:
            config = Config(temp_config_path)
            
            # Verify loaded values
            assert config.server.host == '0.0.0.0'
            assert config.server.port == 9000
            assert config.server.debug is True
            
            assert config.subscriptions.max_keywords == 10
            assert config.subscriptions.default_keywords == ['test1', 'test2']
            
            assert config.llm.timeout == 60
            
        finally:
            os.unlink(temp_config_path)
    
    def test_environment_variable_substitution(self):
        """Test environment variable substitution in config"""
        # Set test environment variable
        test_api_key = "sk-test-12345"
        os.environ['TEST_DEEPSEEK_KEY'] = test_api_key
        
        config_data = {
            'llm': {
                'api_key': '${TEST_DEEPSEEK_KEY}'
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as f:
            yaml.dump(config_data, f)
            temp_config_path = f.name
        
        try:
            config = Config(temp_config_path)
            
            # Verify substitution
            assert config.llm.api_key == test_api_key
            
        finally:
            os.unlink(temp_config_path)
            del os.environ['TEST_DEEPSEEK_KEY']
    
    def test_missing_environment_variable(self):
        """Test behavior when environment variable is not set"""
        config_data = {
            'llm': {
                'api_key': '${MISSING_VAR}'
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as f:
            yaml.dump(config_data, f)
            temp_config_path = f.name
        
        try:
            config = Config(temp_config_path)
            
            # Should be empty string when env var not set
            assert config.llm.api_key == ''
            
        finally:
            os.unlink(temp_config_path)
    
    def test_nested_env_substitution(self):
        """Test environment variable substitution in nested structures"""
        os.environ['TEST_HOST'] = 'custom.host.com'
        os.environ['TEST_PORT'] = '8080'
        
        config_data = {
            'server': {
                'host': '${TEST_HOST}',
                'port': '${TEST_PORT}'
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as f:
            yaml.dump(config_data, f)
            temp_config_path = f.name
        
        try:
            config = Config(temp_config_path)
            
            assert config.server.host == 'custom.host.com'
            # Note: port is still string from YAML, needs type conversion in real usage
            
        finally:
            os.unlink(temp_config_path)
            del os.environ['TEST_HOST']
            del os.environ['TEST_PORT']
    
    def test_partial_config_with_defaults(self):
        """Test that partial config uses defaults for missing values"""
        config_data = {
            'server': {
                'port': 7000
            }
            # Other sections missing
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as f:
            yaml.dump(config_data, f)
            temp_config_path = f.name
        
        try:
            config = Config(temp_config_path)
            
            # Specified value
            assert config.server.port == 7000
            
            # Default values for unspecified
            assert config.server.host == "127.0.0.1"
            assert config.llm.provider == "deepseek"
            assert config.database.path == "./data/cocoon.db"
            
        finally:
            os.unlink(temp_config_path)


class TestConfigSingleton:
    """Test config singleton pattern"""
    
    def test_get_config_singleton(self):
        """Test that get_config returns the same instance"""
        config1 = get_config()
        config2 = get_config()
        
        assert config1 is config2
    
    def test_reload_config(self):
        """Test config reload functionality"""
        config1 = get_config()
        config2 = reload_config()
        
        # Should be different instance after reload
        assert config1 is not config2


class TestConfigDataClasses:
    """Test configuration dataclasses"""
    
    def test_all_dataclasses_initialized(self):
        """Test that all config sections are properly initialized"""
        config = Config("nonexistent.yaml")
        
        # Check all sections exist
        assert hasattr(config, 'server')
        assert hasattr(config, 'subscriptions')
        assert hasattr(config, 'schedule')
        assert hasattr(config, 'output')
        assert hasattr(config, 'llm')
        assert hasattr(config, 'crawler')
        assert hasattr(config, 'database')
        assert hasattr(config, 'logging')
        
        # Check crawler lists are initialized
        assert isinstance(config.crawler.sources, list)
        assert isinstance(config.crawler.user_agents, list)
        assert len(config.crawler.sources) > 0
        assert len(config.crawler.user_agents) > 0
