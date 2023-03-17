import os
import sys
import datetime
import openai
import tiktoken
from rich.console import Console
from rich.markdown import Markdown
from rich.live import Live
from rich.panel import Panel
from prompt_toolkit import prompt
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.validation import Validator
from prompt_toolkit.shortcuts import input_dialog
from prompt_toolkit.styles import Style
from prompt_toolkit.filters import (
    emacs_insert_mode,
    is_multiline,
    vi_insert_mode,
    in_paste_mode
)
from conf import set_openapi_conf

set_openapi_conf()

class ChatSession:
    def __init__(self, console: Console):

        # possible system messages:
        # You are a helpful assistant.
        # You are ChatGPT, a large language model trained by OpenAI. Answer as concisely as possible.
        # You are a helpful advisor. Answer as concisely as possible.
        # You are a helpful teacher. Answer as detailed as possible.
        # available models: "gpt-3.5-turbo", "gpt-3.5-turbo-0301"

        self.system_message: str = 'You are a helpful assistant.'
        self.chat_history = [
            {"role": "system", "content": f"{self.system_message}"},
        ]
        self.chat_total_tokens = 0
        self.temperature = 0.7
        self.model = "gpt-3.5-turbo"
        self.console = console

    def _get_tokens(self, text: str) -> int:
        token_encoding = tiktoken.get_encoding("cl100k_base")
        return len(token_encoding.encode(text))

    def _get_current_tokens(self):
        contents = [item['content'] for item in self.chat_history]
        tokens = [self._get_tokens(txt) for txt in contents]
        return sum(tokens)

    def append_user_message(self, user_text):
        self.chat_history.append({
            "role": "user",
            "content": f"{user_text}"
        })

    def append_assistant_message(self, assistant_text, total_tokens):
        self.chat_history.append({
            "role": "assistant",
            "content": f"{assistant_text}"
        })
        self.chat_total_tokens = total_tokens

    def clear_context(self):
        self.chat_history = [
            {"role": "system", "content": f"{self.system_message}"},
        ]
        self.chat_total_tokens = 0

    def change_system_message(self, text):
        if text is None:
            return
        if not text.strip():
            self.chat_history = []
        else:
            self.system_message = text
            self.chat_history = [
                {"role": "system", "content": f"{self.system_message}"},
            ]
        chat_total_tokens = 0

    def trim_history(self):
        if self.chat_total_tokens >= 4000 or self._get_current_tokens() > 4000:
            self.chat_history = self.chat_history[:1] + self.chat_history[-5:]
            while self._get_current_tokens() > 4000 and len(self.chat_history) > 2:
                chat_history = self.chat_history[:1] + self.chat_history[2:]
            return True
        return False

    def change_temperature(self, setting):
        if setting.startswith('t='):
            try:
                val = float(setting.split('=')[-1])
            except ValueError:
                return
            if 0 <= val <= 2:
                self.temperature = val

    def ask(self):
        response = openai.ChatCompletion.create(
            model = self.model,
            messages = self.chat_history,
            request_timeout = 120,
            timeout = 120,
            temperature = self.temperature
        )
        response_text = response.choices[0].message.content # type: ignore
        total_tokens = response.usage.total_tokens # type: ignore
        self.append_assistant_message(response_text, total_tokens)
        return response_text

