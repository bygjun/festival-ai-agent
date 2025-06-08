
import gradio as gr
import openai
import re
from app.embedding import EmbeddingModel
from app.retriever import search_festivals
from app.prompt import build_system_message, build_assistant_message
from app import config

# Initialize
embedding_model = EmbeddingModel(config.EMBEDDING_MODEL)
openai.api_key = config.OPENAI_API_KEY

def render_festival_cards(text: list) -> str:

    text = text.strip()

    # 도입 문장: 첫 "1." 등장 전까지
    split_start = re.search(r"\n1\.\s+\*\*", text)
    if not split_start:
        return "<p>형식이 올바르지 않습니다.</p>"

    intro = text[:split_start.start()].strip()
    remainder = text[split_start.start():].strip()

    # 번호 패턴으로 축제 섹션 분할 (축제 개수 = sections - 1)
    sections = re.split(r"\n\d+\.\s+\*\*", remainder)

    cards = []
    outro = ""

    for i, section in enumerate(sections[1:]):
        content = "**" + section.strip()

        # 마지막 카드일 때 추가 문장 잘라내기
        if i == len(sections[1:]) - 1:

            lines = content.strip().split("\n")
            # 마지막 문장만 분리
            if len(lines) > 2 and not lines[-1].startswith("-"):
                outro = lines.pop(-1).strip()
            content = "\n".join(lines)

        # 카드 본문 HTML 변환
        html_body = content.replace("**", "<strong>").replace("\n", "<br>")

        card_html = f"""
        <div style='border:1px solid #e0e0e0; border-radius:12px; padding:20px; margin:12px 0;
                    background:linear-gradient(to right, #f9f9f9, #fcfcfc); box-shadow: 0 2px 5px rgba(0,0,0,0.05);'>
            {html_body}
            <div style='margin-top:12px;'>
                <button style='background-color:#4CAF50; color:white; border:none; padding:8px 16px;
                               border-radius:8px; cursor:pointer; margin-right:8px; font-weight:600;'>
                    숙소 보기
                </button>
                <button style='background-color:#2196F3; color:white; border:none; padding:8px 16px;
                               border-radius:8px; cursor:pointer; font-weight:600;'>
                    후기 보기
                </button>
            </div>
        </div>
        """
        cards.append(card_html)

    html = f"<p style='font-size:1.1em; font-weight:500; margin-bottom:16px;'>{intro}</p>"
    html += "".join(cards)
    if outro:
        html += f"<p style='font-size:1em; margin-top:24px; color:#555;'>{outro}</p>"

    return html

def festival_chatbot(message, history):
    try:
        query_embedding = embedding_model.get_embedding(message)
        results = search_festivals(config.MILVUS_COLLECTION, query_embedding, top_k=150)

        festivals = [r.get("entity") for r in results[0]]

        system_msg = build_system_message()
        assistant_msg = build_assistant_message(festivals, message)

        chat_input = [
            {"role": "system", "content": system_msg},
            {"role": "assistant", "content": assistant_msg}
        ]

        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=chat_input
        )
        answer = response["choices"][0]["message"]["content"]
        result_part = answer.split("결과:")[-1].strip()
        print("render::::" +result_part)
        return render_festival_cards( result_part)
    except Exception as e:
        return f"에러 발생: {str(e)}"



with gr.Blocks() as demo:
    gr.Markdown("# 🎉 축제 검색 챗봇")

    chatbot_state = gr.State([])

    with gr.Row():
        user_input = gr.Textbox(label="질문을 입력하세요", scale=6, placeholder="예: 가을에 강원도에서 열리는 축제 알려줘")
        send_button = gr.Button("전송", scale=1)

    chat_history = gr.HTML(label="응답")

    def respond_and_update(message, history):
        history = history or []
        response = festival_chatbot(message, history)
        history.append((message, response))
        display = ""
        for user, bot in history:
            display += f"<div style='margin-bottom:12px'>{bot}</div>"
        return display, history

    send_button.click(respond_and_update, inputs=[user_input, chatbot_state], outputs=[chat_history, chatbot_state])

demo.launch()
