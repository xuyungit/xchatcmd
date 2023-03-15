import os
from pathlib import Path
import openai

def set_openapi_conf(api_key: str, api_base: str) -> None:
    if api_key:
        openai.api_key = api_key
    if api_base:
        openai.api_base = api_base

    def get_conf_content_by_name(name: str) -> str:
        expected_filename_home = Path.home() / name
        expected_filename_cwd = Path(name)
        chosed_filename = None
        if expected_filename_home.exists():
            chosed_filename = expected_filename_home
        elif expected_filename_cwd.exists():
            chosed_filename = expected_filename_cwd
        if chosed_filename:
            return chosed_filename.read_text().strip()
        return ''

    if not openai.api_key:
        content = get_conf_content_by_name('.apikey')
        if content:
            openai.api_key = content
    if not api_base and not os.environ.get("OPENAI_API_BASE"):
        content = get_conf_content_by_name('.apibase')
        if content:
            openai.api_base = content
