# ui.py
import gradio as gr
from core import search_festival, parse_and_render_festivals

chatbot_state = gr.State([])

def festival_chatbot(message, history):
    result_part, festivals = search_festival(message)
    html = parse_and_render_festivals(result_part)
    return html


def respond_and_update(message, history):
    history = history or []
    response = festival_chatbot(message, history)
    history.append((message, response))

    display = ""
    for _, bot_response in history:
        display += f"<div style='margin-bottom:12px'>{bot_response}</div>"
    return display, history

with gr.Blocks() as demo:
    gr.Markdown("# 🎉 축제 검색 챗봇")

    chatbot_state = gr.State([])

    with gr.Column():
        user_input = gr.Textbox(label="질문을 입력하세요", placeholder="예: 가을에 강원도에서 열리는 축제 알려줘")
        send_button = gr.Button("전송")

    chat_history = gr.HTML(label="응답")

    def respond_and_update(message, history):
        response = festival_chatbot(message, history)
        return response, []  

    send_button.click(respond_and_update, inputs=[user_input, chatbot_state], outputs=[chat_history, chatbot_state])



if __name__ == "__main__":
    demo.launch()