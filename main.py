from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

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

    # 新增关键字识别功能
    @filter.event_message_type(filter.EventMessageType.MESSAGE)  # 监听所有消息事件
    async def keyword_handler(self, event: AstrMessageEvent):
        """关键字识别处理器"""
        message_str = event.get_message_str().strip()  # 获取用户发送的消息并去除首尾空格
        
        # 检查是否包含预定义的关键字
        for keyword, response in self.keyword_responses.items():
            if keyword in message_str:
                logger.info(f"匹配到关键字: {keyword}, 发送回复: {response}")
                yield event.plain_result(response)
                return  # 找到匹配的关键字后立即返回，避免重复回复
        
        # 如果没有匹配的关键字，可以不回复或发送默认消息
        # yield event.plain_result("抱歉，我没有理解你的意思。发送'帮助'查看可用关键字。")

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""