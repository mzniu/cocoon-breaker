"""
Configuration management module.
Loads configuration from YAML file and supports environment variable overrides.
"""
import os
import re
import yaml
from pathlib import Path
from typing import Any, Dict
from dataclasses import dataclass


@dataclass
class ServerConfig:
    """Server configuration"""
    host: str = "127.0.0.1"
    port: int = 8000
    debug: bool = False


@dataclass
class SubscriptionConfig:
    """Subscription configuration"""
    max_keywords: int = 5
    default_keywords: list[str] = None


@dataclass
class ScheduleConfig:
    """Schedule configuration"""
    default_time: str = "08:00"
    enabled: bool = True


@dataclass
class OutputConfig:
    """Output configuration"""
    format: str = "html"
    directory: str = "./reports"
    template: str = "./templates/report.html"


@dataclass
class LLMConfig:
    """LLM configuration"""
    provider: str = "deepseek"
    api_key: str = ""
    model: str = "deepseek-reasoner"
    base_url: str = "https://api.deepseek.com"
    timeout: int = 30
    max_retries: int = 3


@dataclass
class CrawlerConfig:
    """Crawler configuration"""
    sources: list[str] = None
    request_interval: list[int] = None
    max_results_per_keyword: int = 20
    timeout: int = 10
    user_agents: list[str] = None


@dataclass
class GoogleConfig:
    """Google Custom Search API configuration"""
    api_key: str = ""
    search_engine_id: str = ""
    enabled: bool = True


@dataclass
class TavilyConfig:
    """Tavily API configuration"""
    api_key: str = ""
    enabled: bool = False
    search_depth: str = "advanced"
    max_results: int = 20


@dataclass
class DatabaseConfig:
    """Database configuration"""
    path: str = "./data/cocoon.db"


@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = "INFO"
    format: str = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
    file: str = "./logs/cocoon.log"
    max_bytes: int = 10485760
    backup_count: int = 5


