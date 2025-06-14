import requests
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

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

def fetch_nearby_accommodations(lat, lon, radius=2000, num_of_rows=10, page_no=1):
    """
    한국관광공사 OpenAPI 위치기반 숙박정보 조회.
    - lat, lon: 위도, 경도 (float)
    - service_key: 발급받은 ServiceKey (URL 인코딩된 형태가 아닌, 원본 키를 requests가 자동 인코딩하게 함)
    - radius: 검색 반경(미터)
    - num_of_rows: 한 페이지 결과 개수
    - page_no: 페이지 번호
    """
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
    # 예시 실행
    address = input("주소를 입력하세요: ").strip()
    coords = geocode_address(address.strip())
    if not coords:
        print("주소를 좌표로 변환하지 못했습니다.")
    else:
        lat, lon = coords
        print(f"주소 '{address}'의 좌표: 위도={lat}, 경도={lon}")
        # ServiceKey: 공공데이터포털에서 발급받은 키를 입력
        # 예: 반경 1km 내 숙박 정보 20개
   