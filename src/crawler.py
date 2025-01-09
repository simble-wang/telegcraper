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
        
    async def _download_media(self, message):
        """下载媒体文件"""
        if not message.media:
            return None
            
        try:
            # 生成唯一文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{message.id}"
            
            # 下载到指定目录
            path = await message.download_media(
                file=os.path.join(self.download_path, filename)
            )
            return path
        except Exception as e:
            print(f"下载媒体文件失败: {str(e)}")
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
                'username': user.username or '',
                'first_name': user.first_name or '',
                'last_name': user.last_name or ''
            }
            # 生成显示名称
            if user.username:
                user_info['display_name'] = f"@{user.username}"
            else:
                full_name = ' '.join(filter(None, [user.first_name, user.last_name]))
                user_info['display_name'] = full_name or f"User{user_id}"
                
            self.users_cache[user_id] = user_info
            return user_info
        except Exception as e:
            print(f"获取用户 {user_id} 信息失败: {str(e)}")
            return {'username': '', 'first_name': '', 'last_name': '', 'display_name': f"User{user_id}"}
            
    async def start_crawling(self, group_id, start_date, progress_callback=None, limit=None):
        """开始爬取消息"""
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
            
            # 先获取指定时间之前的消息数量
            try:
                total_messages = 0
                found_start_date = False
                temp_messages = []
                
                # 将输入的时间转换为带时区的时间
                if start_date.tzinfo is None:
                    start_date = start_date.replace(tzinfo=timezone.utc)
                
                print(f"正在定位 {start_date} 之前的消息...")
                async for message in self.client.iter_messages(entity):
                    # 确保消息时间也是带时区的
                    message_date = message.date
                    if message_date.tzinfo is None:
                        message_date = message_date.replace(tzinfo=timezone.utc)
                    
                    if message_date <= start_date:
                        found_start_date = True
                        temp_messages.append(message)
                        total_messages += 1
                        if progress_callback:
                            progress_callback(0, f"正在统计起始时间前的消息: {total_messages}")
                        
                        # 如果设置了数量限制，达到后就停止
                        if limit and total_messages >= limit:
                            break
                            
                if not found_start_date:
                    raise Exception("未找到指定时间之前的消息")
                    
                if total_messages == 0:
                    raise Exception("未找到符合条件的消息")
                    
                # 显示实际要爬取的消息数量
                actual_limit = min(limit, total_messages) if limit else total_messages
                print(f"找到 {start_date} 之前的 {actual_limit} 条消息")
                
                # 处理已获取的消息
                processed_messages = 0
                for message in temp_messages[:actual_limit]:
                    # 获取发送者信息
                    user_info = await self._get_user_info(message.sender_id)
                    
                    # 确保消息时间带有时区信息
                    message_date = message.date
                    if message_date.tzinfo is None:
                        message_date = message_date.replace(tzinfo=timezone.utc)
                    
                    message_data = {
                        'group': group_id,
                        'sender_id': message.sender_id,
                        'username': user_info['username'],
                        'sender_name': user_info['display_name'],
                        'date': message_date,
                        'text': message.text,
                        'views': getattr(message, 'views', 0),
                        'media_type': self._get_media_type(message),
                        'media_path': await self._download_media(message) if message.media else None
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
                        
            except FloodWaitError as e:
                raise Exception(f"请求过于频繁，需要等待 {e.seconds} 秒")
            except Exception as e:
                raise Exception(f"爬取消息时出错: {str(e)}")
                
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