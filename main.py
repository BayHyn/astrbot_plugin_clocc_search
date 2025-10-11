from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import aiohttp
import json
import re
from typing import Optional, Tuple

@register("clocc_search", "YourName", "CloCC资源搜索插件", "1.0.0")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        # 存储用户的搜索结果，用于交互式查询
        self.user_search_results = {}
        # 存储用户的分页信息
        self.user_pagination = {}

    async def initialize(self):
        """插件初始化"""
        pass
    
    # 搜索功能：当消息以"搜"开头时触发
    @filter.regex(r"^搜(.+)")  
    async def search_handler(self, event: AstrMessageEvent):
        """搜索处理器"""
        message_str = event.get_message_str().strip()
        user_id = event.get_sender_id()
        
        # 使用正则表达式提取搜索关键字
        match = re.match(r"^搜(.+)", message_str)
        if match:
            keyword = match.group(1).strip()
            if keyword:
                # 先发送正在搜索的提示消息
                yield event.plain_result("🔍 正在搜索，请稍后... (๑•̀ω•́๑)✧")
                
                # 调用搜索接口
                result = await self.search_resources(keyword, user_id)
                yield event.plain_result(result)
            else:
                yield event.plain_result("请输入要搜索的关键词，例如：搜电影")
        else:
            yield event.plain_result("搜索格式不正确，请使用：搜+关键词")

    # 处理用户输入的编号（获取详细信息）
    @filter.regex(r"^获取(\d+)$")  
    async def number_handler(self, event: AstrMessageEvent):
        """处理用户输入的编号"""
        message_str = event.get_message_str().strip()
        user_id = event.get_sender_id()
        
        # 使用正则表达式提取编号
        match = re.match(r"^获取(\d+)$", message_str)
        if match:
            try:
                index = int(match.group(1))
                search_results = self.user_search_results[user_id]
                # 获取当前页码信息
                pagination = self.user_pagination.get(user_id, {"page": 1, "per_page": 10})
                current_page = pagination["page"]
                per_page = pagination["per_page"]
                
                # 计算实际索引（考虑分页）
                actual_index = (current_page - 1) * per_page + index
                
                if 1 <= actual_index <= len(search_results):
                    # 获取对应编号的详细信息
                    item = search_results[actual_index - 1]
                    title = item.get("note", "未知标题")
                    url = item.get("url", "未知链接")
                    password = item.get("password", "")
                    source = "百度网盘" if item.get("type") == "baidu" else "夸克网盘"
                    
                    # 如果是百度网盘，先调用转换接口
                    if item.get("type") == "baidu":
                        yield event.plain_result("🔄 正在获取资源，请稍后...预计需要10秒左右 (´∀｀)♡")
                        converted_result = await self.convert_baidu_link(url)
                        if converted_result:
                            # 转换成功，使用新链接
                            url = converted_result[0]
                            password = converted_result[1]
                            result = f"🔍 资源详情:\n📖 标题: {title}\n🔗 来源: {source}\n🌐 链接: {url}"
                            if password:
                                result += f"\n🔑 密码: {password}"
                            yield event.plain_result(result)
                        else:
                            # 转换失败，提示链接已失效
                            yield event.plain_result("❌ 抱歉，该分享链接已失效，请尝试获取其他资源 (；′⌒`)")
                    else:
                        # 夸克网盘直接显示详情
                        result = f"🔍 资源详情:\n📖 标题: {title}\n🔗 来源: {source}\n🌐 链接: {url}"
                        if password:
                            result += f"\n🔑 密码: {password}"
                        yield event.plain_result(result)
                else:
                    yield event.plain_result(f"请输入有效的编号 (1-{min(per_page, len(search_results) - (current_page-1) * per_page)})")
            except ValueError:
                yield event.plain_result("请输入有效的数字编号")
        else:
            # 如果用户没有待处理的搜索结果，则不处理数字消息
            pass

    # 处理下一页指令（不加斜杠）
    @filter.regex(r"^下一页$")  
    async def next_page_handler(self, event: AstrMessageEvent):
        """处理下一页指令"""
        user_id = event.get_sender_id()
        
        # 检查用户是否有待处理的搜索结果
        if user_id in self.user_search_results and self.user_search_results[user_id]:
            # 获取分页信息
            if user_id not in self.user_pagination:
                self.user_pagination[user_id] = {"page": 1, "per_page": 10}
            
            pagination = self.user_pagination[user_id]
            current_page = pagination["page"]
            per_page = pagination["per_page"]
            search_results = self.user_search_results[user_id]
            
            # 计算总页数
            total_pages = (len(search_results) + per_page - 1) // per_page
            
            if current_page < total_pages:
                pagination["page"] = current_page + 1
                # 显示新页面的结果
                result = self.format_paginated_results(user_id, search_results, pagination)
                yield event.plain_result(result)
            else:
                yield event.plain_result("已经是最后一页了")
        else:
            yield event.plain_result("没有搜索结果可以翻页")

    # 处理上一页指令（不加斜杠）
    @filter.regex(r"^上一页$")  
    async def prev_page_handler(self, event: AstrMessageEvent):
        """处理上一页指令"""
        user_id = event.get_sender_id()
        
        # 检查用户是否有待处理的搜索结果
        if user_id in self.user_search_results and self.user_search_results[user_id]:
            # 获取分页信息
            if user_id not in self.user_pagination:
                self.user_pagination[user_id] = {"page": 1, "per_page": 10}
            
            pagination = self.user_pagination[user_id]
            current_page = pagination["page"]
            
            if current_page > 1:
                pagination["page"] = current_page - 1
                # 显示新页面的结果
                search_results = self.user_search_results[user_id]
                result = self.format_paginated_results(user_id, search_results, pagination)
                yield event.plain_result(result)
            else:
                yield event.plain_result("已经是第一页了")
        else:
            yield event.plain_result("没有搜索结果可以翻页")

    async def search_resources(self, keyword: str, user_id: str) -> str:
        """调用搜索接口并返回结果"""
        url = f"https://pansd.xyz/api/search?kw={keyword}&src=all&cloud_types=baidu%2Cquark"
        
        # 准备请求参数
        params = {
            "kw": keyword,
            "src": "all",
            "cloud_types": "baidu,quark"
        }
        
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "AstrBot-Search-Plugin/1.0"
        }
        
        try:
            logger.info(f"正在调用搜索接口: {url}")
            
            # 设置超时时间
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, params=params, headers=headers) as response:
                    logger.info(f"搜索接口响应状态码: {response.status}")
                    
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"搜索接口响应数据: {data}")
                        return self.format_search_results(data, keyword, user_id)
                    else:
                        error_text = await response.text()
                        logger.error(f"搜索接口请求失败，状态码: {response.status}, 响应内容: {error_text}")
                        return f"搜索失败，HTTP状态码: {response.status}"
        except aiohttp.ClientConnectorError as e:
            logger.error(f"网络连接错误: {e}")
            return "搜索失败：无法连接到搜索服务器，请检查网络连接"
        except aiohttp.ClientError as e:
            logger.error(f"HTTP客户端错误: {e}")
            return f"搜索失败：网络请求错误 {e}"
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析错误: {e}")
            return f"搜索失败：返回数据格式错误 {e}"
        except Exception as e:
            logger.error(f"搜索接口调用失败: {e}")
            return f"搜索失败: {e}"

    async def convert_baidu_link(self, original_url: str) -> Optional[Tuple[str, str]]:
        """转换百度网盘链接"""
        convert_url = "http://103.109.22.15:5003/api/key/transfer-and-share"
        api_key = "oPhbkFvdYnuKxMOCsei7gLHVSoQ5cnmj1MCSNiir35s"
        
        headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }
        
        # 固定密码为1234
        data = {
            "share_url": original_url,
            "save_dir": "/pansou_downloads",
            "share_password": "1234",
            "share_period": 0
        }
        
        try:
            logger.info(f"正在转换百度网盘链接: {original_url}")
            
            # 设置超时时间
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(convert_url, headers=headers, json=data) as response:
                    logger.info(f"转换接口响应状态码: {response.status}")
                    
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"转换接口响应数据: {result}")
                        
                        if result.get("success"):
                            share_info = result.get("share_info", {})
                            converted_url = share_info.get("url", original_url)
                            converted_password = share_info.get("password", "1234")
                            return (converted_url, converted_password)
                        else:
                            logger.error(f"转换失败: {result.get('message')}")
                            return None
                    else:
                        error_text = await response.text()
                        logger.error(f"转换接口请求失败，状态码: {response.status}, 响应内容: {error_text}")
                        return None
        except aiohttp.ClientConnectorError as e:
            logger.error(f"转换接口网络连接错误: {e}")
            return None
        except aiohttp.ClientError as e:
            logger.error(f"转换接口HTTP客户端错误: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"转换接口JSON解析错误: {e}")
            return None
        except Exception as e:
            logger.error(f"转换接口调用失败: {e}")
            return None

    def format_search_results(self, data: dict, keyword: str, user_id: str) -> str:
        """格式化搜索结果"""
        try:
            logger.info(f"开始格式化搜索结果: {data}")
            
            # 检查数据结构
            if not data or "merged_by_type" not in data:
                return "未找到相关资源。"
            
            # 分别获取百度网盘和夸克网盘的结果
            merged_data = data.get("merged_by_type", {})
            baidu_results = merged_data.get("baidu", [])
            quark_results = merged_data.get("quark", [])
            
            if not baidu_results and not quark_results:
                return "未找到相关资源。"
            
            # 按照网盘类型分组展示（先5条百度，再5条夸克）
            all_results = self.group_results_by_type(baidu_results, quark_results)
            
            # 将搜索结果存储在用户缓存中
            self.user_search_results[user_id] = all_results
            # 初始化分页信息
            self.user_pagination[user_id] = {"page": 1, "per_page": 10}
            
            # 返回第一页的结果
            pagination = self.user_pagination[user_id]
            return self.format_paginated_results(user_id, all_results, pagination)
        except Exception as e:
            logger.error(f"格式化搜索结果失败: {e}")
            return f"结果格式化失败: {e}"

    def group_results_by_type(self, baidu_results: list, quark_results: list) -> list:
        """按照网盘类型分组展示结果（先5条百度，再5条夸克）"""
        # 创建一个新的列表来存储分组后的结果
        grouped_results = []
        
        # 先添加百度网盘的结果（最多5条）
        baidu_count = min(len(baidu_results), 5)
        for i in range(baidu_count):
            baidu_results[i]["type"] = "baidu"  # 确保有type字段
            grouped_results.append(baidu_results[i])
        
        # 再添加夸克网盘的结果（最多5条）
        quark_count = min(len(quark_results), 5)
        for i in range(quark_count):
            quark_results[i]["type"] = "quark"  # 确保有type字段
            grouped_results.append(quark_results[i])
        
        # 如果某种类型的结果不足5条，用另一种类型的结果补充
        total_added = len(grouped_results)
        if total_added < 10:
            remaining_slots = 10 - total_added
            # 补充百度网盘结果
            if len(baidu_results) > baidu_count:
                for i in range(baidu_count, min(baidu_count + remaining_slots, len(baidu_results))):
                    baidu_results[i]["type"] = "baidu"
                    grouped_results.append(baidu_results[i])
                    remaining_slots -= 1
                    if remaining_slots <= 0:
                        break
            # 补充夸克网盘结果
            if remaining_slots > 0 and len(quark_results) > quark_count:
                for i in range(quark_count, min(quark_count + remaining_slots, len(quark_results))):
                    quark_results[i]["type"] = "quark"
                    grouped_results.append(quark_results[i])
                    remaining_slots -= 1
                    if remaining_slots <= 0:
                        break
        
        # 继续添加剩余的结果，保持分组模式（5个百度，5个夸克）
        baidu_index = max(baidu_count, 5)
        quark_index = max(quark_count, 5)
        
        while baidu_index < len(baidu_results) or quark_index < len(quark_results):
            # 添加下一组百度网盘结果（最多5条）
            baidu_added = 0
            while baidu_added < 5 and baidu_index < len(baidu_results):
                baidu_results[baidu_index]["type"] = "baidu"
                grouped_results.append(baidu_results[baidu_index])
                baidu_index += 1
                baidu_added += 1
            
            # 添加下一组夸克网盘结果（最多5条）
            quark_added = 0
            while quark_added < 5 and quark_index < len(quark_results):
                quark_results[quark_index]["type"] = "quark"
                grouped_results.append(quark_results[quark_index])
                quark_index += 1
                quark_added += 1
            
            # 如果其中一种类型已经没有结果了，继续添加另一种类型的剩余结果
            if baidu_index >= len(baidu_results):
                while quark_index < len(quark_results):
                    quark_results[quark_index]["type"] = "quark"
                    grouped_results.append(quark_results[quark_index])
                    quark_index += 1
            
            if quark_index >= len(quark_results):
                while baidu_index < len(baidu_results):
                    baidu_results[baidu_index]["type"] = "baidu"
                    grouped_results.append(baidu_results[baidu_index])
                    baidu_index += 1
        
        return grouped_results

    def format_paginated_results(self, user_id: str, all_results: list, pagination: dict) -> str:
        """格式化分页结果，按网盘类型分组展示"""
        page = pagination["page"]
        per_page = pagination["per_page"]
        
        # 计算当前页的起始和结束索引
        start_index = (page - 1) * per_page
        end_index = min(start_index + per_page, len(all_results))
        
        # 获取当前页的结果
        page_results = all_results[start_index:end_index]
        
        # 格式化结果
        formatted_results = [f"🔍 搜索结果 (第 {page} 页)："]
        formatted_results.append("═" * 30)
        
        # 按类型分组展示
        baidu_items = []
        quark_items = []
        
        for i, item in enumerate(page_results, 1):
            title = item.get("note", "未知标题")
            if item.get("type") == "baidu":
                baidu_items.append(f"{i}. {title}")
            elif item.get("type") == "quark":
                quark_items.append(f"{i}. {title}")
        
        # 展示百度网盘结果
        if baidu_items:
            formatted_results.append("🌐 百度网盘资源:")
            formatted_results.append("─" * 20)
            formatted_results.extend(baidu_items)
            formatted_results.append("")
        
        # 展示夸克网盘结果
        if quark_items:
            formatted_results.append("🌐 夸克网盘资源:")
            formatted_results.append("─" * 20)
            formatted_results.extend(quark_items)
        
        formatted_results.append("═" * 30)
        
        # 添加分页信息和交互提示
        total_count = len(all_results)
        total_pages = (total_count + per_page - 1) // per_page
        formatted_results.append(f"📈 共 {total_count} 条结果，当前第 {page}/{total_pages} 页")
        formatted_results.append("📌 输入 '获取+编号' 查看详细信息（如：获取1）")
        
        if page > 1:
            formatted_results.append("⬅️  发送 '上一页' 查看前一页")
        if page < total_pages:
            formatted_results.append("➡️  发送 '下一页' 查看下一页")
        
        return "\n".join(formatted_results)

    async def terminate(self):
        """插件销毁"""
        pass