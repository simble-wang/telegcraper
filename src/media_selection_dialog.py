from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, 
                           QTableWidgetItem, QPushButton, QHeaderView, QCheckBox,
                           QLabel, QProgressBar)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
import os

class MediaSelectionDialog(QDialog):
    download_requested = pyqtSignal(list)  # 发送选中的媒体列表

    def __init__(self, media_items, parent=None):
        super().__init__(parent)
        self.setWindowTitle("选择要下载的媒体文件")
        self.setMinimumSize(800, 600)
        self.media_items = media_items
        
        # 创建布局
        layout = QVBoxLayout(self)
        
        # 创建表格
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "选择", "类型", "文件名", "大小", "发送者", "发送时间"
        ])
        
        # 设置表格列宽
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        
        self.populate_table()
        layout.addWidget(self.table)
        
        # 添加按钮
        button_layout = QHBoxLayout()
        
        self.select_all_btn = QPushButton("全选")
        self.select_all_btn.clicked.connect(self.toggle_select_all)
        button_layout.addWidget(self.select_all_btn)
        
        self.download_btn = QPushButton("下载选中文件")
        self.download_btn.clicked.connect(self.start_download)
        button_layout.addWidget(self.download_btn)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        
        # 下载进度部分
        self.progress_layout = QVBoxLayout()
        self.progress_label = QLabel()
        self.progress_bar = QProgressBar()
        self.progress_layout.addWidget(self.progress_label)
        self.progress_layout.addWidget(self.progress_bar)
        self.progress_layout.setVisible(False)
        layout.addLayout(self.progress_layout)
        
    def format_size(self, size):
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
        
    def populate_table(self):
        """填充表格数据"""
        self.table.setRowCount(len(self.media_items))
        for row, item in enumerate(self.media_items):
            # 添加复选框
            checkbox = QCheckBox()
            self.table.setCellWidget(row, 0, checkbox)
            
            # 填充其他列
            self.table.setItem(row, 1, QTableWidgetItem(item['media_type']))
            self.table.setItem(row, 2, QTableWidgetItem(item['filename']))
            self.table.setItem(row, 3, QTableWidgetItem(self.format_size(item['size'])))
            self.table.setItem(row, 4, QTableWidgetItem(item['sender_name']))
            self.table.setItem(row, 5, QTableWidgetItem(
                item['date'].strftime('%Y-%m-%d %H:%M:%S')
            ))
            
    def toggle_select_all(self):
        """切换全选状态"""
        is_checked = self.select_all_btn.text() == "全选"
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 0)
            checkbox.setChecked(is_checked)
        self.select_all_btn.setText("取消全选" if is_checked else "全选")
        
    def start_download(self):
        """开始下载选中的文件"""
        selected_items = []
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 0)
            if checkbox.isChecked():
                selected_items.append(self.media_items[row])
                
        if selected_items:
            self.download_requested.emit(selected_items)
            self.accept()
        
    def update_progress(self, current, total, filename):
        """更新下载进度"""
        self.progress_layout.setVisible(True)
        self.progress_label.setText(f"正在下载: {filename}")
        self.progress_bar.setValue(int((current / total) * 100)) 