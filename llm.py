"""Small OpenAI-compatible Chat Completions adapter; no third-party dependencies."""
import json
import os
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

def chat(messages, tools=None):
    key = os.environ.get('LLM_API_KEY', '')
    model = os.environ.get('LLM_MODEL', '')
    base = os.environ.get('LLM_BASE_URL', 'https://api.openai.com/v1').rstrip('/')
    if not key or not model:
        raise ValueError('Set LLM_API_KEY and LLM_MODEL for live mode')
    if not base.startswith('https://'):
        raise ValueError('LLM_BASE_URL must use HTTPS')
    body = dict(model=model, messages=messages, temperature=0)
    if tools:
        body.update(tools=tools, tool_choice='auto')
    req = Request(base+'/chat/completions', data=json.dumps(body).encode(),
                  headers={'Authorization': 'Bearer '+key, 'Content-Type': 'application/json'})
    try:
        with urlopen(req, timeout=30) as response:
            return json.load(response)['choices'][0]['message']
    except HTTPError as exc:
        # Do not print vendor response bodies, prompts, or credentials.
        raise RuntimeError(f'LLM HTTP {exc.code}; check model, quota and endpoint') from None
    except (URLError, TimeoutError):
        raise RuntimeError('LLM network failure or timeout') from None
