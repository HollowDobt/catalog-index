from prompt_to_metadata import prompt_to_metadata

ls = prompt_to_metadata(
    interface="debug", 
    raw_message_process_llm="deepseek", 
    raw_message_process_llm_model="deepseek-reasoner", 
    api_generate_llm="qwen", 
    api_generate_llm_model="qwen3-coder-plus"
)

print(ls)