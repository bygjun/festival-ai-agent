from flask import Flask, request, jsonify
from app.embedding import EmbeddingModel
from app.retriever import search_festivals
from app.prompt import build_system_message, build_assistant_message
import openai
from app.config import *
import os
import requests
from bs4 import BeautifulSoup
import re
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

embedding_model = EmbeddingModel(EMBEDDING_MODEL)
openai.api_key = OPENAI_API_KEY
print(OPENAI_API_KEY)


def remove_duplicate_spaces(text):
    return re.sub(r'\s+', ' ', text).strip()

def extract_text_from_url(url):
    try:
        response = requests.get(url, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        text = soup.get_text(separator='\n')
        text = remove_duplicate_spaces(text)
        return text
    except Exception as e:
        return ''
    
def search_keyword_by_web(keyword, skip=0, site=''):
    url = (
        "https://customsearch.googleapis.com/customsearch/v1"
        f"?cx=d7d1ee088fb2947ee"
        f"&q={requests.utils.quote(keyword)}"
        f"&key={os.getenv('GOOGLE_API_KEY_CUSTOMSEARCH', 'AIzaSyC6UcB9UMLkVsQWxlNt_YJAtRXOwOfgaxo')}"
        f"&start={skip}"
        f"&siteSearch={site}"
        f"&siteSearchFilter=i"
    )
    response = requests.get(url)
    data = response.json()
    return {
        "hasNextPage": data.get("queries", {}).get("nextPage", [{}])[0] if data.get("queries", {}).get("nextPage") else None,
        "list": data.get("items", [])
    }

def summarize_reviews_with_gpt(festival_name, reviews):
    prompt = f"아래는 '{festival_name}'에 대한 후기입니다. 핵심만 요약해줘.\n\n"
    for i, review in enumerate(reviews):
        prompt += f"[후기{i+1}]\n{review[:1000]}\n\n"
    response = openai.ChatCompletion.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return response["choices"][0]["message"]["content"]

def extract_festival_names(festivals):
    names = []
    for f in festivals:
        text = f.get('embedding_text', '')
        match = re.match(r'(.+?)은\(는\)', text)
        if match:
            names.append(match.group(1))
    return names

# def search_festival_reviews(user_query, festivals):
#     festival_reviews = []
#     for festival in festivals:
#         result = search_keyword_by_web(festival)
#         urls = [item['link'] for item in result['list']]
#         reviews = []
#         for url in urls[:3]:
#             text = extract_text_from_url(url)
#             if text:
#                 reviews.append(text)
#         summary = summarize_reviews_with_gpt(user_query, festival, reviews)
#         festival_reviews.append({
#             'festival_name': festival,
#             'review_summary': summary
#         })
#     return festival_reviews


def search_festival_review(festival_name):
    reviews = []
    result = search_keyword_by_web(festival_name)
    urls = [item['link'] for item in result['list']]
    for url in urls[:3]:
        text = extract_text_from_url(url)
        if text:
            reviews.append(text)
    summary = summarize_reviews_with_gpt(festival_name, reviews)
    return summary

def extract_used_festival_names(answer, festival_names):
    used = []
    for name in festival_names:
        if name in answer:
            used.append(name)
    return used

def extract_festival_names_and_addresses(festivals):
    result = []
    for f in festivals:
        text = f.get('embedding_text', '')
        # 축제명 추출
        name_match = re.match(r'(.+?)은\(는\)', text)
        # 주소 추출 (예: "경기도 성남시 중원구 둔촌대로 83번길에서" 패턴)
        addr_match = re.search(r'([가-힣0-9\s\-]+?에서)', text)
        if name_match and addr_match:
            name = name_match.group(1)
            # '에서' 제거
            addr = addr_match.group(1).replace('에서', '').strip()
            result.append({'name': name, 'address': addr})
    return result

def search_festival(user_query):
    query_embedding = embedding_model.get_embedding(user_query)
    results = search_festivals(MILVUS_COLLECTION, query_embedding, 150)
    festivals = [r.get('entity') for r in results[0]]
    system_msg = build_system_message()
    assistant_msg = build_assistant_message(festivals, user_query)
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "assistant", "content": assistant_msg}
    ]
    response = openai.ChatCompletion.create(
        model="gpt-4.1-mini",
        messages=messages
    )
    answer = response["choices"][0]["message"]["content"]
    result_part = answer.split("결과:")[-1].strip()
    
    return result_part, festivals
    

def geocode_address(address, user_agent="my_geocoder"):
    """
    주소 문자열을 받아 Nominatim으로부터 (위도, 경도) 튜플을 반환.
    실패 시 None을 반환.
    """
    geolocator = Nominatim(user_agent=user_agent)
    try:
        location = geolocator.geocode(address, timeout=10)
        if location:
            return (location.latitude, location.longitude)
    except (GeocoderTimedOut, GeocoderServiceError) as e:
        print(f"Geocoding error: {e}")
    return None


def search_nearby_contents(lon, lat, radius=2000, num_of_rows=10, page_no=1):

    # 엔드포인트 URL: 실제로 제공받은 Base URL/SWAGGER 문서 참고
    base_url = "http://apis.data.go.kr/B551011/KorService2/locationBasedList2"
    params = {
        "ServiceKey": "0jY3xlWlBSmUzyQgCRRlQ65QJHi779J5zYk+pLBZYIV+dqyGWr7HfYOo9WWDew18cxxhDTr109sYeb2DWP10pw==",
        "MobileOS": "ETC",
        "MobileApp": "MyApp",  # 앱 이름(임의 문자열)
        "mapX": lon,           # 경도
        "mapY": lat,           # 위도
        "radius": radius,      # 반경(미터)
        "_type": "json",       # JSON 형식 응답
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    try:
        resp = requests.get(base_url, params=params, headers=headers, timeout=10, verify=False)

        data = resp.json()
        print(data)
        # 응답 구조 예시: data['response']['body']['items']['item']가 리스트
        items = data.get('response', {}).get('body', {}).get('items', {}).get('item')
        if not items:
            print("검색 결과가 없습니다.")
            return []
        accommodations = []
        for it in items:
            # 주요 필드: 제목(title), 주소(addr1/addr2), 전화번호(tel), 위도(mapy), 경도(mapx), 이미지 대표(picURL 또는 firstImageUrl)
            acc = {
                "title": it.get("title"),
                "addr": it.get("addr1"),
                "addr_detail": it.get("addr2"),
                "tel": it.get("tel"),
                "map_lat": it.get("mapy"),
                "map_lon": it.get("mapx"),
                "first_image": it.get("firstimage") or it.get("firstImageUrl"),  # 필드명은 API 버전에 따라 다를 수 있음
                # 필요에 따라 추가 필드 추출
            }
            accommodations.append(acc)
        return accommodations
    except requests.RequestException as e:
        print(f"API 호출 중 오류 발생: {e}")
    except ValueError as e:
        print(f"JSON 파싱 오류: {e}")
    return []

if __name__ == "__main__":
    result = search('서울 먹거리 축제')
    print(result)   
    