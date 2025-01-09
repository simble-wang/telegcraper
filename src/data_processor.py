import json
import os
from datetime import datetime
import pandas as pd

class DataProcessor:
    def __init__(self, save_dir="data"):
        self.save_dir = save_dir
        self.ensure_save_dir()
        
    def ensure_save_dir(self):
        """确保保存目录存在"""
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)
            
    def save_progress(self, group_id, messages, last_message_id=None, start_date=None):
        """保存爬取进度和数据"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        progress_file = os.path.join(self.save_dir, f"progress_{group_id}.json")
        data_file = os.path.join(self.save_dir, f"messages_{group_id}_{timestamp}.json")
        
        # 保存进度信息
        progress_info = {
            'group_id': group_id,
            'last_message_id': last_message_id,
            'start_date': start_date.isoformat() if start_date else None,
            'message_count': len(messages),
            'last_update': timestamp,
            'data_file': data_file
        }
        
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump(progress_info, f, ensure_ascii=False, indent=2)
            
        # 保存消息数据
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(messages, f, ensure_ascii=False, indent=2)
            
    def load_progress(self, group_id):
        """加载上次的爬取进度"""
        progress_file = os.path.join(self.save_dir, f"progress_{group_id}.json")
        
        if not os.path.exists(progress_file):
            return None
            
        try:
            with open(progress_file, 'r', encoding='utf-8') as f:
                progress_info = json.load(f)
                
            # 加载消息数据
            if os.path.exists(progress_info['data_file']):
                with open(progress_info['data_file'], 'r', encoding='utf-8') as f:
                    messages = json.load(f)
                return progress_info, messages
            
        except Exception as e:
            print(f"加载进度失败: {str(e)}")
        return None
        
    def merge_messages(self, old_messages, new_messages):
        """合并新旧消息数据"""
        # 使用消息ID作为唯一标识
        message_dict = {msg['id']: msg for msg in old_messages}
        
        # 添加新消息
        for msg in new_messages:
            if msg['id'] not in message_dict:
                message_dict[msg['id']] = msg
                
        # 转换回列表并按时间排序
        merged = list(message_dict.values())
        merged.sort(key=lambda x: x['date'])
        return merged 