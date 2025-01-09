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
        
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            print("配置已保存")
        except Exception as e:
            print(f"保存配置失败: {str(e)}")
            
    def load_config(self):
        """从文件加载配置"""
        if not os.path.exists(self.config_file):
            return None
            
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
            # 确保所有必要的字段都存在
            required_fields = ['api_id', 'api_hash', 'group_id']
            if all(field in config for field in required_fields):
                return config
                
        except Exception as e:
            print(f"加载配置失败: {str(e)}")
        return None 