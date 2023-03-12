import os
import sys
import time
import openai
import tiktoken
import argparse

token_encoding = tiktoken.get_encoding("cl100k_base")

def set_openapi_conf(api_key, api_base):
    if api_key:
        openapi.api_key = api_key
    if api_base:
        openapi.api_base = api_base
        
    if not api_key:
        home_dir = os.path.expanduser("~")
        expected_apikey_filename = os.path.join(home_dir, '.apikey')
    
        if os.path.exists(expected_apikey_filename):
            openai.api_key_path = expected_apikey_filename
        elif os.path.exists('.apikey'):
            openai.api_key_path = '.apikey'
        else:
            print('apikey is not available')
            sys.exit(1)
    if not api_base:
        if os.path.exists('.apibase'):
            openai.api_base = open('.apibase').read().strip()
        else:
            expected_apibase_filename = os.path.join(home_dir, '.apibase')
            if os.path.exists(expected_apibase_filename):
                openai.api_base = open(expected_apibase_filename).read().strip()

def ask(user_text, temperature):
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
    response_text = response.choices[0].message.content
    total_tokens = response.usage.total_tokens
    return response_text, total_tokens

# def ask(user_text, temperature):
#     return user_text, get_tokens(user_text)

def get_tokens(text):
    return len(token_encoding.encode(text))

def get_next_split(text, start_pos, max_tokens=1365):
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
        while True and end_pos > 0:
            end_pos -= 1
            c = text[end_pos]
            if c in sentence_split_punctuation:
                break

def translate(
        source_english_filename: str, 
        output_chinese_filename: str,
        start_split_no=1,
        translate_limits=65535) -> None:
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
        while not done and translated_splits < translate_limits:
            splited_text, start_pos, _, done = get_next_split(text, start_pos)
            if not splited_text.strip():
                continue
            start_time = time.time()
            print(f'Request to translate split: {current_split_no}...', end='', flush=True)
            ret, total_tokens = ask(splited_text, 0.6)
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
        print(f'Stopped at split {current_split_no}, finished {translate_limits} splits')
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

    args = parser.parse_args()
    return args

arg = get_arguments()
set_openapi_conf(arg.id, arg.api)
translate(
    source_english_filename=arg.src,
    output_chinese_filename=arg.output,
    start_split_no=arg.start,
    translate_limits=arg.splits
)
