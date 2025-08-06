import json
from pathlib import Path
import sys
sys.path.extend(['src', 'src/infrastructure'])
from infrastructure.document_parsers import DocumentParser

class DummyLLM:
    def chat_completion(self, *args, **kwargs):
        """
        Mock chat completion method.

        params
        ------
        *args: positional arguments passed to the call
        **kwargs: keyword arguments passed to the call

        return
        ------
        Dictionary mimicking an LLM response
        """
        data = [
            {"term": "Alpha", "definition": "A term", "synonyms": ["A"]}
        ]
        return {"choices": [{"message": {"content": json.dumps(data)}}]}

def test_safe_load_json():
    raw = "```json\n[{\"term\":\"A\"}]```"
    result = DocumentParser._safe_load_json(raw)
    assert isinstance(result, list) and result[0]["term"] == "A"

def test_parse_file(tmp_path):
    parser = DocumentParser(DummyLLM())
    sample = Path('tests/sample_documents/sample.docx')
    result = parser.parse_file(sample)
    assert result["segments"][0]["term"] == "Alpha"
    assert result["segments"][0]["synonyms"] == ["A"]

