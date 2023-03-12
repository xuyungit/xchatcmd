import os
import sys
import openai
import datetime
from rich.console import Console
from rich.markdown import Markdown
from rich.live import Live
from prompt_toolkit import prompt
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.shortcuts import message_dialog
from prompt_toolkit.validation import Validator
from prompt_toolkit.shortcuts import input_dialog
from prompt_toolkit.filters import (
    emacs_insert_mode,
    is_multiline,
    vi_insert_mode,
    in_paste_mode
)

home_dir = os.path.expanduser("~")
expected_apikey_filename = os.path.join(home_dir, '.apikey')

if os.path.exists(expected_apikey_filename):
    openai.api_key_path = expected_apikey_filename
elif os.path.exists('.apikey'):
    openai.api_key_path = '.apikey'
else:
    print('apikey is not available')
    sys.exit(1)

if os.path.exists('.apibase'):
    openai.api_base = open('.apibase').read().strip()
else:
    expected_apibase_filename = os.path.join(home_dir, '.apibase')
    if os.path.exists(expected_apibase_filename):
        openai.api_base = open(expected_apibase_filename).read().strip()

# possible system messages:
# You are a helpful assistant.
# You are ChatGPT, a large language model trained by OpenAI. Answer as concisely as possible. 
# You are a helpful advisor. Answer as concisely as possible.
# You are a helpful teacher. Answer as detailed as possible.
# available models: "gpt-3.5-turbo", "gpt-3.5-turbo-0301"

MODEL = "gpt-3.5-turbo"
# system_message = 'You are a helpful teacher. Answer as detailed as possible.'
system_message = 'You are a helpful assistant.'

chat_history = [
    {"role": "system", "content": f"{system_message}"},
]
chat_total_tokens = 0
temperature = 0.7

commands = ('cls', 'm', 's', 'bye', 'h')
bindings = KeyBindings()
insert_mode = vi_insert_mode | emacs_insert_mode

def is_command(text):
    text = text.strip()
    if text.startswith('t='):
        return True
    if text in commands:
        return True

@bindings.add('enter', filter=insert_mode & is_multiline)
def _(event):
    if is_command(event.current_buffer.text):
        event.current_buffer.validate_and_handle()
    else:
        event.current_buffer.newline(copy_margin=not in_paste_mode())

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

def change_system_message(text):
    if text is None:
        return
    global chat_history
    if not text.strip():
        chat_history = []
    else:
        global system_message
        system_message = text
        chat_history = [
            {"role": "system", "content": f"{system_message}"},
        ]
    global chat_total_tokens
    chat_total_tokens = 0
        
# ChatGPT 最大可以存储 4096 个 token
# 当前的实现是使用ChatGPT返回的token数量
def is_token_reached_max():
    return chat_total_tokens >= 4000

def trim_history():
    global chat_history
    if is_token_reached_max():
        chat_history = chat_history[:1] + chat_history[-10:]
        print(f'！！！注意：当前对话交互文字过多，现在仅保留最后5次交互。！！！\n建议适当时使用cls清除上下文，开始新的会话')

def get_remote_ip():
    ssh_connection = os.environ.get('SSH_CONNECTION')
    if ssh_connection:
        remote_ip = ssh_connection.split()[0]
        return remote_ip
    else:
        return 'Unknown'

def get_timestamp():
    now = datetime.datetime.now()                                                                                                                                                                                                   
    formatted_time = now.strftime("%Y-%m-%d %H:%M")                                                                                                                                                                                 
    return formatted_time

def log_answer(answer_text):
    with open('.chatgpt.log', 'a') as f:
        name = 'ChatGPT'
        f.write(f'{name:>15} {get_timestamp()}: {answer_text}\n')

def log_prompt(remote_ip, user_text):
    with open('.chatgpt.log', 'a') as f:
        f.write(f'{remote_ip:>15} {get_timestamp()}: {user_text}\n')

# Todo: add more parameters
def ask(user_text):
    append_user_message(user_text)
    log_prompt(get_remote_ip(), user_text)

    response = openai.ChatCompletion.create(
      model = MODEL,
      messages = chat_history,
      request_timeout = 120,
      timeout = 120,
      temperature = temperature
    )
    response_text = response.choices[0].message.content
    total_tokens = response.usage.total_tokens
    append_assistant_message(response_text, total_tokens)
    return response_text

def ask_stream(user_text):
    append_user_message(user_text)
    log_prompt(get_remote_ip(), user_text)

    response = openai.ChatCompletion.create(
      model = MODEL,
      messages = chat_history,
      request_timeout = 120,
      timeout = 120,
      temperature = temperature,
      stream=True
    )
    return response

