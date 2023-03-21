import sys
from typing import Union
from rich.console import Console
from rich.markdown import Markdown
from rich.live import Live
from rich.panel import Panel
from prompt_toolkit import prompt
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding import KeyPressEvent
from prompt_toolkit.validation import Validator
from prompt_toolkit.shortcuts import input_dialog
from prompt_toolkit.styles import Style
from prompt_toolkit.filters import (
    emacs_insert_mode,
    is_multiline,
    vi_insert_mode,
    in_paste_mode
)
from chat_session import ChatSession
from simple_logger import SimpleLogger

class CmdSession:
    commands = ('cls', 'm', 's', 'bye', 'h')
    bindings = KeyBindings()
    insert_mode = vi_insert_mode | emacs_insert_mode

    def __init__(self):
        self.console = Console()
        self.stream_mode = False
        self.multiline_mode = False
        if '-m' in sys.argv:
            self.multiline_mode = True
        self.colorful_mode = True
        if '-c' in sys.argv:
            self.colorful_mode = False
        if '-s' in sys.argv:
            self.stream_mode = True

        self.logger = SimpleLogger()

    @staticmethod
    def is_command(text: str) -> bool:
        text = text.strip()
        if text.startswith('t='):
            return True
        if text in CmdSession.commands:
            return True
        return False

    @staticmethod
    @bindings.add('enter', filter=insert_mode & is_multiline)
    def _(event: KeyPressEvent):
        if CmdSession.is_command(event.current_buffer.text):
            event.current_buffer.validate_and_handle()
        else:
            event.current_buffer.newline(copy_margin=not in_paste_mode())

    @staticmethod
    def is_valid_cmd(text: str):
        if text.strip().startswith('t='):
            try:
                val = float(text.split('=')[-1])
            except ValueError:
                return False
            return 0 <= val <= 2
        return True

    def box(self, message: Union[str, Markdown], title=''):
        self.console.print(Panel(message, expand=False, title=title))

    def get_input(self, prompt_mark: str):
        validator = Validator.from_callable(
            CmdSession.is_valid_cmd,
            error_message="Illegal command. Please enter 'h' to view help.",
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

    def show_help(self, title=''):
        help_text = '''
    h: Display Help
    bye: Quit
    cls: Clear Chat Context
    m: Switch to multiple line mode
    s: Switch to single line mode
    t=0.7: Set Temperature of API (0-2)
    system=: Change system prompt
    '''
        self.box(help_text, title)

    def switch_to_multiple_line_mode(self):
        self.multiline_mode = True
        self.box('Multiple Line Mode, use Alt+Enter to send. Use s to switch back to Single Line Mode.')

    def switch_to_single_line_mode(self):
        self.multiline_mode = False
        self.box('Single Line Mode, use Enter to send. Use m to switch back to Multiple Line Mode.')

    def handle_cls_command(self, chat_session: ChatSession):
        chat_session.clear_context()
        self.box('chat context cleared.')

    def handle_m_command(self):
        self.switch_to_multiple_line_mode()

    def handle_s_command(self):
        self.switch_to_single_line_mode()

    def handle_t_command(self, user_text: str, chat_session: ChatSession):
        chat_session.change_temperature(user_text)
        self.box(f'Temperature is set to {chat_session.temperature}')

    def handle_system_command(self, chat_session):
        ret = input_dialog(
            title="Change system prompt message",
            text="Current System Message is",
            default=chat_session.system_message
        ).run()
        chat_session.change_system_message(ret)

    def handle_h_command(self):
        self.show_help()

    def handle_exit_command(self):
        self.box('Bye')

    def handle_stream_output(self, chat_session: ChatSession, user_text: str):
        response = chat_session.ask_stream(user_text)
        self.console.print("[bold blue]ChatGPT[/bold blue]")
        with Live("[bold green]Asking...", refresh_per_second=0.5) as live:
            for r in response:
                markdown = Markdown(r, inline_code_lexer="auto", inline_code_theme="monokai")
                live.update(markdown)

    def handle_output(self, user_text, chat_session):
        with self.console.status("[bold green]Asking...", spinner="point") as status:
            response = chat_session.ask(user_text)
            self.logger.log_answer(response)
            if self.colorful_mode:
                self.console.print("[bold blue]ChatGPT[/bold blue]")
                markdown = Markdown(response, inline_code_lexer="auto", inline_code_theme="monokai",)
                self.console.print(markdown)
            else:
                print("ChatGPT")
                print(response)
            status.update("[bold green]Done!")

    def process_user_text(self, user_text: str, chat_session: ChatSession):
        trimmed = chat_session.trim_context()
        if trimmed:
            self.box('[bold red]Attention: The context of chat is too long, some context has been cleared.[/bold red]\n'
                'To clear the remaining context, you can use the command "cls".')
        self.logger.log_prompt(user_text)
        if self.stream_mode:
            try:
                self.handle_stream_output(chat_session, user_text)
            except Exception as e:
                self.logger.log_error(str(e))
                raise e
        else:
            try:
                self.handle_output(user_text, chat_session)
            except Exception as e:
                self.logger.log_error(str(e))
                raise e

    def start_chat(self):
        chat_session = ChatSession()
        self.show_help(title='Welcome to ChatGPT')

        while True:
            try:
                user_text = self.get_input('You: ')
                if len(user_text.strip()) == 0:
                    continue
                if user_text.strip() == 'cls':
                    self.handle_cls_command(chat_session)
                    continue
                if user_text.strip() == 'm':
                    self.handle_m_command()
                    continue
                if user_text.strip() == 's':
                    self.handle_s_command()
                    continue
                if user_text.startswith('t='):
                    self.handle_t_command(user_text, chat_session)
                    continue
                if user_text.startswith('system='):
                    self.handle_system_command(chat_session)
                    continue
                if user_text.strip() == 'h':
                    self.handle_h_command()
                    continue
                if user_text.strip() in ('exit', 'bye', 'quit'):
                    self.handle_exit_command()
                    break

                self.process_user_text(user_text, chat_session)
            except KeyboardInterrupt:
                self.box('bye')
                break


if __name__ == '__main__':
    chatBot = CmdSession()
    chatBot.start_chat()
