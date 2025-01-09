from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                           QTextEdit, QPushButton)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
import os

class MessageDetailDialog(QDialog):
    def __init__(self, message, parent=None):
        super().__init__(parent)
        self.setWindowTitle("消息详情")
        self.setMinimumSize(500, 400)
        
        layout = QVBoxLayout(self)
        
        # 基本信息
        info_layout = QHBoxLayout()
        info_layout.addWidget(QLabel(f"发送者: {message['sender_name']}"))
        info_layout.addWidget(QLabel(f"时间: {message['date'].strftime('%Y年%m月%d日 %H:%M:%S')}"))
        info_layout.addWidget(QLabel(f"查看数: {message['views']}"))
        layout.addLayout(info_layout)
        
        # 消息内容
        content_label = QLabel("消息内容:")
        layout.addWidget(content_label)
        
        content = QTextEdit()
        content.setPlainText(message['text'])
        content.setReadOnly(True)
        layout.addWidget(content)
        
        # 如果有媒体文件
        if message['media_type']:
            media_label = QLabel(f"媒体类型: {message['media_type']}")
            layout.addWidget(media_label)
            
            if message['media_path'] and os.path.exists(message['media_path']):
                if message['media_type'] == 'photo':
                    media_preview = QLabel()
                    pixmap = QPixmap(message['media_path'])
                    scaled_pixmap = pixmap.scaled(400, 300, Qt.AspectRatioMode.KeepAspectRatio)
                    media_preview.setPixmap(scaled_pixmap)
                    layout.addWidget(media_preview)
                else:
                    media_path = QLabel(f"媒体文件路径: {message['media_path']}")
                    layout.addWidget(media_path)
        
        # 关闭按钮
        close_button = QPushButton("关闭")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button) 