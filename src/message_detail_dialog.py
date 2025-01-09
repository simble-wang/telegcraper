from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QTextEdit,
    QPushButton,
    QLabel
)
from PyQt6.QtCore import Qt

class MessageDetailDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("消息详情")
        self.setMinimumSize(400, 300)
        
        # 创建布局
        layout = QVBoxLayout()
        
        # 消息内容显示区域
        self.content_text = QTextEdit()
        self.content_text.setReadOnly(True)
        
        # 关闭按钮
        close_button = QPushButton("关闭")
        close_button.clicked.connect(self.close)
        
        # 添加组件到布局
        layout.addWidget(QLabel("消息内容："))
        layout.addWidget(self.content_text)
        layout.addWidget(close_button)
        
        self.setLayout(layout)
    
    def set_message_content(self, content):
        """设置消息内容"""
        self.content_text.setText(content) 