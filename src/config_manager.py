import json
import os

class ConfigManager:
    def __init__(self, config_file="config.json"):
        self.config_file = config_file
        
    def save_config(self, api_id, api_hash, group_id, proxy_config=None):
        """保存配置到文件"""
        config = {
            'api_id': api_id,
            'api_hash': api_hash,
            'group_id': group_id,
            'proxy_config': proxy_config
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(config, f)
            
    def load_config(self):
        """从文件加载配置"""
        if not os.path.exists(self.config_file):
            return None
            
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except Exception:
            return None 