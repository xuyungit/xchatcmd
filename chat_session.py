import openai
import tiktoken

from conf import set_openapi_conf

class ChatSession:
    """
    A class to manage chat sessions with an AI assistant using the OpenAI API.
    """
    def __init__(self):
        """
        Initializes a ChatSession object with default values for system message, chat history,
        total tokens, temperature, and model.
        """
        # possible system messages:
        # You are a helpful assistant.
        # You are ChatGPT, a large language model trained by OpenAI. Answer as concisely as possible.
        # You are a helpful advisor. Answer as concisely as possible.
        # You are a helpful teacher. Answer as detailed as possible.
        # available models: "gpt-3.5-turbo", "gpt-3.5-turbo-0301"

        self.MAX_TOKEN = 4000
        self.system_message: str = 'You are a helpful assistant.'
        self.chat_history = [
            {"role": "system", "content": f"{self.system_message}"},
        ]
        self.chat_total_tokens = 0
        self.temperature = 0.7
        self.model = "gpt-3.5-turbo"
        set_openapi_conf()

    def _count_tokens(self, text: str) -> int:
        """
        Counts the number of tokens in the given text.

        Args:
            text (str): The text to count tokens for.

        Returns:
            int: The number of tokens in the text.
        """
        token_encoding = tiktoken.get_encoding("cl100k_base")
        return len(token_encoding.encode(text))

    def _count_current_tokens(self):
        """
        Counts the total number of tokens in the current chat history.

        Returns:
            int: The total number of tokens in the chat history.
        """
        return sum(self._count_tokens(item['content']) for item in self.chat_history)

    def append_user_message(self, user_text):
        """
        Appends a user message to the chat history.

        Args:
            user_text (str): The user's message to add to the chat history.
        """
        if user_text.strip():
            self.chat_history.append({
                "role": "user",
                "content": user_text
            })

    def append_assistant_message(self, assistant_text, total_tokens):
        """
        Appends an assistant message to the chat history and updates the total tokens.

        Args:
            assistant_text (str): The assistant's message to add to the chat history.
            total_tokens (int): The updated total tokens after receiving the assistant's message.
        """
        self.chat_history.append({
            "role": "assistant",
            "content": f"{assistant_text}"
        })
        self.chat_total_tokens = total_tokens

    def clear_context(self):
        """
        Clears the chat history except for the system message and resets the total tokens.
        """
        self.chat_history = [
            {"role": "system", "content": f"{self.system_message}"},
        ]
        self.chat_total_tokens = 0

    def change_system_message(self, text):
        """
        Changes the system message and clears the chat history, keeping only the new system message.

        Args:
            text (str): The new system message text.
        """
        if text is None:
            return
        if not text.strip():
            self.chat_history = []
        else:
            self.system_message = text
            self.chat_history = [
                {"role": "system", "content": f"{self.system_message}"},
            ]
        self.chat_total_tokens = 0

    def trim_history(self):
        """
        Trims the chat history if the token count exceeds the limit (4000 by default).

        Returns:
            bool: True if the chat history was trimmed, False otherwise.
        """
        if self.chat_total_tokens >= self.MAX_TOKEN or self._count_current_tokens() > self.MAX_TOKEN:
            self.chat_history = self.chat_history[:1] + self.chat_history[-5:]
            while self._count_current_tokens() > self.MAX_TOKEN and len(self.chat_history) > 2:
                self.chat_history = self.chat_history[:1] + self.chat_history[2:]
            return True
        return False

    def change_temperature(self, setting):
        """
        Changes the temperature setting for the AI model's response generation.

        Args:
            setting (str): A string in the format 't=<value>', where <value> is a float between 0 and 2.
        """
        if setting.startswith('t='):
            try:
                val = float(setting.split('=')[-1])
            except ValueError:
                return
            if 0 <= val <= 2:
                self.temperature = val

    def ask(self, user_text):
        """
        Sends the chat history to the OpenAI API and retrieves the AI assistant's response.

        Args:
            user_text (str): The user's message to send to the OpenAI API.
        Returns:
            str: The AI assistant's response text.
        """
        self.append_user_message(user_text)

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

    def ask_stream(self, user_text: str) -> str:
        
        self.append_user_message(user_text)

        response = openai.ChatCompletion.create(
            model = self.model,
            messages = self.chat_history,
            request_timeout = 120,
            timeout = 120,
            temperature = self.temperature,
            stream=True
        )
        content = ''
        for v in response:
            if v.choices and "content" in v.choices[0].delta and v.choices[0].delta.content:  # type: ignore
                content += v.choices[0].delta.content  # type: ignore
                yield content # type: ignore
        if content:
            self.append_assistant_message(content, self._count_current_tokens())