from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import aiohttp
import json
import re

@register("clocc_search", "YourName", "CloCC资源搜索插件", "1.0.0")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        # 存储用户的搜索结果，用于交互式查询
        self.user_search_results = {}

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
                yield event.plain_result("正在搜索，请稍后...")
                
                # 调用搜索接口
                result = await self.search_resources(keyword, user_id)
                yield event.plain_result(result)
            else:
                yield event.plain_result("请输入要搜索的关键词，例如：搜电影")
        else:
            yield event.plain_result("搜索格式不正确，请使用：搜+关键词")

    # 处理用户输入的编号
    @filter.regex(r"^(\d+)$")  
    async def number_handler(self, event: AstrMessageEvent):
        """处理用户输入的编号"""
        message_str = event.get_message_str().strip()
        user_id = event.get_sender_id()
        
        # 检查用户是否有待处理的搜索结果
        if user_id in self.user_search_results and self.user_search_results[user_id]:
            try:
                index = int(message_str)
                search_results = self.user_search_results[user_id]
                
                if 1 <= index <= len(search_results):
                    # 返回对应编号的详细信息
                    item = search_results[index - 1]
                    title = item.get("note", "未知标题")
                    url = item.get("url", "未知链接")
                    password = item.get("password", "")
                    source = "百度网盘" if item.get("type") == "baidu" else "夸克网盘"
                    
                    result = f"资源详情:\n标题: {title}\n来源: {source}\n链接: {url}"
                    if password:
                        result += f"\n密码: {password}"
                    
                    # 清除用户的搜索结果缓存
                    del self.user_search_results[user_id]
                    yield event.plain_result(result)
                else:
                    yield event.plain_result(f"请输入有效的编号 (1-{len(search_results)})")
            except ValueError:
                yield event.plain_result("请输入有效的数字编号")
        else:
            # 如果用户没有待处理的搜索结果，则不处理数字消息
            pass

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
            
            # 平均展示百度网盘和夸克网盘的结果
            all_results = []
            
            # 轮流添加百度和夸克的结果，确保平均展示
            max_len = max(len(baidu_results), len(quark_results))
            for i in range(max_len):
                # 添加百度网盘结果
                if i < len(baidu_results):
                    all_results.append(baidu_results[i])
                # 添加夸克网盘结果
                if i < len(quark_results):
                    all_results.append(quark_results[i])
            
            # 最多只展示10条
            all_results = all_results[:10]
            
            # 将搜索结果存储在用户缓存中
            self.user_search_results[user_id] = all_results
            
            # 只返回带编号的标题列表
            formatted_results = [f"搜索结果 (关键词: {keyword}):"]
            for i, item in enumerate(all_results, 1):
                title = item.get("note", "未知标题")
                source = "百度网盘" if item.get("type") == "baidu" else "夸克网盘"
                formatted_results.append(f"{i}. {title} [{source}]")
            
            # 添加交互提示
            formatted_results.append("\n请输入编号查看详细信息（如：1）")
            
            return "\n".join(formatted_results)
        except Exception as e:
            logger.error(f"格式化搜索结果失败: {e}")
            return f"结果格式化失败: {e}"

    async def terminate(self):
        """插件销毁"""
        pass