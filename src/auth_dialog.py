from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                           QLineEdit, QPushButton)

class PhoneInputDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Telegram 验证")
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        # 电话号码输入
        phone_layout = QHBoxLayout()
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("+8613800138000")
        phone_layout.addWidget(QLabel("请输入电话号码:"))
        phone_layout.addWidget(self.phone_input)
        layout.addLayout(phone_layout)
        
        # 按钮
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("确定")
        self.cancel_button = QPushButton("取消")
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
        
        # 连接信号
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

class CodeInputDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("验证码")
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        # 验证码输入
        code_layout = QHBoxLayout()
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("12345")
        code_layout.addWidget(QLabel("请输入验证码:"))
        code_layout.addWidget(self.code_input)
        layout.addLayout(code_layout)
        
        # 按钮
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("确定")
        self.cancel_button = QPushButton("取消")
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
        
        # 连接信号
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject) 