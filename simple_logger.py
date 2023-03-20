import os
import datetime

class SimpleLogger:
    logfilename = '.chatgpt.log'

    @staticmethod
    def _get_ssh_remote_ip():
        ssh_connection = os.environ.get('SSH_CONNECTION')
        if ssh_connection:
            remote_ip = ssh_connection.split()[0]
            return remote_ip
        else:
            return 'Unknown'

    @staticmethod
    def _get_timestamp():
        now = datetime.datetime.now()
        formatted_timestamp = now.strftime("%Y-%m-%d %H:%M")
        return formatted_timestamp

    @staticmethod
    def log_answer(answer_text: str):
        with open(SimpleLogger.logfilename, 'a') as f:
            name = 'ChatGPT'
            f.write(f'{name:>15} {SimpleLogger._get_timestamp()}: {answer_text}\n')

    @staticmethod
    def log_prompt(user_text: str):
        with open(SimpleLogger.logfilename, 'a') as f:
            f.write(f'{SimpleLogger._get_ssh_remote_ip():>15} {SimpleLogger._get_timestamp()}: {user_text}\n')

    @staticmethod
    def log_error(error_text: str):
        with open(SimpleLogger.logfilename, 'a') as f:
            f.write(f'Got Exception: {SimpleLogger._get_timestamp()}: {error_text}\n')
