"""
========================
|src/application/app.py|
========================
"""


from fastapi import FastAPI
from pydantic import BaseModel

from domains import main


class InputModel(BaseModel):
    raw_message_process_llm: str
    raw_message_process_llm_model: str
    api_generate_llm: str
    api_generate_llm_model: str
    embedding_llm: str
    embedding_llm_model:str
    max_workers_llm: int = 8
    max_search_retries: int = 2


class OutputModel(BaseModel):
    result: str


app = FastAPI(title="Library Index")

@app.post("/research", response_model=OutputModel)
async def research(payload: InputModel):
    output = main(**payload.model_dump())
    return OutputModel.model_validate(output)