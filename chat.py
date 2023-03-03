import openai

openai.api_key_path = 'apikey'

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

def append_user_message(user_text):
    chat_history.append({
        "role": "user",
        "content": f"{user_text}"
    })

def append_assistant_message(assistant_text):
    chat_history.append({
        "role": "assistant",
        "content": f"{assistant_text}"
    })

def clear_context():
    global chat_history
    chat_history = [
        {"role": "system", "content": f"{system_message}"},
    ]

# ChatGPT 最大可以存储 4096 个 token（大约16384个英文字母）的上下文，当一个会话的内容超出这个数量，最前面的信息就会被遗忘。
# 而 ChatGPT API 每次都要将完整的上下文传递过去，这意味着我们可以选择保留重要的信息，选择性地去掉一些无用的以避免超出限制。
# 对于中文的token的计算和英文不大一样，4096个token不意味着16384个中文字符。粗糙实现先暂定为7000个字符
def is_token_reached_max():
    global chat_history
    all_text = ''.join([item['content'] for item in chat_history])
    return len(all_text) > 7000

def trim_history():
    global chat_history
    if len(chat_history) > 30 or is_token_reached_max():
        chat_history = chat_history[:1] + chat_history[-10:]
        print(f'当前对话交互次数过多，现在仅保留最后5次交互，建议使用cls清除上下文，开始新的会话')

# Todo: add more parameters
def ask(user_text):
    append_user_message(user_text)

    response = openai.ChatCompletion.create(
      model = MODEL,
      messages = chat_history
    )
    response_text = response.choices[0].message.content
    append_assistant_message(response_text)
    return response_text

while True:
    try:
        user_text = input('> ')
        if len(user_text.strip()) == 0:
            continue
        if user_text == 'cls':
            clear_context()
            continue
        if user_text == 'bye':
            print('bye')
            break
        response = ask(user_text)
        print(f'You:\n{user_text}')
        print(f"ChatGPT:\n{response}")
        trim_history()
    except KeyboardInterrupt:
        print('bye')
        break