def _print(text, render):
    content = text
    markdown = Markdown(
        content,
        inline_code_lexer="auto",
        inline_code_theme="monokai",
    )
    render(markdown)
    
def handle_stream_output(user_text):
    content = ""
    with Live("[bold green]Asking...", refresh_per_second=0.5) as live:
        response = ask_stream(user_text)
        for v in response:
            if v.choices and "content" in v.choices[0].delta and v.choices[0].delta.content:
                content += v.choices[0].delta.content
                _print(content, live.update)
        append_assistant_message(content, 0)
        
def is_valid_cmd(text):
    if text.strip().startswith('t='):
        try:
            val = float(text.split('=')[-1])
        except ValueError:
            return False
        if 0 <= val <= 2:
            return True
        else:
            return False
    return True    
        
def get_input(prompt_mark, multiple_line=False):
    validator = Validator.from_callable(
        is_valid_cmd,
        error_message="非法命令，请输入h查看帮助",
        move_cursor_to_end=True
    )
    if not multiple_line:
        return prompt(prompt_mark, validator=validator, validate_while_typing=False).strip()
    ret = prompt(prompt_mark, multiline=True, prompt_continuation="", key_bindings=bindings)
    return ret

def switch_to_multiple_line_mode():
    global multiline_mode
    multiline_mode = True
    print('当前运行在多行模式下，输入完成后，按Alt+Enter来进行发送。使用s命令切换到单行模式。')

def switch_to_single_line_mode():
    global multiline_mode
    multiline_mode = False
    print('当前运行在单行模式下，回车即发送。使用m命令切换到多行模式。')

def change_temperature(setting):
    if setting.startswith('t='):
        try:
            val = float(setting.split('=')[-1])
        except ValueError:
            print('非法设置')
            return
        if 0 <= val <= 2:
            global temperature
            temperature = val
            print(f'Temperature参数修改为{val}')
        else:
            print(f'Temperature参数的取值范围为0~2，数值越小生成的文本越确定，数值越大随机性/创意/出错概率就越大。当前值为{temperature}')

def show_help_dialog():
    help_text = '''
h: 显示帮助
bye: 退出
cls: 清除聊天上下文
m: 切换多行模式
s: 切换单行模式
t=float_val: 设置Temperature参数。参数的取值范围为0~2，数值越小生成的文本越确定，数值越大随机性/创意/出错概率就越大
Press ENTER to quit.
'''
    message_dialog(
        title='Help',
        text=help_text
    ).run()

console = Console()

multiline_mode = False
if '-m' in sys.argv:
    multiline_mode = True
colorful_mode = True
if '-c' in sys.argv:
    colorful_mode = False

print(f"欢迎使用ChatGPT，会话中使用h显示帮助，bye退出，cls清除聊天上下文，m切换多行模式")
print(f'可以使用t=0.2这样的方式设置Temperature参数。参数的取值范围为0~2，数值越小生成的文本越确定，数值越大随机性/创意/出错概率就越大。当前值为{temperature}')

if multiline_mode:
    switch_to_multiple_line_mode()

while True:
    try:
        user_text = get_input('You: ', multiline_mode)
        if len(user_text.strip()) == 0:
            continue
        if user_text.strip() == 'cls':
            clear_context()
            print('聊天上下文已经清除。')
            continue
        if user_text.strip() == 'm':
            switch_to_multiple_line_mode()
            continue
        if user_text.strip() == 's':
            switch_to_single_line_mode()
            continue
        if user_text.startswith('t='):
            change_temperature(user_text)
            continue
        if user_text.startswith('system='):
            ret = input_dialog(
                title="Change system prompt message",
                text="Current System Message is",
                default=system_message
            ).run()
            change_system_message(ret)
            continue
        if user_text.strip() == 'h':
            show_help_dialog()
            continue
        if user_text.strip() in ('exit', 'bye', 'quit'):
            print('bye')
            break
        if False:
            handle_stream_output(user_text)
        else:
            with console.status("[bold green]Asking...", spinner="point") as status:
                response = ask(user_text)
                log_answer(response)
                # print(f"ChatGPT:\n{response}\n")
                if colorful_mode:
                    console.print("[bold blue]ChatGPT[/bold blue]")
                    markdown = Markdown(response, inline_code_lexer="auto", inline_code_theme="monokai",)
                    console.print(markdown)
                else:
                    print("ChatGPT")
                    print(response)
                status.update("[bold green]Done!")
        trim_history()
    except KeyboardInterrupt:
        print('bye')
        break