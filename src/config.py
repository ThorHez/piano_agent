"""
配置管理模块
"""
import yaml
from pathlib import Path
from typing import Dict, Any, List


class Config:
    """配置类"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config_path = Path(config_path)
        self._config: Dict[str, Any] = {}
        self.load()
    
    def load(self):
        """加载配置文件"""
        if not self.config_path.exists():
            print(f"⚠️  配置文件不存在: {self.config_path}，使用默认配置")
            self._load_default_config()
            return
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f) or {}
            print(f"✅ 已加载配置文件: {self.config_path}")
        except (FileNotFoundError, yaml.YAMLError, IOError) as e:
            print(f"❌ 加载配置文件失败: {e}，使用默认配置")
            self._load_default_config()
    
    def _load_default_config(self):
        """加载默认配置"""
        self._config = {
            'server': {
                'host': '0.0.0.0',
                'port': 8000,
                'reload': True,
                'workers': 1
            },
            'auth': {
                'enabled': False,
                'secret_key': 'your-secret-key-here-change-in-production',
                'algorithm': 'HS256',
                'access_token_expire_minutes': 30
            },
            'cors': {
                'allow_origins': ['*'],
                'allow_credentials': True,
                'allow_methods': ['*'],
                'allow_headers': ['*']
            },
            'performance': {
                'default_tempo': 120,
                'min_tempo': 20,
                'max_tempo': 240,
                'stream_buffer_size': 100
            },
            'logging': {
                'level': 'INFO',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值，支持点号分隔的路径"""
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        
        return value
    
    @property
    def server_host(self) -> str:
        return self.get('server.host', '0.0.0.0')
    
    @property
    def server_port(self) -> int:
        return self.get('server.port', 8000)
    
    @property
    def server_reload(self) -> bool:
        return self.get('server.reload', True)
    
    @property
    def server_workers(self) -> int:
        return self.get('server.workers', 1)
    
    @property
    def auth_enabled(self) -> bool:
        return self.get('auth.enabled', False)
    
    @property
    def auth_secret_key(self) -> str:
        return self.get('auth.secret_key', 'your-secret-key-here')
    
    @property
    def auth_algorithm(self) -> str:
        return self.get('auth.algorithm', 'HS256')
    
    @property
    def cors_origins(self) -> List[str]:
        return self.get('cors.allow_origins', ['*'])
    
    @property
    def cors_credentials(self) -> bool:
        return self.get('cors.allow_credentials', True)
    
    @property
    def log_level(self) -> str:
        return self.get('logging.level', 'INFO')

    @property
    def nx_host(self) -> str:
        return self.get('nx.host', '192.168.1.100')
    
    @property
    def nx_user(self) -> str:
        return self.get('nx.user', 'ubuntu')
    
    @property
    def nx_password(self) -> str:
        return self.get('nx.password', 'your_password')

    @property
    def voice_url(self) -> str:
        return self.get('voice.url', 'http://192.168.3.24:9331/voice/stream')

    @property
    def performance_stream_url(self) -> str:
        return self.get('performance.stream_url', 'http://192.168.3.24:5000/play_stream')

    @property
    def performance_record_url(self) -> str:
        return self.get('performance.record_url', 'http://localhost:8123/record')

    @property
    def music_download_url(self) -> str:
        return self.get('music.download_url', 'http://192.168.100.51:8080/download/music')


# 全局配置实例
config = Config()

