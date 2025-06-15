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
import json


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



def extract_and_remove_festival_ids(answer):
    """
    GPT 응답 문자열에서 JSON 형식의 festival_ids 정보를 추출하고 제거.
    """
    match = re.search(r'(\{[^{]*"festival_ids"\s*:\s*\[[^\]]*\][^}]*\})', answer)
    festival_ids = []
    if match:
        try:
            obj = json.loads(match.group(1))
            festival_ids = obj.get("festival_ids", [])
        except Exception as e:
            print("JSON 파싱 오류:", e)
        answer = answer.replace(match.group(1), '').strip()
    return festival_ids, answer


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
    festival_ids, clean_answer = extract_and_remove_festival_ids(result_part)
    festival_reviews = []
    for festival_id in festival_ids:
        festivalInfo = next((x for x in festivals if x['primary_key'] == festival_id), None)
        festival_reviews.append(festivalInfo)

    print(clean_answer, festival_reviews)
    return clean_answer, festival_reviews


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
    base_url = "http://apis.data.go.kr/B551011/KorService2/locationBasedList2"
    params = {
        "ServiceKey": "0jY3xlWlBSmUzyQgCRRlQ65QJHi779J5zYk+pLBZYIV+dqyGWr7HfYOo9WWDew18cxxhDTr109sYeb2DWP10pw==",
        "MobileOS": "ETC",
        "MobileApp": "MyApp",
        "mapX": lon,
        "mapY": lat,
        "radius": radius,
        "contentTypeId": "12",  # 관광지
        "numOfRows": num_of_rows,
        "pageNo": page_no,
        "_type": "json",
    }
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    }

    try:
        resp = requests.get(base_url, params=params, headers=headers, timeout=10, verify=False)

        # JSON 파싱 시 예외 대비
        try:
            data = resp.json()
        except json.JSONDecodeError:
            print("JSON 파싱 실패. 응답:", resp.text)
            return []

        if not isinstance(data, dict):
            print("JSON 응답이 dict 형식이 아님. 실제 타입:", type(data))
            return []

        items = data.get('response', {}).get('body', {}).get('items', {}).get('item', [])

        if not items:
            print("주변 콘텐츠 검색 결과 없음.")
            return []

        accommodations = []
        for it in items:
            acc = {
                "title": it.get("title"),
                "addr": it.get("addr1"),
                "addr_detail": it.get("addr2"),
                "tel": it.get("tel"),
                "map_lat": it.get("mapy"),
                "map_lon": it.get("mapx"),
                "first_image": it.get("firstimage") or it.get("firstImageUrl"),
            }
            accommodations.append(acc)

        print("주변 콘텐츠 검색 성공:", len(accommodations), "건")
        return accommodations

    except requests.RequestException as e:
        print(f"API 호출 중 네트워크 오류 발생: {e}")
    except Exception as e:
        print(f"알 수 없는 오류 발생: {e}")

    return []