class CmdSession:
    commands = ('cls', 'm', 's', 'bye', 'h')
    bindings = KeyBindings()
    insert_mode = vi_insert_mode | emacs_insert_mode

    @staticmethod
    def is_command(text):
        text = text.strip()
        if text.startswith('t='):
            return True
        if text in CmdSession.commands:
            return True

    @bindings.add('enter', filter=insert_mode & is_multiline)
    @staticmethod
    def _(event):
        if CmdSession.is_command(event.current_buffer.text):
            event.current_buffer.validate_and_handle()
        else:
            event.current_buffer.newline(copy_margin=not in_paste_mode())

    @staticmethod
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

    def box(self, message):
        self.console.print(Panel(message, expand=False))

    def get_input(self, prompt_mark):
        validator = Validator.from_callable(
            CmdSession.is_valid_cmd,
            error_message="非法命令，请输入h查看帮助",
            move_cursor_to_end=True
        )
        custom_style = Style.from_dict({
            'prompt': 'fg:#E0D562',  # Customize the prompt color
        })
        if not self.multiline_mode:
            return prompt(
                prompt_mark, validator=validator, validate_while_typing=False, style=custom_style
            ).strip()
        ret = prompt(
            prompt_mark, multiline=True, prompt_continuation="", key_bindings=CmdSession.bindings, style=custom_style
        )
        return ret

    def show_help_dialog(self):
        help_text = '''
    h: 显示帮助
    bye: 退出
    cls: 清除聊天上下文
    m: 切换多行模式
    s: 切换单行模式
    t=float_val: 设置Temperature参数。参数的取值范围为0~2，数值越小生成的文本越确定，数值越大随机性/创意/出错概率就越大
    '''
        self.box(help_text)

    def __init__(self):
        self.multiline_mode = False
        self.console = Console()

        self.multiline_mode = False
        if '-m' in sys.argv:
            multiline_mode = True
        self.colorful_mode = True
        if '-c' in sys.argv:
            self.colorful_mode = False

        self.logger = SimpleLogger()

    def switch_to_multiple_line_mode(self):
        self.multiline_mode = True
        self.box('当前运行在多行模式下，输入完成后，按Alt+Enter来进行发送。使用s命令切换到单行模式。')

    def switch_to_single_line_mode(self):
        self.multiline_mode = False
        self.box('当前运行在单行模式下，回车即发送。使用m命令切换到多行模式。')

    def start_chat(self):
        chat_session = ChatSession(self.console)
        welcome_message = f"""\
欢迎使用**ChatGPT**，会话中使用`h`显示帮助，`bye`退出，`cls`清除聊天上下文，`m`切换多行模式

可以使用`t=0.2`这样的方式设置`Temperature`参数。参数的取值范围为**0~2**，数值越小生成的文本越确定，数值越大随机性/创意/出错概率就越大。当前值为{chat_session.temperature}
        """
        welcome_message = Markdown(welcome_message, inline_code_lexer="auto", inline_code_theme="monokai")
        self.box(welcome_message)

        while True:
            try:
                user_text = self.get_input('You: ')
                if len(user_text.strip()) == 0:
                    continue
                if user_text.strip() == 'cls':
                    chat_session.clear_context()
                    self.box('聊天上下文已经清除。')
                    continue
                if user_text.strip() == 'm':
                    self.switch_to_multiple_line_mode()
                    continue
                if user_text.strip() == 's':
                    self.switch_to_single_line_mode()
                    continue
                if user_text.startswith('t='):
                    chat_session.change_temperature(user_text)
                    self.box(f'Temperature参数修改为{chat_session.temperature}')
                    continue
                if user_text.startswith('system='):
                    ret = input_dialog(
                        title="Change system prompt message",
                        text="Current System Message is",
                        default=chat_session.system_message
                    ).run()
                    chat_session.change_system_message(ret)
                    continue
                if user_text.strip() == 'h':
                    self.show_help_dialog()
                    continue
                if user_text.strip() in ('exit', 'bye', 'quit'):
                    self.box('bye')
                    break
                chat_session.append_user_message(user_text)
                trimmed = chat_session.trim_history()
                if trimmed:
                    self.box('注意：当前对话交互文字过多，现清除部分上下文。\n建议适当时使用cls清除上下文，开始新的会话')
                self.logger.log_prompt(user_text)
                if False:
                    handle_stream_output(chat_history)
                else:
                    with self.console.status("[bold green]Asking...", spinner="point") as status:
                        response = chat_session.ask()
                        self.logger.log_answer(response)
                        if self.colorful_mode:
                            self.console.print("[bold blue]ChatGPT[/bold blue]")
                            markdown = Markdown(response, inline_code_lexer="auto", inline_code_theme="monokai",)
                            self.console.print(markdown)
                        else:
                            print("ChatGPT")
                            print(response)
                        status.update("[bold green]Done!")
            except KeyboardInterrupt:
                self.box('bye')
                break


class SimpleLogger:
    @staticmethod
    def _get_remote_ip():
        ssh_connection = os.environ.get('SSH_CONNECTION')
        if ssh_connection:
            remote_ip = ssh_connection.split()[0]
            return remote_ip
        else:
            return 'Unknown'

    @staticmethod
    def _get_timestamp():
        now = datetime.datetime.now()
        formatted_time = now.strftime("%Y-%m-%d %H:%M")
        return formatted_time

    @staticmethod
    def log_answer(answer_text):
        with open('.chatgpt.log', 'a') as f:
            name = 'ChatGPT'
            f.write(f'{name:>15} {SimpleLogger._get_timestamp()}: {answer_text}\n')

    @staticmethod
    def log_prompt(user_text):
        with open('.chatgpt.log', 'a') as f:
            f.write(f'{SimpleLogger._get_remote_ip():>15} {SimpleLogger._get_timestamp()}: {user_text}\n')

if __name__ == '__main__':
    chatBot = CmdSession()
    chatBot.start_chat()
