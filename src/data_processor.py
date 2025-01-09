import pandas as pd
import sqlite3

class DataProcessor:
    def __init__(self, db_path):
        self.conn = sqlite3.connect(db_path)
        
    def process_messages(self, messages):
        df = pd.DataFrame(messages)
        
        # 基础统计
        stats = {
            'total_messages': len(df),
            'unique_users': df['sender'].nunique(),
            'media_count': df['media_type'].notna().sum(),
            'avg_views': df['views'].mean()
        }
        
        return df, stats
        
    def export_to_excel(self, df, output_path):
        with pd.ExcelWriter(output_path) as writer:
            df.to_excel(writer, sheet_name='Raw Data', index=False)
            self._write_stats_sheet(writer) 