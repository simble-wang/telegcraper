from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                           QLineEdit, QPushButton, QComboBox)
from PyQt6.QtCore import Qt
import socks

class ProxyDialog(QDialog):
    def __init__(self, parent=None, current_config=None):
        super().__init__(parent)
        self.setWindowTitle("代理设置")
        self.setModal(True)
        
        # 默认配置
        self.default_config = {
            'proxy_type': socks.SOCKS5,
            'addr': '127.0.0.1',
            'port': 3067,
            'rdns': True
        }
        
        # 使用当前配置或默认配置
        self.current_config = current_config or self.default_config.copy()
        
        # 设置布局
        layout = QVBoxLayout(self)
        
        # 代理类型选择
        type_layout = QHBoxLayout()
        self.proxy_type = QComboBox()
        self.proxy_type.addItems(['SOCKS5', 'SOCKS4', 'HTTP'])
        type_layout.addWidget(QLabel("代理类型:"))
        type_layout.addWidget(self.proxy_type)
        layout.addLayout(type_layout)
        
        # 代理地址
        addr_layout = QHBoxLayout()
        self.addr_input = QLineEdit()
        addr_layout.addWidget(QLabel("代理地址:"))
        addr_layout.addWidget(self.addr_input)
        layout.addLayout(addr_layout)
        
        # 代理端口
        port_layout = QHBoxLayout()
        self.port_input = QLineEdit()
        port_layout.addWidget(QLabel("代理端口:"))
        port_layout.addWidget(self.port_input)
        layout.addLayout(port_layout)
        
        # 按钮
        button_layout = QHBoxLayout()
        self.save_button = QPushButton("保存")
        self.cancel_button = QPushButton("取消")
        self.reset_button = QPushButton("重置默认")
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.reset_button)
        layout.addLayout(button_layout)
        
        # 连接信号
        self.save_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        self.reset_button.clicked.connect(self.reset_to_default)
        
        # 初始化值
        self.load_current_config()
        
    def load_current_config(self):
        """加载当前配置"""
        # 设置代理类型
        proxy_type_map = {
            socks.SOCKS5: 'SOCKS5',
            socks.SOCKS4: 'SOCKS4',
            socks.HTTP: 'HTTP'
        }
        self.proxy_type.setCurrentText(
            proxy_type_map.get(self.current_config['proxy_type'], 'SOCKS5')
        )
        
        # 设置地址和端口
        self.addr_input.setText(self.current_config['addr'])
        self.port_input.setText(str(self.current_config['port']))
        
    def reset_to_default(self):
        """重置为默认配置"""
        self.current_config = self.default_config.copy()
        self.load_current_config()
        
    def get_config(self):
        """获取当前配置"""
        proxy_type_map = {
            'SOCKS5': socks.SOCKS5,
            'SOCKS4': socks.SOCKS4,
            'HTTP': socks.HTTP
        }
        
        return {
            'proxy_type': proxy_type_map[self.proxy_type.currentText()],
            'addr': self.addr_input.text(),
            'port': int(self.port_input.text()),
            'rdns': True
        } 