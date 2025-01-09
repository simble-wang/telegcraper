from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                           QLabel, QLineEdit, QPushButton, QProgressBar,
                           QDateTimeEdit, QGroupBox, QTextEdit, QFileDialog, QDialog,
                           QSplitter, QListWidget, QListWidgetItem)
from PyQt6.QtCore import Qt, QDateTime, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap
import sys
import pandas as pd
from datetime import datetime
import asyncio
from src.crawler import TelegramCrawler
from src.config_manager import ConfigManager
from src.proxy_dialog import ProxyDialog
from src.auth_dialog import PhoneInputDialog, CodeInputDialog
from src.message_detail_dialog import MessageDetailDialog

class CrawlerThread(QThread):
    progress_updated = pyqtSignal(float, str)
    media_progress_updated = pyqtSignal(int, float, float, str, str, int, int)  # message_id, percentage, speed, media_type, filename, received, total
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    
    def __init__(self, api_id, api_hash, group_id, start_date, proxy_config=None, limit=None, resume=False):
        super().__init__()
        self.api_id = api_id
        self.api_hash = api_hash
        self.group_id = group_id
        self.start_date = start_date
        self.proxy_config = proxy_config
        self.limit = limit
        self.resume = resume
        
        # 创建爬虫实例
        try:
            api_id = int(self.api_id)
            self.crawler = TelegramCrawler(api_id, self.api_hash, proxy=self.proxy_config)
        except ValueError:
            self.error.emit("API ID 必须是数字")
        except Exception as e:
            self.error.emit(f"初始化错误: {str(e)}")
        
    def run(self):
        try:
            # 创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # 定义媒体下载进度回调
                def media_progress_callback(message_id, percentage, speed, media_type, filename, received, total):
                    self.media_progress_updated.emit(message_id, percentage, speed, media_type, filename, received, total)
                
                # 运行爬虫
                loop.run_until_complete(
                    self.crawler.start_crawling(
                        self.group_id,
                        self.start_date,
                        lambda p, m: self.progress_updated.emit(p, m),
                        media_progress_callback,  # 传递媒体下载进度回调
                        limit=self.limit,
                        resume=self.resume
                    )
                )
                
                # 获取结果
                self.finished.emit(self.crawler.get_messages())
                
            except Exception as e:
                self.error.emit(f"爬取过程出错: {str(e)}")
            finally:
                # 清理事件循环
                try:
                    # 取消所有待处理的任务
                    pending = asyncio.all_tasks(loop)
                    for task in pending:
                        task.cancel()
                        
                    # 运行直到所有任务完成
                    if pending:
                        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                        
                    loop.close()
                except Exception as e:
                    print(f"清理事件循环时出错: {str(e)}")
            
        except Exception as e:
            self.error.emit(f"运行错误: {str(e)}")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Telegram Group Crawler")
        self.setMinimumSize(800, 600)
        
        # 初始化配置管理器
        self.config_manager = ConfigManager()
        
        # 创建一个中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 设置中央部件的布局
        self.main_layout = QVBoxLayout(central_widget)
        
        # 配置区域
        self.setup_config_section()
        
        # 进度显示区域
        self.setup_progress_section()
        
        # 统计分析区域
        self.setup_analysis_section()
        
        # 操作按钮区域
        self.setup_action_section()
        
        # 加载保存的配置
        self.load_saved_config()
        
    def setup_config_section(self):
        config_group = QGroupBox("配置信息")
        config_layout = QVBoxLayout()
        
        # API配置
        api_layout = QHBoxLayout()
        self.api_id_input = QLineEdit()
        self.api_hash_input = QLineEdit()
        api_layout.addWidget(QLabel("API ID:"))
        api_layout.addWidget(self.api_id_input)
        api_layout.addWidget(QLabel("API Hash:"))
        api_layout.addWidget(self.api_hash_input)
        config_layout.addLayout(api_layout)
        
        # 群组ID配置
        group_layout = QHBoxLayout()
        self.group_id_input = QLineEdit()
        self.group_id_input.setPlaceholderText("输入群组ID (例如: -1001234567890)")
        group_layout.addWidget(QLabel("群组ID:"))
        group_layout.addWidget(self.group_id_input)
        config_layout.addLayout(group_layout)
        
        # 添加说明标签
        help_label = QLabel("注意: 超级群组ID通常以 -100 开头")
        help_label.setStyleSheet("color: gray; font-size: 10px;")
        config_layout.addWidget(help_label)
        
        # 消息数量限制
        limit_layout = QHBoxLayout()
        self.limit_input = QLineEdit()
        self.limit_input.setPlaceholderText("不填则爬取全部消息")
        limit_layout.addWidget(QLabel("爬取数量:"))
        limit_layout.addWidget(self.limit_input)
        config_layout.addLayout(limit_layout)
        
        # 时间选择
        time_layout = QHBoxLayout()
        self.start_time = QDateTimeEdit(QDateTime.currentDateTime())
        self.start_time.setCalendarPopup(True)  # 添加日历弹出功能
        time_layout.addWidget(QLabel("起始时间:"))
        time_layout.addWidget(self.start_time)
        time_layout.addWidget(QLabel("(将爬取此时间之前的消息)"))
        config_layout.addLayout(time_layout)
        
        config_group.setLayout(config_layout)
        self.main_layout.addWidget(config_group)

    def setup_progress_section(self):
        progress_group = QGroupBox("进度")
        progress_layout = QVBoxLayout()
        
        # 总体进度
        progress_label = QLabel("总体进度:")
        self.progress_bar = QProgressBar()
        progress_layout.addWidget(progress_label)
        progress_layout.addWidget(self.progress_bar)
        
        # 媒体下载进度
        media_progress_label = QLabel("媒体下载进度:")
        self.media_progress_bar = QProgressBar()
        progress_layout.addWidget(media_progress_label)
        progress_layout.addWidget(self.media_progress_bar)
        
        # 状态信息
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMaximumHeight(150)
        progress_layout.addWidget(self.status_text)
        
        progress_group.setLayout(progress_layout)
        self.main_layout.addWidget(progress_group)

    def setup_analysis_section(self):
        analysis_group = QGroupBox("统计分析")
        analysis_layout = QVBoxLayout()
        
        # 分割统计和预览
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧统计信息
        stats_widget = QWidget()
        stats_layout = QVBoxLayout(stats_widget)
        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)
        stats_layout.addWidget(self.stats_text)
        splitter.addWidget(stats_widget)
        
        # 右侧消息预览
        preview_widget = QWidget()
        preview_layout = QVBoxLayout(preview_widget)
        preview_label = QLabel("消息预览")
        self.message_list = QListWidget()
        self.message_list.itemClicked.connect(self.show_message_detail)
        preview_layout.addWidget(preview_label)
        preview_layout.addWidget(self.message_list)
        splitter.addWidget(preview_widget)
        
        analysis_layout.addWidget(splitter)
        analysis_group.setLayout(analysis_layout)
        self.main_layout.addWidget(analysis_group)

    def setup_action_section(self):
        action_layout = QHBoxLayout()
        
        # 代理设置按钮
        self.proxy_button = QPushButton("代理设置")
        self.proxy_button.clicked.connect(self.show_proxy_settings)
        action_layout.addWidget(self.proxy_button)
        
        # 开始采集按钮
        self.start_button = QPushButton("开始采集")
        self.start_button.clicked.connect(self.start_crawling)
        action_layout.addWidget(self.start_button)
        
        # 继续上次采集按钮
        self.resume_button = QPushButton("继续上次采集")
        self.resume_button.clicked.connect(lambda: self.start_crawling(resume=True))
        action_layout.addWidget(self.resume_button)
        
        # 导出按钮
        self.export_button = QPushButton("导出Excel")
        self.export_button.clicked.connect(self.export_data)
        self.export_button.setEnabled(False)
        action_layout.addWidget(self.export_button)
        
        self.main_layout.addLayout(action_layout)

    def start_crawling(self, resume=False):
        # 获取输入值
        api_id = self.api_id_input.text().strip()
        api_hash = self.api_hash_input.text().strip()
        group_id = self.group_id_input.text().strip()
        start_date = self.start_time.dateTime().toPyDateTime()
        
        # 获取消息数量限制
        limit_text = self.limit_input.text().strip()
        limit = None
        if limit_text:
            try:
                limit = int(limit_text)
                if limit <= 0:
                    self.status_text.setText("爬取数量必须大于0")
                    return
            except ValueError:
                self.status_text.setText("爬取数量必须是数字")
                return
        
        # 验证输入
        if not all([api_id, api_hash, group_id]):
            self.status_text.setText("请填写所有必要信息")
            return
            
        try:
            # 验证API ID是否为数字
            int(api_id)
        except ValueError:
            self.status_text.setText("API ID必须是数字")
            return
            
        # 创建并启动爬虫线程
        self.crawler_thread = CrawlerThread(
            api_id, api_hash, group_id, start_date, 
            proxy_config=getattr(self, 'proxy_config', None),
            limit=limit,
            resume=resume
        )
        
        # 连接所有信号
        self.crawler_thread.progress_updated.connect(self.update_progress)
        self.crawler_thread.media_progress_updated.connect(self.update_media_progress)
        self.crawler_thread.finished.connect(self.crawling_finished)
        self.crawler_thread.error.connect(self.crawling_error)
        
        # 禁用按钮
        self.start_button.setEnabled(False)
        self.export_button.setEnabled(False)
        
        # 启动线程
        self.crawler_thread.start()
        
    def update_progress(self, progress, message):
        self.progress_bar.setValue(int(progress))
        current_text = self.status_text.toPlainText()
        lines = current_text.split('\n')
        # 保持最多显示10行
        if len(lines) > 10:
            lines = lines[1:]
        lines.append(message)
        self.status_text.setText('\n'.join(lines))
        # 滚动到底部
        self.status_text.verticalScrollBar().setValue(
            self.status_text.verticalScrollBar().maximum()
        )

    def update_media_progress(self, message_id, percentage, speed, media_type, filename, received, total):
        """更新媒体下载进度"""
        self.media_progress_bar.setValue(int(percentage))
        
        # 格式化显示信息
        media_type_names = {
            'photo': '图片',
            'video': '视频',
            'audio': '音频',
            'document': '文档'
        }
        
        media_type_display = media_type_names.get(media_type, media_type)
        status = (
            f"正在下载{media_type_display}文件:\n"
            f"文件名: {filename}\n"
            f"进度: {percentage:.1f}% ({self.format_size(received)}/{self.format_size(total)})\n"
            f"速度: {speed:.1f} KB/s"
        )
        
        # 更新状态文本
        current_text = self.status_text.toPlainText()
        lines = current_text.split('\n')
        # 如果有超过4行的媒体下载信息，删除旧的
        if len(lines) > 4:
            lines = lines[:4]
        lines.append(status)
        self.status_text.setText('\n'.join(lines))
        self.status_text.verticalScrollBar().setValue(
            self.status_text.verticalScrollBar().maximum()
        )

    def format_size(self, size):
        """格式化文件大小显示"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def crawling_finished(self, messages):
        self.messages = messages
        self.status_text.setText("爬取完成!")
        self.start_button.setEnabled(True)
        self.export_button.setEnabled(True)
        
        # 显示统计信息
        self.show_statistics()
        
        # 更新消息预览
        self.message_list.clear()
        for msg in messages[:100]:  # 只显示前100条消息预览
            item = QListWidgetItem(
                f"[{msg['date'].strftime('%Y-%m-%d %H:%M')}] {msg['sender_name']}: "
                f"{msg['text'][:50]}{'...' if len(msg['text']) > 50 else ''}"
            )
            item.setData(Qt.ItemDataRole.UserRole, msg)
            self.message_list.addItem(item)
        
    def crawling_error(self, error_message):
        self.status_text.setText(f"错误: {error_message}")
        self.start_button.setEnabled(True)
        self.progress_bar.setValue(0)
        
        # 根据不同错误类型给出具体提示
        if "服务器错误" in error_message:
            self.status_text.append("\n服务器连接不稳定，请稍后重试")
        elif "连接Telegram失败" in error_message:
            self.status_text.append("\n请确保：\n1. 已开启代理服务\n2. 代理端口正确(默认3067)\n3. 网络连接稳定")
        elif "无法获取群组信息" in error_message:
            self.status_text.append("\n群组ID可以是：\n1. 数字ID\n2. 用户名(如 @groupname)\n3. 邀请链接(如 t.me/groupname)")
        elif "需要两步验证密码" in error_message:
            self.status_text.append("\n请先在Telegram客户端完成两步验证")

    def show_statistics(self):
        if not hasattr(self, 'messages'):
            return
            
        df = pd.DataFrame(self.messages)
        
        # 基础统计
        basic_stats = f"""基础统计:
        总消息数: {len(df)}
        发言人数: {df['sender_id'].nunique()}
        包含媒体消息数: {df['media_type'].notna().sum()}
        平均查看数: {df['views'].mean():.2f}
        """
        
        # 活跃用户统计
        top_users = df['sender_name'].value_counts().head(5)
        user_stats = "\n\n活跃用户 (Top 5):\n"
        for name, count in top_users.items():
            user_stats += f"{name}: {count}条消息\n"
        
        # 媒体类型统计
        if 'media_type' in df.columns:
            media_stats = df['media_type'].value_counts()
            media_text = "\n\n媒体类型统计:\n"
            for type_name, count in media_stats.items():
                if pd.notna(type_name):
                    media_text += f"{type_name}: {count}个\n"
        
        # 时间分布
        if 'date' in df.columns:
            df['hour'] = df['date'].apply(lambda x: x.hour)
            hour_stats = df['hour'].value_counts().sort_index()
            time_text = "\n\n消息时间分布 (小时):\n"
            max_count = hour_stats.max()
            for hour, count in hour_stats.items():
                bar_length = int((count / max_count) * 20)
                time_text += f"{hour:02d}时: {'█' * bar_length} ({count}条)\n"
        
        # 合并所有统计信息
        self.stats_text.setText(basic_stats + user_stats + media_text + time_text)

    def export_data(self):
        if not hasattr(self, 'messages'):
            self.status_text.setText("没有可导出的数据")
            return
            
        try:
            # 获取保存路径
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"telegram_messages_{timestamp}.xlsx"
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "保存Excel文件",
                default_filename,
                "Excel Files (*.xlsx)"
            )
            
            if not file_path:  # 用户取消了保存
                return
            
            # 创建DataFrame并处理时区
            df = pd.DataFrame(self.messages)
            
            # 处理日期时间格式
            if 'date' in df.columns:
                # 移除时区信息并格式化日期时间
                df['date'] = df['date'].apply(lambda x: x.replace(tzinfo=None).strftime('%Y年%m月%d日 %H:%M:%S'))
            
            # 写入Excel
            with pd.ExcelWriter(file_path) as writer:
                # 原始数据sheet
                df.to_excel(writer, sheet_name='消息数据', index=False)
                
                # 统计数据sheet
                stats_df = pd.DataFrame({
                    '统计项': [
                        '总消息数',
                        '发言人数',
                        '包含媒体消息数',
                        '平均查看数'
                    ],
                    '数值': [
                        len(df),
                        df['sender_id'].nunique(),
                        df['media_type'].notna().sum(),
                        f"{df['views'].mean():.2f}"
                    ]
                })
                stats_df.to_excel(writer, sheet_name='统计数据', index=False)
                
                # 发言人统计sheet
                sender_stats = df.groupby(['sender_id', 'sender_name']).agg({
                    'text': 'count',
                    'views': 'mean',
                    'media_type': lambda x: x.notna().sum()
                }).reset_index()
                sender_stats.columns = ['发言人ID', '发言人名称', '发言次数', '平均查看数', '媒体消息数']
                sender_stats = sender_stats.sort_values('发言次数', ascending=False)  # 按发言次数排序
                sender_stats.to_excel(writer, sheet_name='发言人统计', index=False)
            
            self.status_text.setText(f"数据已导出到: {file_path}")
            
        except Exception as e:
            self.status_text.setText(f"导出失败: {str(e)}") 

    def load_saved_config(self):
        """加载保存的配置"""
        config = self.config_manager.load_config()
        if config:
            self.api_id_input.setText(str(config['api_id']))
            self.api_hash_input.setText(config['api_hash'])
            self.group_id_input.setText(config['group_id'])
            
            # 加载代理配置
            if 'proxy_config' in config and config['proxy_config']:
                self.proxy_config = config['proxy_config']
                print("已加载代理配置")

    def save_current_config(self):
        """保存当前配置"""
        api_id = self.api_id_input.text().strip()
        api_hash = self.api_hash_input.text().strip()
        group_id = self.group_id_input.text().strip()
        
        if all([api_id, api_hash, group_id]):
            self.config_manager.save_config(
                api_id, 
                api_hash, 
                group_id,
                getattr(self, 'proxy_config', None)
            )
            print("配置已保存")

    def closeEvent(self, event):
        """窗口关闭时保存配置"""
        self.save_current_config()
        event.accept()

    def show_proxy_settings(self):
        """显示代理设置对话框"""
        dialog = ProxyDialog(self, getattr(self, 'proxy_config', None))
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.proxy_config = dialog.get_config()
            # 保存配置
            self.save_current_config()
            
    def show_message_detail(self, item):
        """显示消息详情"""
        message = item.data(Qt.ItemDataRole.UserRole)
        detail_dialog = MessageDetailDialog(message, self)
        detail_dialog.exec() 