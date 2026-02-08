import streamlit as st
import pandas as pd
import requests

# --- 설정 ---
st.set_page_config(page_title="나만의 찐맛집 탐색기 (API ver)", page_icon="⚡", layout="wide")

def search_kakao_api(api_key, query, x=None, y=None, radius=None):
    """
    카카오 로컬 API를 사용하여 검색 결과를 가져옵니다.
    """
    base_url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    headers = {"Authorization": f"KakaoAK {api_key}"}
    
    all_data = []
    
    # 1페이지부터 3페이지까지 (최대 45개) - API 제약상 45개가 최대 효율
    for page in range(1, 4):
        params = {
            "query": query,
            "page": page,
            "size": 15,  # 한 페이지당 최대 갯수
            "sort": "accuracy" # 정확도순
        }
        # 만약 좌표 중심 검색이라면 추가
        if x and y and radius:
            params.update({"x": x, "y": y, "radius": radius})

        try:
            response = requests.get(base_url, headers=headers, params=params)
            
            if response.status_code == 200:
                result = response.json()
                documents = result.get('documents', [])
                
                if not documents:
                    break # 더 이상 데이터 없으면 중단
                
                for place in documents:
                    all_data.append({
                        "식당명": place.get('place_name'),
                        "카테고리": place.get('category_name'),
                        "전화번호": place.get('phone'),
                        "주소": place.get('road_address_name') or place.get('address_name'),
                        "지도링크": place.get('place_url'),
                        "X": place.get('x'), # 경도
                        "Y": place.get('y')  # 위도
                    })
                
                # 마지막 페이지인지 확인
                if result.get('meta', {}).get('is_end'):
                    break
            else:
                st.error(f"API 요청 실패 (코드 {response.status_code}): API 키를 확인해주세요.")
                return pd.DataFrame()
                
        except Exception as e:
            st.error(f"에러 발생: {e}")
            return pd.DataFrame()
            
    return pd.DataFrame(all_data)

# --- UI 구성 ---
st.title("⚡ 나만의 찐맛집 탐색기 (공식 API 버전)")
st.markdown("더 이상 크롤링 막힐 걱정 없습니다. **카카오 REST API 키**를 넣어주세요.")

# 사이드바 설정
with st.sidebar:
    st.header("🔑 설정")
    # API 키 입력받기 (보안을 위해 password 타입으로)
    api_key = st.text_input("카카오 REST API 키", type="password", help="developers.kakao.com > 내 애플리케이션 > REST API 키")
    
    st.divider()
    
    st.header("🔍 검색")
    query = st.text_input("검색어 (예: 대전 유성구 맛집)", value="대전 유성구 맛집")
    
    run_btn = st.button("데이터 가져오기 🚀")

# 메인 로직
if run_btn:
    if not api_key:
        st.warning("⚠️ 먼저 왼쪽 사이드바에 'REST API 키'를 입력해주세요!")
    else:
        with st.spinner("카카오 서버에서 데이터를 가져오는 중..."):
            df = search_kakao_api(api_key, query)
            
            if not df.empty:
                st.success(f"✅ 총 {len(df)}개의 장소를 찾았습니다!")
                
                # 카테고리 필터링 (맛집만 남기기 위해)
                # 카카오 카테고리는 "음식점 > 한식 > ..." 형태임
                is_restaurant = df['카테고리'].str.contains("음식점|카페|술집", na=False)
                df_filtered = df[is_restaurant]
                
                st.markdown(f"### 🍽️ '{query}' 검색 결과")
                
                # 데이터프레임 출력 (링크 클릭 가능)
                st.dataframe(
                    df_filtered,
                    column_config={
                        "지도링크": st.column_config.LinkColumn("카카오맵 보기")
                    },
                    use_container_width=True
                )
                
                # CSV 다운로드
                st.download_button(
                    label="CSV로 결과 다운로드",
                    data=df_filtered.to_csv(index=False).encode('utf-8-sig'),
                    file_name=f"{query}_결과.csv",
                    mime='text/csv'
                )
            else:
                st.error("결과가 없습니다. API 키가 정확한지, 검색어가 올바른지 확인해주세요.")