class Config:
    """Application configuration"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self._raw_config: Dict[str, Any] = {}
        
        # Initialize configurations
        self.server = ServerConfig()
        self.subscriptions = SubscriptionConfig(default_keywords=[])
        self.schedule = ScheduleConfig()
        self.output = OutputConfig()
        self.llm = LLMConfig()
        self.crawler = CrawlerConfig(
            sources=["baidu", "bing"],
            request_interval=[1, 3],
            user_agents=[
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            ]
        )
        self.google = GoogleConfig()
        self.tavily = TavilyConfig()
        self.database = DatabaseConfig()
        self.logging = LoggingConfig()
        
        # Load configuration
        self.load()
    
    def load(self):
        """Load configuration from YAML file"""
        config_file = Path(self.config_path)
        
        if not config_file.exists():
            print(f"Warning: Config file {self.config_path} not found, using defaults")
            return
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                self._raw_config = yaml.safe_load(f) or {}
            
            # Process environment variable substitution
            self._raw_config = self._substitute_env_vars(self._raw_config)
            
            # Load each section
            self._load_server()
            self._load_subscriptions()
            self._load_schedule()
            self._load_output()
            self._load_llm()
            self._load_crawler()
            self._load_google()
            self._load_tavily()
            self._load_database()
            self._load_logging()
            
        except Exception as e:
            print(f"Error loading config: {e}")
            raise
    
    def _substitute_env_vars(self, config: Any) -> Any:
        """
        Recursively substitute environment variables in config.
        Supports ${VAR_NAME} format.
        """
        if isinstance(config, dict):
            return {k: self._substitute_env_vars(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._substitute_env_vars(item) for item in config]
        elif isinstance(config, str):
            # Match ${VAR_NAME} pattern
            pattern = r'\$\{([A-Z_][A-Z0-9_]*)\}'
            matches = re.findall(pattern, config)
            
            for var_name in matches:
                env_value = os.getenv(var_name, '')
                if not env_value:
                    print(f"Warning: Environment variable {var_name} not set")
                config = config.replace(f'${{{var_name}}}', env_value)
            
            return config
        else:
            return config
    
    def _load_server(self):
        """Load server configuration"""
        if 'server' in self._raw_config:
            cfg = self._raw_config['server']
            self.server.host = cfg.get('host', self.server.host)
            self.server.port = cfg.get('port', self.server.port)
            self.server.debug = cfg.get('debug', self.server.debug)
    
    def _load_subscriptions(self):
        """Load subscriptions configuration"""
        if 'subscriptions' in self._raw_config:
            cfg = self._raw_config['subscriptions']
            self.subscriptions.max_keywords = cfg.get('max_keywords', self.subscriptions.max_keywords)
            self.subscriptions.default_keywords = cfg.get('default_keywords', self.subscriptions.default_keywords)
    
    def _load_schedule(self):
        """Load schedule configuration"""
        if 'schedule' in self._raw_config:
            cfg = self._raw_config['schedule']
            self.schedule.default_time = cfg.get('default_time', self.schedule.default_time)
            self.schedule.enabled = cfg.get('enabled', self.schedule.enabled)
    
    def _load_output(self):
        """Load output configuration"""
        if 'output' in self._raw_config:
            cfg = self._raw_config['output']
            self.output.format = cfg.get('format', self.output.format)
            self.output.directory = cfg.get('directory', self.output.directory)
            self.output.template = cfg.get('template', self.output.template)
    
    def _load_llm(self):
        """Load LLM configuration"""
        if 'llm' in self._raw_config:
            cfg = self._raw_config['llm']
            self.llm.provider = cfg.get('provider', self.llm.provider)
            self.llm.api_key = cfg.get('api_key', self.llm.api_key)
            self.llm.model = cfg.get('model', self.llm.model)
            self.llm.base_url = cfg.get('base_url', self.llm.base_url)
            self.llm.timeout = cfg.get('timeout', self.llm.timeout)
            self.llm.max_retries = cfg.get('max_retries', self.llm.max_retries)
    
    def _load_crawler(self):
        """Load crawler configuration"""
        if 'crawler' in self._raw_config:
            cfg = self._raw_config['crawler']
            self.crawler.sources = cfg.get('sources', self.crawler.sources)
            self.crawler.request_interval = cfg.get('request_interval', self.crawler.request_interval)
            self.crawler.max_results_per_keyword = cfg.get('max_results_per_keyword', 
                                                            self.crawler.max_results_per_keyword)
            self.crawler.timeout = cfg.get('timeout', self.crawler.timeout)
            self.crawler.user_agents = cfg.get('user_agents', self.crawler.user_agents)
    
    def _load_google(self):
        """Load Google API configuration"""
        if 'google' in self._raw_config:
            cfg = self._raw_config['google']
            self.google.api_key = cfg.get('api_key', self.google.api_key)
            self.google.search_engine_id = cfg.get('search_engine_id', self.google.search_engine_id)
            self.google.enabled = cfg.get('enabled', self.google.enabled)
    
    def _load_tavily(self):
        """Load Tavily API configuration"""
        if 'tavily' in self._raw_config:
            cfg = self._raw_config['tavily']
            self.tavily.api_key = cfg.get('api_key', self.tavily.api_key)
            self.tavily.enabled = cfg.get('enabled', self.tavily.enabled)
            self.tavily.search_depth = cfg.get('search_depth', self.tavily.search_depth)
            self.tavily.max_results = cfg.get('max_results', self.tavily.max_results)
    
    def _load_database(self):
        """Load database configuration"""
        if 'database' in self._raw_config:
            cfg = self._raw_config['database']
            self.database.path = cfg.get('path', self.database.path)
    
    def _load_logging(self):
        """Load logging configuration"""
        if 'logging' in self._raw_config:
            cfg = self._raw_config['logging']
            self.logging.level = cfg.get('level', self.logging.level)
            self.logging.format = cfg.get('format', self.logging.format)
            self.logging.file = cfg.get('file', self.logging.file)
            self.logging.max_bytes = cfg.get('max_bytes', self.logging.max_bytes)
            self.logging.backup_count = cfg.get('backup_count', self.logging.backup_count)


# Global config instance
_config_instance: Config = None


def get_config(config_path: str = "config.yaml") -> Config:
    """Get global config instance (singleton)"""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config(config_path)
    return _config_instance


def reload_config(config_path: str = "config.yaml"):
    """Reload configuration"""
    global _config_instance
    _config_instance = Config(config_path)
    return _config_instance
