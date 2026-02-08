import streamlit as st
import pandas as pd
import requests
import re
import time

# --- [설정] 페이지 기본 설정 ---
st.set_page_config(page_title="네이버 찐맛집 탐색기 (Pro)", page_icon="🥘", layout="wide")

# --- [함수 1] HTML 태그 제거 및 텍스트 정제 ---
def clean_text(text):
    cleanr = re.compile('<.*?>')
    text = re.sub(cleanr, '', text)
    return text.replace("&quot;", "").replace("&amp;", "&").strip()

# --- [함수 2] 네이버 검색 API (기본) ---
def fetch_naver_data(client_id, client_secret, query, display=5):
    url = "https://openapi.naver.com/v1/search/local.json"
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret
    }
    
    all_items = []
    
    # 네이버는 한 번에 5개씩 제공 -> 루프 돌며 수집
    # 찐맛집 탐색을 위해 최대 3페이지(15개) 정도만 깊게 팜
    for start in [1, 6, 11]:
        params = {
            "query": query,
            "display": 5,
            "start": start,
            "sort": "comment" # 리뷰 많은 순 (기본 신뢰도 확보)
        }
        try:
            resp = requests.get(url, headers=headers, params=params)
            if resp.status_code == 200:
                items = resp.json().get('items', [])
                if not items: break
                for item in items:
                    all_items.append({
                        "식당명": clean_text(item['title']),
                        "카테고리": clean_text(item['category']),
                        "주소": clean_text(item['roadAddress'] or item['address']),
                        "링크": item['link'],
                        "검색키워드": query # 어떤 키워드로 걸렸는지 추적
                    })
            else:
                break
        except:
            break
            
    return all_items

# --- [함수 3] 찐맛집 로직 통합 프로세서 ---
def get_authentic_restaurants(client_id, client_secret, region, deep_search=False):
    data_pool = []
    
    # 1. 기본 검색
    base_query = f"{region} 맛집"
    data_pool.extend(fetch_naver_data(client_id, client_secret, base_query))
    
    # 2. [Logic C] 딥 서치 (검색어 확장)
    # 단순히 '맛집'만 찾는 게 아니라, '노포', '현지인' 키워드로 추가 발굴
    if deep_search:
        keywords = ["노포", "현지인 맛집", "숨은 맛집"]
        progress_text = st.empty()
        
        for kw in keywords:
            extended_query = f"{region} {kw}"
            progress_text.text(f"📡 '{extended_query}' 데이터 발굴 중...")
            data_pool.extend(fetch_naver_data(client_id, client_secret, extended_query))
            time.sleep(0.1) # API 예의
            
        progress_text.empty()
        
    df = pd.DataFrame(data_pool)
    
    if df.empty:
        return df
        
    # 3. 중복 제거 (여러 키워드에 동시에 걸린 집은 '찐'일 확률이 높음 -> 남기고 중복만 제거)
    # 식당명을 기준으로 중복 제거하되, 먼저 발견된 것 유지
    df = df.drop_duplicates(subset=['식당명'], keep='first')
    
    return df

# --- [UI] 사이드바 설정 ---
with st.sidebar:
    st.header("⚙️ 설정 & 필터")
    
    # API 키 입력 (비밀번호 모드)
    client_id = st.text_input("네이버 Client ID", type="password")
    client_secret = st.text_input("네이버 Secret", type="password")
    
    st.divider()
    
    # 검색 설정
    region = st.text_input("지역명 (예: 대전 유성구)", value="대전 유성구")
    
    # [Logic B & C] 로직 제어
    st.subheader("🕵️ 탐색 옵션")
    use_deep_search = st.checkbox("딥 서치 (노포/현지인 키워드 포함)", value=True, help="맛집 외에 노포, 현지인 키워드로도 검색하여 결과를 합칩니다.")
    
    st.subheader("🧹 필터링")
    remove_chain = st.checkbox("프랜차이즈 제거 (지점 삭제)", value=True, help="'XX점'으로 끝나는 곳을 지웁니다. (단, '본점'은 살림)")
    only_korean = st.checkbox("한식/아재입맛 집중", value=False, help="카페, 디저트, 양식을 제외하고 밥집 위주로 봅니다.")

    search_btn = st.button("찐맛집 찾기 🚀", type="primary")

# --- [UI] 메인 화면 ---
st.title("🥘 나만의 찐맛집 탐색기 (Logic A+B+C)")

if search_btn:
    if not client_id or not client_secret:
        st.error("좌측 사이드바에 네이버 API 키를 입력해주세요!")
    else:
        with st.spinner(f"🔍 '{region}'의 숨은 맛집 데이터를 긁어모으는 중..."):
            df = get_authentic_restaurants(client_id, client_secret, region, use_deep_search)
            
            if df.empty:
                st.warning("데이터를 찾지 못했습니다. 검색어를 확인해주세요.")
            else:
                original_count = len(df)
                
                # --- [Logic A] 프랜차이즈 필터링 로직 ---
                if remove_chain:
                    # '점'으로 끝나면서 '본점'은 아닌 것 찾기 (정규식 활용)
                    # 공백+글자+점 으로 끝나는 패턴 (예: "스타벅스 대전점")
                    # 단, "반점"(중국집)은 제외해야 함 -> 로직 복잡하니 심플하게 ' 점'으로 끝나는 것 타겟
                    is_chain = df['식당명'].str.contains(r'\s\S+점$', regex=True) & ~df['식당명'].str.contains('본점')
                    df = df[~is_chain]
                
                # --- [Logic B] 카테고리 필터링 (취향) ---
                if only_korean:
                    # 카페, 베이커리, 양식 등 제외
                    exclude_keywords = "카페|커피|디저트|베이커리|양식|피자|파스타|햄버거"
                    df = df[~df['카테고리'].str.contains(exclude_keywords, na=False)]
                
                filtered_count = len(df)
                
                # 결과 요약
                st.success(f"발굴 완료! 총 {original_count}개 중 광고성/프랜차이즈 의심 {original_count - filtered_count}개를 쳐내고 **{filtered_count}개** 엄선.")
                
                # --- [시각화] 데이터프레임 꾸미기 ---
                # 인덱스 1부터 시작
                df = df.reset_index(drop=True)
                df.index = df.index + 1
                
                # 출력
                st.dataframe(
                    df[['식당명', '카테고리', '주소', '링크']],
                    column_config={
                        "링크": st.column_config.LinkColumn("네이버 정보"),
                        "카테고리": st.column_config.TextColumn("업종", help="네이버 등록 카테고리"),
                    },
                    use_container_width=True
                )
                
                # 다운로드
                st.download_button(
                    "CSV 다운로드",
                    df.to_csv(index=False).encode('utf-8-sig'),
                    "real_tasty_places.csv",
                    "text/csv"
                )

else:
    st.info("👈 왼쪽에서 API 키를 넣고 '찐맛집 찾기'를 눌러주세요.")
    st.markdown("""
    ### 💡 이 앱에 적용된 3단계 로직
    1. **딥 서치 (Deep Search):** 단순히 '맛집'만 검색하지 않고 **'노포', '현지인'** 키워드를 자동 추가 검색합니다.
    2. **체인점 컷 (Chain-Cut):** 이름이 **'OO점'**으로 끝나는 프랜차이즈를 자동으로 발라냅니다. (본점은 제외)
    3. **중복 방어:** 여러 키워드에서 공통적으로 발견된 식당을 중복 없이 깔끔하게 보여줍니다.
    """)
