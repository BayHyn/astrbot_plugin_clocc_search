from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import aiohttp
import json
import re

@register("helloworld", "YourName", "一个简单的 Hello World 插件", "1.0.0")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        # 定义关键字和对应的回复
        self.keyword_responses = {
            "你好": "你好！很高兴见到你！",
            "hello": "Hello! Nice to meet you!",
            "帮助": "这是一个关键字回复插件。你可以试试发送：你好、hello、帮助等关键字。",
            "天气": "今天天气不错呢！",
            "时间": "现在是北京时间：2025年10月11日"
        }

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""
    
    # 注册指令的装饰器。指令名为 helloworld。注册成功后，发送 `/helloworld` 就会触发这个指令，并回复 `你好, {user_name}!`
    @filter.command("helloworld")
    async def helloworld(self, event: AstrMessageEvent):
        """这是一个 hello world 指令""" # 这是 handler 的描述，将会被解析方便用户了解插件内容。建议填写。
        user_name = event.get_sender_name()
        message_str = event.message_str # 用户发的纯文本消息字符串
        message_chain = event.get_messages() # 用户所发的消息的消息链 # from astrbot.api.message_components import *
        logger.info(message_chain)
        yield event.plain_result(f"Hello, {user_name}, 你发了 {message_str}!") # 发送一条纯文本消息

    # 搜索功能：当消息以"搜"开头时触发
    @filter.regex(r"^搜(.+)")  
    async def search_handler(self, event: AstrMessageEvent):
        """搜索处理器"""
        message_str = event.get_message_str().strip()
        # 使用正则表达式提取搜索关键字
        match = re.match(r"^搜(.+)", message_str)
        if match:
            keyword = match.group(1).strip()
            if keyword:
                # 先发送正在搜索的提示消息
                yield event.plain_result("正在搜索，请稍后...")
                
                # 调用搜索接口
                result = await self.search_resources(keyword)
                yield event.plain_result(result)
            else:
                yield event.plain_result("请输入要搜索的关键词，例如：搜电影")
        else:
            yield event.plain_result("搜索格式不正确，请使用：搜+关键词")

    # 关键字回复功能：匹配除搜索外的其他消息
    @filter.regex(r"^(?!搜).*$")  # 使用负向先行断言，匹配不以"搜"开头的消息
    async def keyword_handler(self, event: AstrMessageEvent):
        """关键字识别处理器"""
        message_str = event.get_message_str().strip()  # 获取用户发送的消息并去除首尾空格
        
        # 检查是否包含预定义的关键字
        for keyword, response in self.keyword_responses.items():
            if keyword in message_str:
                logger.info(f"匹配到关键字: {keyword}, 发送回复: {response}")
                yield event.plain_result(response)
                return  # 找到匹配的关键字后立即返回，避免重复回复

    async def search_resources(self, keyword: str) -> str:
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
                        return self.format_search_results(data, keyword)
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

    def format_search_results(self, data: dict, keyword: str) -> str:
        """格式化搜索结果"""
        try:
            logger.info(f"开始格式化搜索结果: {data}")
            
            # 检查数据结构
            if not data or "merged_by_type" not in data:
                return "未找到相关资源。"
            
            # 获取总结果数
            total_count = data.get("total", 0)
            
            # 分别获取百度网盘和夸克网盘的结果
            merged_data = data.get("merged_by_type", {})
            baidu_results = merged_data.get("baidu", [])
            quark_results = merged_data.get("quark", [])
            
            if not baidu_results and not quark_results:
                return "未找到相关资源。"
            
            # 平均展示百度网盘和夸克网盘的结果
            all_results = []
            max_results = min(10, max(len(baidu_results), len(quark_results)))
            
            # 轮流添加百度和夸克的结果，确保平均展示
            for i in range(max_results):
                # 添加百度网盘结果
                if i < len(baidu_results):
                    all_results.append(baidu_results[i])
                # 添加夸克网盘结果
                if i < len(quark_results):
                    all_results.append(quark_results[i])
            
            # 如果还有空间，继续添加剩余结果，最多10条
            i = 0
            while len(all_results) < 10 and (i < len(baidu_results) or i < len(quark_results)):
                if i < len(baidu_results) and baidu_results[i] not in all_results:
                    all_results.append(baidu_results[i])
                if i < len(quark_results) and quark_results[i] not in all_results:
                    all_results.append(quark_results[i])
                i += 1
            
            # 最多只展示10条
            all_results = all_results[:10]
            
            # 格式化结果
            formatted_results = [f"搜索结果 (关键词: {keyword}):"]
            for i, item in enumerate(all_results, 1):
                title = item.get("note", "未知标题")
                url = item.get("url", "未知链接")
                password = item.get("password", "")
                source = "百度网盘" if "baidu.com" in url else "夸克网盘"
                
                if password:
                    formatted_results.append(f"{i}. {title}\n   来源: {source}\n   链接: {url}\n   密码: {password}")
                else:
                    formatted_results.append(f"{i}. {title}\n   来源: {source}\n   链接: {url}")
            
            # 添加结果统计信息
            displayed_count = len(all_results)
            formatted_results.append(f"\n📊 共搜索到 {total_count} 条数据，当前展示 {displayed_count} 条")
            formatted_results.append("如需查看更多结果，请复制 https://pansd.xyz 到浏览器查看。")
            
            return "\n\n".join(formatted_results)
        except Exception as e:
            logger.error(f"格式化搜索结果失败: {e}")
            return f"结果格式化失败: {e}"

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""