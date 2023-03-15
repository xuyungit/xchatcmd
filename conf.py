import os
from pathlib import Path
import openai

def get_conf_content_by_name(name: str) -> str:
    """
    Search for and read the content of a configuration file by its name.

    This function looks for the specified configuration file in the user's
    home directory and the current working directory. If it finds the file,
    it reads its content, removes leading and trailing whitespace, and
    returns the content as a string. If it doesn't find the file, it returns
    an empty string.

    Args:
        name (str): The filename of the configuration file.

    Returns:
        str: The content of the configuration file, or an empty string if
        the file is not found.
    """

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

def set_openapi_conf(api_key: str, api_base: str) -> None:
    """
    Configure the OpenAI API with the given API key and API base URL.

    If the API key and/or API base URL are not provided, this function will
    search for the corresponding configuration files in the user's home
    directory and the current working directory.

    Args:
        api_key (str): The API key for the OpenAI API.
        api_base (str): The API base URL for the OpenAI API.
    """
    if api_key:
        openai.api_key = api_key
    if api_base:
        openai.api_base = api_base

    if not openai.api_key:
        content = get_conf_content_by_name('.apikey')
        if content:
            openai.api_key = content
    if not api_base and not os.environ.get('OPENAI_API_BASE'):
        content = get_conf_content_by_name('.apibase')
        if content:
            openai.api_base = content
