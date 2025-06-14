# ui.py
import gradio as gr
from core import search_festival, parse_and_render_festivals

chatbot_state = gr.State([])

def festival_chatbot(message, history):
    try:
        result_text, _ = search_festival(message)
        rendered_html = parse_and_render_festivals(result_text)
        return rendered_html
    except Exception as e:
        return f"<p style='color:red'>에러 발생: {str(e)}</p>"

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

    with gr.Column():  # ✅ 텍스트박스 아래에 버튼 위치
        user_input = gr.Textbox(label="질문을 입력하세요", placeholder="예: 가을에 강원도에서 열리는 축제 알려줘")
        send_button = gr.Button("전송")

    chat_history = gr.HTML(label="응답")

    def respond_and_update(message, history):
        response = festival_chatbot(message, history)
        return response, []  # ✅ 결과 덮어쓰기

    send_button.click(respond_and_update, inputs=[user_input, chatbot_state], outputs=[chat_history, chatbot_state])



if __name__ == "__main__":
    demo.launch()