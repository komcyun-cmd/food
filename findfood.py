import streamlit as st
import pandas as pd
import requests
import re

st.set_page_config(page_title="네이버 찐맛집 탐색기", page_icon="💚", layout="wide")

def clean_html(raw_html):
    cleanr = re.compile('<.*?>')
    return re.sub(cleanr, '', raw_html)

def search_naver_api(client_id, client_secret, query):
    url = "https://openapi.naver.com/v1/search/local.json"
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret
    }
    
    all_data = []
    
    # 1~3페이지 (최대 15개씩 3번 = 45개)
    for start in [1, 16, 31]:
        params = {
            "query": query,
            "display": 15,
            "start": start,
            "sort": "comment"  # 리뷰 많은 순으로 정렬 (찐맛집 찾기 유리)
        }
        
        try:
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                items = response.json().get('items', [])
                if not items:
                    break
                    
                for item in items:
                    title = clean_html(item['title'])
                    category = item['category']
                    address = item['roadAddress'] or item['address']
                    link = item['link']
                    
                    # 네이버는 별점을 바로 안 줘서, 카테고리로 1차 필터
                    all_data.append({
                        "식당명": title,
                        "카테고리": category,
                        "주소": address,
                        "링크": link
                    })
            else:
                st.error(f"에러 코드 {response.status_code}: ID와 Secret을 확인해주세요.")
                return pd.DataFrame()
                
        except Exception as e:
            st.error(f"연결 실패: {e}")
            return pd.DataFrame()
            
    return pd.DataFrame(all_data)

# --- UI ---
st.title("💚 네이버 찐맛집 탐색기 (무료/개인용)")

with st.sidebar:
    st.header("설정")
    client_id = st.text_input("Naver Client ID", type="password")
    client_secret = st.text_input("Naver Client Secret", type="password")
    
    st.divider()
    query = st.text_input("검색어", value="대전 유성구 맛집")
    run_btn = st.button("검색 시작 🚀")

if run_btn:
    if not client_id or not client_secret:
        st.warning("설정창에 네이버 API 키 2개를 모두 넣어주세요!")
    else:
        with st.spinner("네이버 지도를 훑는 중..."):
            df = search_naver_api(client_id, client_secret, query)
            
            if not df.empty:
                st.success(f"🎉 총 {len(df)}개의 맛집을 찾았습니다!")
                
                # '음식점' 카테고리만 남기기 (카페 포함)
                # 네이버 카테고리 포맷: "음식점>한식", "카페,디저트" 등
                df_clean = df[df['카테고리'].str.contains("육류|한식|일식|중식|양식|분식|카페|요리", na=False)]
                
                st.dataframe(
                    df_clean,
                    column_config={
                        "링크": st.column_config.LinkColumn("네이버 정보 보기")
                    },
                    use_container_width=True
                )
            else:
                st.error("결과가 없습니다. 키 값을 확인하거나 검색어를 바꿔보세요.")
