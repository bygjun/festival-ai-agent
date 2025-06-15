import streamlit as st
from core import search_festival_review, search_festival, geocode_address, search_nearby_contents
import re

def parse_clean_answer(clean_answer: str):
    result = {"intro": "", "items": [], "outro": ""}
    lines = clean_answer.strip().split("\n")
    current_item = []

    for idx, line in enumerate(lines):
        if re.match(r"^\d+\.\s", line):
            if current_item:
                result["items"].append("\n".join(current_item).strip())
                current_item = []
            current_item.append(line)
        elif current_item:
            current_item.append(line)
        elif not result["items"]:
            result["intro"] += line.strip() + "\n"

    if current_item:
        result["items"].append("\n".join(current_item).strip())

    if lines:
        result["outro"] = lines[-1].strip()
        if result["items"] and result["items"][-1].endswith(result["outro"]):
            result["items"][-1] = result["items"][-1].rsplit(result["outro"], 1)[0].strip()

    result["intro"] = result["intro"].strip()
    return result

# 세션 상태 초기화
if "search_query" not in st.session_state:
    st.session_state["search_query"] = ""

st.title("🎊 대한민국 축제 검색")

# 검색 입력 폼
with st.form(key="search_form"):
    input_query = st.text_input("축제를 검색하세요", value=st.session_state["search_query"])
    submitted = st.form_submit_button("검색")
    if submitted:
        st.session_state["search_query"] = input_query
        st.rerun()

# 검색 실행
query = st.session_state["search_query"]
if query:
    with st.spinner("🔍 축제를 찾는 중입니다..."):
        clean_answer, festivals = search_festival(query)
        parsed = parse_clean_answer(clean_answer)

        if parsed["intro"]:
            st.markdown(parsed["intro"])

        # items와 festivals를 인덱스 기반으로 확실하게 매핑
        for i, (item_text, fest) in enumerate(zip(parsed["items"], festivals)):
            title_match = re.match(r"\d+\.\s*(.+?)\s*\n", item_text)
            name = title_match.group(1).strip() if title_match else f"축제{i+1}"

            st.markdown("---")
            st.markdown(item_text)

        if parsed["outro"]:
            st.markdown(parsed["outro"])
