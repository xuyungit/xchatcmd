import os
import sys
import openai

home_dir = os.path.expanduser("~")
expected_apikey_filename = os.path.join(home_dir, '.apikey')
if os.path.exists(expected_apikey_filename):
    openai.api_key_path = expected_apikey_filename
elif os.path.exists('.apikey'):
    openai.api_key_path = '.apikey'
else:
    print('apikey is not available')
    sys.exit(1)

# possible system messages:
# You are a helpful assistant.
# You are ChatGPT, a large language model trained by OpenAI. Answer as concisely as possible. 
# You are a helpful advisor. Answer as concisely as possible.
# You are a helpful teacher. Answer as detailed as possible.
# available models: "gpt-3.5-turbo", "gpt-3.5-turbo-0301"

MODEL = "gpt-3.5-turbo"
system_message = 'You are a helpful teacher. Answer as detailed as possible..'

chat_history = [
    {"role": "system", "content": f"{system_message}"},
]
chat_total_tokens = 0

def append_user_message(user_text):
    chat_history.append({
        "role": "user",
        "content": f"{user_text}"
    })

def append_assistant_message(assistant_text, total_tokens):
    chat_history.append({
        "role": "assistant",
        "content": f"{assistant_text}"
    })
    global chat_total_tokens
    chat_total_tokens = total_tokens

def clear_context():
    global chat_history
    chat_history = [
        {"role": "system", "content": f"{system_message}"},
    ]
    global chat_total_tokens
    chat_total_tokens = 0

# ChatGPT 最大可以存储 4096 个 token
# 当前的实现是使用ChatGPT返回的token数量
def is_token_reached_max():
    return chat_total_tokens >= 4096

def trim_history():
    global chat_history
    if is_token_reached_max():
        chat_history = chat_history[:1] + chat_history[-10:]
        print(f'！！！注意：当前对话交互文字过多，现在仅保留最后5次交互。！！！\n建议适当时使用cls清除上下文，开始新的会话')

# Todo: add more parameters
def ask(user_text):
    append_user_message(user_text)

    response = openai.ChatCompletion.create(
      model = MODEL,
      messages = chat_history,
      request_timeout = 30,
      timeout = 30
    )
    response_text = response.choices[0].message.content
    total_tokens = response.usage.total_tokens
    append_assistant_message(response_text, total_tokens)
    return response_text

def get_input(prompt_mark, multiple_line=False):
    print(prompt_mark, end='')
    first_line = input()
    if first_line.strip() in ('cls', 'exit', 'bye', 'quit'):
        return first_line.strip()
    lines = [first_line]
    if multiple_line:
        while True:
            try:
                line = input()
                lines.append(line)
            except EOFError:
                print('  ')  # Eminate the ^D
                break
    return '\n'.join(lines)

multiline_mode = False
if '-m' in sys.argv:
    multiline_mode = True

print(f"欢迎使用ChatGPT，会话中使用bye退出，cls清除聊天上下文")
if multiline_mode:
    print('当前运行在多行模式下，输入完成后，另起一行按Ctrl+D来进行发送')

while True:
    try:
        user_text = get_input('You: ', multiline_mode)
        if len(user_text.strip()) == 0:
            continue
        if user_text.strip() == 'cls':
            clear_context()
            continue
        if user_text.strip() in ('exit', 'bye', 'quit'):
            print('bye')
            break
        if not multiline_mode:
            print(f'You:\n{user_text}', flush=True)
        response = ask(user_text)
        print(f"ChatGPT:\n{response}\n")
        trim_history()
    except KeyboardInterrupt:
        print('bye')
        break