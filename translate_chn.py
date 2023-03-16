import time
import argparse
import openai
import tiktoken
from conf import set_openapi_conf

def ask(user_text: str, temperature: float):
    MODEL = "gpt-3.5-turbo"
    response = openai.ChatCompletion.create(
      model = MODEL,
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
    token_encoding = tiktoken.get_encoding("cl100k_base")
    return len(token_encoding.encode(text))

def get_next_split(text: str, start_pos: int, max_tokens=1365):
    sentence_split_punctuation = '.!?'
    # Let's assume that each token has 6 character length on average
    end_pos = min(len(text) - 1, start_pos + max_tokens * 6)
    done = False
    while True:
        ret = text[start_pos:end_pos+1]
        tokens = get_tokens(ret)
        if tokens <= max_tokens:
            if end_pos == len(text) - 1:
                done = True
            return ret, end_pos + 1, tokens, done
        # search backwards for a sentence
        while end_pos > 0:
            end_pos -= 1
            c = text[end_pos]
            if c in sentence_split_punctuation:
                break

def translate(
        source_english_filename: str,
        output_chinese_filename: str,
        start_split_no=1,
        splits_to_translate=65535,
        temperature=0.6,
        max_token_per_request=1365) -> None:

    text = open(source_english_filename, encoding="utf-8").read()

    done = False
    start_pos = 0
    translated_splits = 0
    current_split_no = 1
    total_tokens_used = 0

    # Skip the splits before start_split_no
    while current_split_no < start_split_no:
        splited_text, start_pos, _, done = get_next_split(text, start_pos)
        current_split_no += 1
    try:
        while not done and translated_splits < splits_to_translate:
            splited_text, start_pos, _, done = get_next_split(text, start_pos, max_tokens=max_token_per_request)
            if not splited_text.strip():
                continue
            start_time = time.time()
            print(f'Request to translate split: {current_split_no}...', end='', flush=True)
            ret, total_tokens = ask(splited_text, temperature)
            current_split_no += 1
            translated_splits += 1
            total_tokens_used += total_tokens
            end_time = time.time()
            print(f'Done...Takes {end_time - start_time:.2f} seconds')
            with open(output_chinese_filename, 'ab') as f:
                f.write(ret.encode('utf-8'))

            # print(f'English tokens: {english_tokens}')
            # if total_tokens >= 4096:
            #     print(f'Response has not enough tokens')
            # print(f'Chinese tokens: {total_tokens-english_tokens}')
            # print(f'Chinese token Magnification ratio: {(total_tokens-english_tokens) / english_tokens: .2f}')
    except Exception as e:
        print(f'Got Exception {e}')
    except KeyboardInterrupt:
        print('break')
    finally:
        print(f'Stopped at split {current_split_no}, finished {splits_to_translate} splits')
        print(f'Token used: {total_tokens_used}, ${total_tokens_used / 1000 * 0.002:.3f} dollars.')

def get_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--id', help='You OpenAPI Key', required=False)
    parser.add_argument('--api', help='You openAPI Base', required=False)
    parser.add_argument('--src', help='Filename of the book to be translated', required=True)
    parser.add_argument('--output', help='Filename of the translated output', required=True)
    parser.add_argument('--start', help='The split number to start', type=int, default=1)
    parser.add_argument('--splits', help='The number of splits to be translated', type=int, default=65536)
    parser.add_argument('--temperature', help="API's temperature parameter (0~2.0)", type=float, default=0.6)
    parser.add_argument('--tokens', help='Maximum number of English tokens in one API call', type=int, default=1365)

    args = parser.parse_args()
    return args

if __name__ == '__main__':
    arg = get_arguments()
    set_openapi_conf(arg.id, arg.api)
    if not openai.api_key:
        print('API KEY is not configured')
        exit(1)
    translate(
        source_english_filename=arg.src,
        output_chinese_filename=arg.output,
        start_split_no=arg.start,
        splits_to_translate=arg.splits,
        temperature=arg.temperature,
        max_token_per_request=arg.tokens,
    )
