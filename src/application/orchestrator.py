"""
-------------------------------
src/application/orchestrator.py
-------------------------------

Global Scheduler
"""

def orchestrate(
    cliIO: CliIO,
    lightLLM: LLMClient,
    
):
    userMessage = cliIO.ask("你好科研者, 请问你来此处的目的是什么?")    # 获取用户输入的内容
    
    dictMessageOld = lightLLM.chat_completion(
        systemMessage = "分析用户的检索需求, 按照他们的需求生成检索关键词",
        userMessage = userMessage
    )
    
    cliIO.answer(dictMessageOld)
    enhanceMessage = cliIO.ask("这是我当前帮您分析的关键词, 请问您认为还需要补充吗? 还有什么别的需求吗?")
    
    dictMessageNew = lightCoderLLM.api_coder(
        userMessage = userMessage + enhanceMessage
    )
    
    metaDataCollection = dataBase.request(
        key_words = dictMessageNew
    )
    
    answer = []
    
    # 并行更好, 不一定循环
    for metaData in metaDataCollection:
        fileArticle = memoryClient.search(metaData)
        
        if fileArticle:
            pass
        else:
            rawArticle = dataBase.fetch_and_parser(
                meta_data = metaData
            )
            fileArticle = lightLLM.analyze(rawArticle)
            memoryClient.add_memory(fileArticle)
        
        answer += heavyLLM.analyze(fileArticle)
    
    for answerNode in answer:
        if dataBase.fetch_and_parser(answerNode["ALL-DOI"]):
            cliIO.output(answerNode["Content"])