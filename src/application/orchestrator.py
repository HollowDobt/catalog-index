"""
-------------------------------
src/application/orchestrator.py
-------------------------------

Global Scheduler
"""

"""
程序主逻辑函数, 相当于 main 或者 loop 函数
"""

def orchestrate(
    cliIO: CliIO,
    lightLLM: LLMClient,
):
    userMessage = ask("你好科研者, 请问你来此处的目的是什么?")    # 获取用户输入的内容
    
    dictMessageOld = lightLLM.chat_completion(
        systemMessage = "分析用户的检索需求, 按照他们的需求生成检索关键词",
        userMessage = userMessage
    ) # 由大模型负责用户需求分析, 将用户提到的内容转变为关键词. 注意强制要求 AI 只能输出关键词, 如 Q:"Python 比 C++ 弱的证据", A: "Python & C++, Python, 解释器, 编译器, ..."
    
    answer(dictMessageOld) # 将目前 AI 生成的关键词输出
    enhanceMessage = cliIO.ask("这是我当前帮您分析的关键词, 请问您认为还需要补充吗? 还有什么别的需求吗?") # 让用户补充用户认为必要的关键词
    
    dictMessageNew = lightCoderLLM.api_coder(
        userMessage = userMessage + enhanceMessage
    ) # 将前面所有的关键词发向 AI, 让 AI 解析为 Arxiv 平台适配的 api 访问 code. 返回值只能是形如 "['all:electron', 'all:...]" 这样的列表, 里面存储所有访问所需的 api code.
    
    metaDataCollection = [] # 存储元数据的列表
    
    for query in dictMessageNew:
        metaDataCollection += dataBase.request(
            query = query
        ) # 通过 ai 返回的 api code 将元数据填装到元数据存储列表
    
    answer = [] # 存储 AI 分析的结果
    
    for metaData in metaDataCollection:
        fileArticle = memoryClient.search(metaData) # 先查询 mem0 里面是否存有相应的 metadata, 没有的话视为否(False)
        
        if fileArticle:
            pass # 有的话就不需要再解析一遍了
        else:
            rawArticle = dataBase.fetch_and_parser(
                meta_data = metaData
            ) # 没有的话首先根据 metadata 从 arxiv 获取论文, 并将论文解析为 List[Dict[str, Any]] 类型, 存储有所有的文字, 表格和图片信息
            fileArticle = lightLLM.analyze(rawArticle) # 根据上面得到的解析后的文字进行分析, 分析为对 AI 友好的提示词式索引. 严格要求包含论文的所有内容且不改变原意
            memoryClient.add_memory(fileArticle, metaData) # 将解析后的论文存储到 mem0
        
        answer += heavyLLM.find_connect(fileArticle, userMessage) # 联系用户的需求与解析出的论文, 依次确定二者之间的句子词语是否可以互为佐证, 强相关, 给出强相关的语句和论文的大概意思, 并且给出论文元数据方便查询. 要求 AI 的返回形式为 List[Dict[str, Any]], 其中每个元素的 "content" 对应内容, "metadata" 对应元数据
    
    for answerNode in answer:
        if dataBase.fetch_and_parser(answerNode["ALL-DOI"]): # 最后再次确认论文数据库中这个元数据是否真实存在对应的论文, 确定不是 AI 造假
            answer(answerNode["Content"]) # 确实存在则输出相关内容
        else:
            del answer[answerNode] # 不存在就删掉不输出
    
    if not answer:
        answer("No target content found. ") # 如果全部不存在就 target not found.