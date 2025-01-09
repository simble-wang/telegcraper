import os
import json
import hashlib
from datetime import datetime

class DownloadManager:
    def __init__(self, download_path="downloads"):
        self.download_path = download_path
        self.record_file = os.path.join(download_path, "download_records.json")
        self.download_records = self._load_records()
        
    def _load_records(self):
        """加载下载记录"""
        if os.path.exists(self.record_file):
            try:
                with open(self.record_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
        
    def _save_records(self):
        """保存下载记录"""
        os.makedirs(self.download_path, exist_ok=True)
        with open(self.record_file, 'w', encoding='utf-8') as f:
            json.dump(self.download_records, f, ensure_ascii=False, indent=2)
            
    def generate_file_id(self, message_id, media_type, file_size):
        """生成文件唯一标识"""
        content = f"{message_id}_{media_type}_{file_size}"
        return hashlib.md5(content.encode()).hexdigest()
        
    def get_file_path(self, file_id, original_name):
        """获取文件保存路径"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if original_name:
            filename = f"{timestamp}_{file_id}_{original_name}"
        else:
            filename = f"{timestamp}_{file_id}"
        
        # 清理文件名
        safe_filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '.'))
        return os.path.join(self.download_path, safe_filename)
        
    def is_file_completed(self, file_id, file_size):
        """检查文件是否已完整下载"""
        if file_id not in self.download_records:
            return False
            
        record = self.download_records[file_id]
        file_path = record['file_path']
        
        if not os.path.exists(file_path):
            del self.download_records[file_id]
            self._save_records()
            return False
            
        if os.path.getsize(file_path) != file_size:
            return False
            
        return True
        
    def add_download_record(self, file_id, file_path, file_size):
        """添加下载记录"""
        self.download_records[file_id] = {
            'file_path': file_path,
            'file_size': file_size,
            'download_time': datetime.now().isoformat()
        }
        self._save_records()
        
    def remove_download_record(self, file_id):
        """删除下载记录"""
        if file_id in self.download_records:
            file_path = self.download_records[file_id]['file_path']
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except:
                    pass
            del self.download_records[file_id]
            self._save_records() 