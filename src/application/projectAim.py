"""
类与函数接口定义(伪代码表)
"""

def ask(query: str) -> None:
	"""
	允许传入询问字符串, 获取用户当前输入的内容
	"""
	...


def answer(query: str) -> None:
	"""
	输出你输传入的内容
	"""
	...

class LLMClient:
	"""
	用于统一的大模型抽象层, 核心兼容 DeepSeek 官网式的请求标准.
	因此后面私有部署时为保证最佳兼容性建议使用 DeepSeek 官网标准.
	"""
	def chat_completion(self, user_query: str, system_query: str) -> str:
		"""
		作为一个工具函数, 作用是指定 user 和 system 提示词对大模型运行的网站发起请求.
		可以通过使用其他函数调用这个函数进行简单的封装
		"""
		...

	def api_coder(self, user_query: str) -> str:
		"""
		将用户的请求按照文档中明确指示的通过 api 请求格式进行输出
		"""
		...

	def analyze(self, article: str) -> str:
		"""
		发送论文, 让 AI 解析为结构化的文档. 要求完整性和不改变原文内容
		这一步需要大量的工作, 也是重点, 我在 7 月 29 日会解决到底怎么存储的问题
		"""
		...

	def find_connect(self, article: str, user_query: str) -> str:
		"""
		再次发送论文, 查找论文和用户需求之间有无关联
		"""

class DataBase:
	"""
	用于统一的科研数据库抽象层. 目前使用的是 arxiv.org 请求标准.
	arxiv 本身没有对于 api 的要求, 是开源免费的, 因此很好完成请求
	"""
	def request(self, query: str) -> List[str]:
		"""
		通过 api 端口获取 feed 文件的元数据(metadata)
		注意限制速度 3 篇每秒
		"""
		...

	def fetch_and_parser(self, meta_data: Dict[str, Any]) -> str:
		"""
		通过元数据获取论文
		"""
		...



class MemoryLayer:
	"""
	记忆层/解析后内容存储层
	"""
	def search(self, meta_data: Dict[str, Any]) -> str:
		"""
		从记忆层中通过 meta_data 搜索
		"""
		...

	def add_memory(self, meta_data: Dict[str, Any]) -> None:
		"""
		使用元数据作为标签添加到记忆层
		"""
		...
