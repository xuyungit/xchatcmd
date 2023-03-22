import time
import argparse
from pathlib import Path
import openai
import tiktoken
from conf import set_openapi_conf

AVERAGE_CHARS_PER_TOKEN = 6
MODEL_NAME = "gpt-3.5-turbo"

def translate_text(user_text: str, temperature: float):
    """
    Request translation of the given text using OpenAI API.

    :param user_text: Text to be translated.
    :param temperature: Controls the randomness of the AI's response.
    :return: Tuple containing the translated text and the number of tokens used in the API call.
    """

    response = openai.ChatCompletion.create(
      model = MODEL_NAME,
      messages = [
        {
            'role': "user",
            "content": f'将下面的文字翻译成简体中文\n"""{user_text}\n"""'
        }
      ],
      request_timeout = 120,
      timeout = 120,
      temperature = temperature
    )
    response_text:str = response.choices[0].message.content # type: ignore
    total_tokens:int = response.usage.total_tokens # type: ignore
    return response_text, total_tokens

def get_tokens(text: str) -> int:
    """
    Calculate the number of tokens in the given text.

    :param text: Text for which tokens should be calculated.
    :return: Number of tokens in the text.
    """

    token_encoding = tiktoken.get_encoding("cl100k_base")
    return len(token_encoding.encode(text))

def get_next_chunk(text: str, start_pos: int, max_tokens=1365):
    """
    Find the next chunk of text to translate based on the starting position and maximum tokens allowed.

    :param text: Full text to be translated.
    :param start_pos: Starting position for the next chunk.
    :param max_tokens: Maximum number of tokens allowed for the chunk.
    :return: Tuple containing the text chunk, end position, number of tokens, and a flag indicating if the end of the text is reached.
    """

    sentence_split_punctuation = '.!?'
    # Let's assume that each token has 6 character length on average
    end_pos = min(len(text) - 1, start_pos + max_tokens * AVERAGE_CHARS_PER_TOKEN)
    is_end_of_text = False
    while True:
        chunk_text = text[start_pos:end_pos+1]
        tokens = get_tokens(chunk_text)
        if tokens <= max_tokens:
            if end_pos == len(text) - 1:
                is_end_of_text = True
            return chunk_text, end_pos + 1, tokens, is_end_of_text
        # search backwards for a sentence
        while end_pos > 0:
            end_pos -= 1
            c = text[end_pos]
            if c in sentence_split_punctuation:
                break

def translate(
        source_english_filename: str,
        output_chinese_filename: str,
        start_chunk_no=1,
        chunks_to_translate=65535,
        temperature=0.6,
        max_token_per_request=1365) -> None:
    """
    Translate a text file from English to Simplified Chinese using OpenAI API.

    :param source_english_filename: Path to the input English text file.
    :param output_chinese_filename: Path to the output Simplified Chinese text file.
    :param start_chunk_no: The chunk number to start translating from.
    :param chunks_to_translate: The number of chunks to be translated.
    :param temperature: Controls the randomness of the AI's response.
    :param max_token_per_request: Maximum number of tokens allowed in one API call.
    """

    text = open(source_english_filename, encoding="utf-8").read()

    done = False
    start_pos = 0
    translated_chunks = 0
    current_chunk_no = 1
    total_tokens_consumed = 0

    # Skip the chunks before start_chunk_no
    while current_chunk_no < start_chunk_no:
        chunk_text, start_pos, _, done = get_next_chunk(text, start_pos)
        current_chunk_no += 1
    try:
        while not done and translated_chunks < chunks_to_translate:
            chunk_text, start_pos, _, done = get_next_chunk(text, start_pos, max_tokens=max_token_per_request)
            if not chunk_text.strip():
                continue
            start_time = time.time()
            print(f'Request to translate chunk: {current_chunk_no}...', end='', flush=True)
            translated_text, total_tokens = translate_text(chunk_text, temperature)
            current_chunk_no += 1
            translated_chunks += 1
            total_tokens_consumed += total_tokens
            end_time = time.time()
            print(f'Done...Takes {end_time - start_time:.2f} seconds')
            with open(output_chinese_filename, 'ab') as f:
                f.write(translated_text.encode('utf-8'))

            # print(f'English tokens: {english_tokens}')
            # if total_tokens >= 4096:
            #     print(f'Response has not enough tokens')
            # print(f'Chinese tokens: {total_tokens-english_tokens}')
            # print(f'Chinese token Magnification ratio: {(total_tokens-english_tokens) / english_tokens: .2f}')
    except Exception as e:
        print(f'Got Exception {e}')
    except KeyboardInterrupt:
        print('break')
    else:
        print('Translation completed.')
    finally:
        print(f'Stopped at chunk {current_chunk_no}, finished {chunks_to_translate} chunks')
        print(f'Token consumed: {total_tokens_consumed}, ${total_tokens_consumed / 1000 * 0.002:.3f} dollars.')

def get_arguments():
    """
    Parse command-line arguments.

    :return: Namespace object containing the parsed command-line arguments.
    """

    parser = argparse.ArgumentParser()
    parser.add_argument('--api-key', help='You OpenAPI Key', required=False)
    parser.add_argument('--api-base', help='You openAPI Base', required=False)
    parser.add_argument('--source', help='Filename of the book to be translated', required=True)
    parser.add_argument('--output', help='Filename of the translated output', required=True)
    parser.add_argument('--start', help='The chunk number to start', type=int, default=1)
    parser.add_argument('--chunks', help='The number of chunks to be translated', type=int, default=65536)
    parser.add_argument('--temperature', help="API's temperature parameter (0~2.0)", type=float, default=0.6)
    parser.add_argument('--tokens', help='Maximum number of English tokens in one API call', type=int, default=1365)

    args = parser.parse_args()
    return args

if __name__ == '__main__':
    arg = get_arguments()
    set_openapi_conf(arg.api_key, arg.api_base)
    if not openai.api_key:
        print('API KEY is not configured')
        exit(1)

    source_file = Path(arg.source)
    if not source_file.is_file():
        print(f'{arg.source} is not available')
        exit(1)

    translate(
        source_english_filename=arg.source,
        output_chinese_filename=arg.output,
        start_chunk_no=arg.start,
        chunks_to_translate=arg.chunks,
        temperature=arg.temperature,
        max_token_per_request=arg.tokens,
    )
