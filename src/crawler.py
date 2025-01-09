from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError, SessionPasswordNeededError, ServerError
from telethon.tl.types import InputPeerChannel, InputPeerChat, PeerChannel
from telethon.network import ConnectionTcpFull
import asyncio
import pandas as pd
import os
from datetime import datetime, timezone
import socks
import time
from src.data_processor import DataProcessor
from src.download_manager import DownloadManager

class TelegramCrawler:
    def __init__(self, api_id, api_hash, download_path="downloads", proxy=None):
        self.api_id = api_id
        self.api_hash = api_hash
        self.download_path = download_path
        self.ensure_download_path()
        self.client = None
        self.proxy = proxy or {
            'proxy_type': socks.SOCKS5,
            'addr': '127.0.0.1',
            'port': 3067,
            'rdns': True
        }
        self.phone_code_callback = None
        self.password_callback = None
        self.max_retries = 3  # 最大重试次数
        self.retry_delay = 5  # 重试延迟（秒）
        self.users_cache = {}  # 添加用户信息缓存
        self.data_processor = DataProcessor()
        self.download_manager = DownloadManager(download_path)
        
    def ensure_download_path(self):
        """确保下载目录存在"""
        if not os.path.exists(self.download_path):
            os.makedirs(self.download_path)
            
    def _get_media_type(self, message):
        """获取消息中的媒体类型"""
        if message.photo:
            return 'photo'
        elif message.video:
            return 'video'
        elif message.document:
            return 'document'
        elif message.audio:
            return 'audio'
        return None
        
    async def _download_media_with_retry(self, message, max_retries=3):
        """带重试机制的媒体下载"""
        for attempt in range(max_retries):
            try:
                return await self._download_media(message)
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"下载失败，{attempt + 1}/{max_retries} 次尝试: {str(e)}")
                    await asyncio.sleep(2 * (attempt + 1))  # 指数退避
                else:
                    print(f"下载失败，已达到最大重试次数: {str(e)}")
                    return None

    async def _download_media(self, message):
        """下载媒体文件"""
        if not message.media:
            return None
            
        try:
            # 获取媒体信息
            media_type = self._get_media_type(message)
            file_size = 0
            
            if hasattr(message.media, 'document'):
                file_size = message.media.document.size
            elif hasattr(message.media, 'photo'):
                sizes = message.media.photo.sizes
                largest_size = max(sizes, key=lambda x: getattr(x, 'size', 0) if hasattr(x, 'size') else 0)
                file_size = getattr(largest_size, 'size', 0)
                
            # 生成文件ID
            file_id = self.download_manager.generate_file_id(message.id, media_type, file_size)
            
            # 检查是否已下载
            if self.download_manager.is_file_completed(file_id, file_size):
                file_path = self.download_manager.download_records[file_id]['file_path']
                print(f"文件已存在且完整，跳过下载: {os.path.basename(file_path)}")
                return file_path
                
            # 获取保存路径
            original_name = getattr(message.media, 'filename', '')
            file_path = self.download_manager.get_file_path(file_id, original_name)
            
            # 创建进度回调
            last_update = [0]
            start_time = [time.time()]
            
            async def progress_callback(received, total):
                if total:
                    now = time.time()
                    if now - last_update[0] >= 0.5:
                        percentage = (received / total) * 100
                        speed = received / (now - start_time[0]) / 1024
                        
                        if self.download_progress_callback:
                            self.download_progress_callback(
                                message.id,
                                percentage,
                                speed,
                                media_type,
                                os.path.basename(file_path),
                                received,
                                total
                            )
                        last_update[0] = now
                        
            # 下载文件
            downloaded_path = await message.download_media(
                file=file_path,
                progress_callback=progress_callback
            )
            
            # 验证下载是否成功
            if downloaded_path and os.path.exists(downloaded_path):
                actual_size = os.path.getsize(downloaded_path)
                if actual_size == file_size:
                    # 添加下载记录
                    self.download_manager.add_download_record(file_id, downloaded_path, file_size)
                    
                    # 发送100%进度
                    if self.download_progress_callback:
                        self.download_progress_callback(
                            message.id,
                            100.0,
                            0,
                            media_type,
                            os.path.basename(file_path),
                            file_size,
                            file_size
                        )
                    return downloaded_path
                else:
                    # 下载不完整，删除文件和记录
                    self.download_manager.remove_download_record(file_id)
                    print(f"文件下载不完整，将重试: {os.path.basename(file_path)}")
                    return None
                    
        except Exception as e:
            print(f"下载媒体文件失败: {str(e)}")
            if 'file_id' in locals():
                self.download_manager.remove_download_record(file_id)
            return None
            
    async def _process_group_id(self, group_id):
        """处理不同格式的群组ID"""
        try:
            # 如果是纯数字
            if group_id.startswith('-100'):
                # 处理超级群组ID
                raw_id = int(group_id[4:])  # 去掉 -100 前缀
                return PeerChannel(raw_id)
            elif group_id.startswith('-'):
                # 处理普通群组ID
                return int(group_id)
                
            # 如果是t.me链接
            if 't.me/' in group_id:
                group_id = group_id.split('/')[-1]
                
            # 尝试直接获取实体
            try:
                entity = await self.client.get_entity(group_id)
                return entity
            except ValueError:
                # 如果直接获取失败，尝试其他方式
                if group_id.isdigit():
                    # 尝试作为频道ID处理
                    return PeerChannel(int(group_id))
                    
            return None
            
        except ValueError as e:
            print(f"处理群组ID时出错: {str(e)}")
            return None
            
    async def _ensure_connected(self):
        """确保与Telegram服务器的连接"""
        retries = 0
        while retries < self.max_retries:
            try:
                if not self.client.is_connected():
                    await self.client.connect()
                if await self.client.is_user_authorized():
                    return True
                return False
            except Exception as e:
                print(f"连接尝试 {retries + 1} 失败: {str(e)}")
                retries += 1
                if retries < self.max_retries:
                    print(f"等待 {self.retry_delay} 秒后重试...")
                    time.sleep(self.retry_delay)
                
        raise Exception("无法连接到Telegram服务器，请检查网络和代理设置")
        
    async def _get_user_info(self, user_id):
        """获取用户信息"""
        if user_id in self.users_cache:
            return self.users_cache[user_id]
            
        try:
            user = await self.client.get_entity(user_id)
            user_info = {
                'username': getattr(user, 'username', ''),
                'first_name': '',
                'last_name': '',
                'display_name': ''
            }
            
            # 处理不同类型的发送者
            if hasattr(user, 'title'):  # 如果是频道或群组
                user_info['display_name'] = user.title
            else:  # 如果是用户
                user_info['first_name'] = getattr(user, 'first_name', '')
                user_info['last_name'] = getattr(user, 'last_name', '')
                if user.username:
                    user_info['display_name'] = f"@{user.username}"
                else:
                    full_name = ' '.join(filter(None, [user_info['first_name'], user_info['last_name']]))
                    user_info['display_name'] = full_name or f"User{user_id}"
                    
            self.users_cache[user_id] = user_info
            return user_info
        except Exception as e:
            print(f"获取发送者 {user_id} 信息失败: {str(e)}")
            return {
                'username': '',
                'first_name': '',
                'last_name': '',
                'display_name': f"Unknown{user_id}"
            }
            
    async def start_crawling(self, group_id, start_date, progress_callback=None, download_progress_callback=None, limit=None, resume=False):
        """开始爬取消息"""
        self.download_progress_callback = download_progress_callback
        try:
            # 初始化客户端
            print(f"使用代理配置: {self.proxy}")
            self.client = TelegramClient(
                'anon',
                self.api_id,
                self.api_hash,
                proxy=self.proxy,
                connection=ConnectionTcpFull,  # 使用完整TCP连接
                connection_retries=5,
                retry_delay=2,
                timeout=60,  # 增加超时时间
                auto_reconnect=True  # 启用自动重连
            )
            
            # 设置回调函数
            if self.phone_code_callback:
                self.client.phone_code_callback = self.phone_code_callback
                
            # 连接到Telegram
            try:
                print("正在连接到Telegram...")
                if not await self._ensure_connected():
                    print("需要进行身份验证...")
                    phone = await self.phone_code_callback()
                    if not phone:
                        raise Exception("未提供电话号码")
                        
                    await self.client.send_code_request(phone)
                    code = await self.code_callback()
                    if not code:
                        raise Exception("未提供验证码")
                        
                    try:
                        await self.client.sign_in(phone, code)
                    except SessionPasswordNeededError:
                        raise Exception("需要两步验证密码")
                        
                print("认证成功，正在获取群组信息...")
                
            except ServerError as e:
                raise Exception(f"服务器错误: {str(e)}\n请稍后重试")
            except Exception as e:
                raise Exception(f"连接Telegram失败: {str(e)}\n请检查网络连接或代理设置")
                
            # 处理群组ID
            processed_id = await self._process_group_id(group_id)
            if not processed_id:
                raise Exception("无法处理群组ID，请确保格式正确")
                
            # 获取群组信息
            try:
                print(f"尝试获取群组信息...")
                if isinstance(processed_id, (PeerChannel, int)):
                    entity = await self.client.get_entity(processed_id)
                else:
                    entity = processed_id
                    
                print(f"成功获取群组信息: {entity.title if hasattr(entity, 'title') else '未知群组'}")
            except ValueError as e:
                raise Exception(f"无法获取群组信息: {str(e)}\n请确保：\n1. 群组ID正确\n2. 您已经加入该群组\n3. 您有权限访问该群组")
            except Exception as e:
                raise Exception(f"获取群组信息失败: {str(e)}")
                
            # 初始化消息列表
            self.messages = []
            
            # 将输入的时间转换为带时区的时间
            if start_date and start_date.tzinfo is None:
                start_date = start_date.replace(tzinfo=timezone.utc)
            
            # 检查是否有上次的进度
            progress_info = None
            last_message_id = None
            if resume:
                progress_data = self.data_processor.load_progress(group_id)
                if progress_data:
                    progress_info, self.messages = progress_data
                    if progress_info and 'last_message_id' in progress_info:
                        last_message_id = progress_info['last_message_id']
                    print(f"找到上次进度：已爬取 {len(self.messages)} 条消息")
                    
            # 获取消息
            try:
                total_messages = 0
                found_start_date = False
                temp_messages = []
                
                print(f"正在定位消息...")
                kwargs = {}
                if start_date:
                    kwargs['offset_date'] = start_date
                if last_message_id:
                    kwargs['offset_id'] = last_message_id
                    
                async for message in self.client.iter_messages(entity, **kwargs):
                    # 如果没有指定起始时间，直接收集消息
                    if not start_date:
                        found_start_date = True
                        temp_messages.append(message)
                        total_messages += 1
                    else:
                        # 确保消息时间也是带时区的
                        message_date = message.date
                        if message_date.tzinfo is None:
                            message_date = message_date.replace(tzinfo=timezone.utc)
                        
                        if message_date <= start_date:
                            found_start_date = True
                            temp_messages.append(message)
                            total_messages += 1
                    
                    if progress_callback:
                        progress_callback(0, f"正在统计消息: {total_messages}")
                    
                    # 如果设置了数量限制，达到后就停止
                    if limit and total_messages >= limit:
                        break
                        
                if total_messages == 0:
                    raise Exception("未找到符合条件的消息")
                    
                # 显示实际要爬取的消息数量
                actual_limit = min(limit, total_messages) if limit else total_messages
                print(f"找到 {actual_limit} 条消息")
                
                # 处理已获取的消息
                processed_messages = 0
                for message in temp_messages[:actual_limit]:
                    try:
                        # 获取发送者信息
                        user_info = await self._get_user_info(message.sender_id)
                        
                        # 更新消息处理进度
                        if progress_callback:
                            progress = (processed_messages / actual_limit) * 100
                            status_text = (
                                f"正在处理消息 {processed_messages + 1}/{actual_limit}\n"
                                f"发送者: {user_info['display_name']}\n"
                                f"时间: {message.date.strftime('%Y-%m-%d %H:%M:%S')}\n"
                                f"类型: {'含媒体文件' if message.media else '纯文本'}"
                            )
                            progress_callback(progress, status_text)
                        
                        # 确保消息时间带有时区信息
                        message_date = message.date
                        if message_date.tzinfo is None:
                            message_date = message_date.replace(tzinfo=timezone.utc)
                        
                        message_data = {
                            'id': message.id,
                            'group': group_id,
                            'sender_id': message.sender_id,
                            'username': user_info['username'],
                            'sender_name': user_info['display_name'],
                            'date': message_date,
                            'text': message.text or '',
                            'views': getattr(message, 'views', 0),
                            'media_type': self._get_media_type(message),
                            'media_path': await self._download_media_with_retry(message) if message.media else None
                        }
                        self.messages.append(message_data)
                        
                        # 更新进度
                        processed_messages += 1
                        if progress_callback:
                            progress = (processed_messages / actual_limit) * 100
                            progress_callback(progress, f"已处理 {processed_messages}/{actual_limit} 条消息")
                            
                        # 每处理10条消息暂停一下，避免请求过于频繁
                        if processed_messages % 10 == 0:
                            await asyncio.sleep(0.5)
                            
                        # 定期保存进度
                        if processed_messages % 100 == 0:
                            self.data_processor.save_progress(
                                group_id,
                                self.messages,
                                last_message_id=message.id,
                                start_date=start_date
                            )
                    except Exception as e:
                        print(f"处理消息 {message.id} 时出错: {str(e)}")
                        continue
                
            except FloodWaitError as e:
                raise Exception(f"请求过于频繁，需要等待 {e.seconds} 秒")
            except Exception as e:
                # 发生错误时保存进度
                if self.messages:
                    self.data_processor.save_progress(
                        group_id,
                        self.messages,
                        last_message_id=last_message_id,
                        start_date=start_date
                    )
                raise e
                
        except Exception as e:
            raise Exception(f"爬取失败: {str(e)}")
        finally:
            if self.client:
                await self.client.disconnect()
            
    def get_messages(self):
        """获取已爬取的消息"""
        return self.messages
        
    def export_to_pandas(self):
        """将数据转换为pandas DataFrame"""
        return pd.DataFrame(self.messages) 