import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="맛집 탐색기 (디버깅 모드)", page_icon="🐞", layout="wide")

st.title("🐞 에러 진단 모드")
st.info("이 코드는 카카오가 거절하는 '진짜 이유'를 화면에 표시해줍니다.")

# 사이드바
with st.sidebar:
    api_key = st.text_input("카카오 REST API 키", type="password")
    query = st.text_input("검색어", value="대전 유성구 맛집")
    run_btn = st.button("진단 시작 🚑")

if run_btn:
    if not api_key:
        st.warning("키를 입력해주세요.")
    else:
        url = "https://dapi.kakao.com/v2/local/search/keyword.json"
        headers = {"Authorization": f"KakaoAK {api_key}"}
        params = {"query": query, "page": 1}

        try:
            response = requests.get(url, headers=headers, params=params)
            
            # [핵심] 성공이든 실패든 상세 정보를 보여줌
            if response.status_code == 200:
                st.success("🎉 성공! 데이터가 정상적으로 들어옵니다.")
                st.json(response.json()['documents'][0]) # 데이터 샘플 출력
            else:
                st.error(f"⛔ 차단됨 (코드 {response.status_code})")
                # 카카오가 보낸 에러 메시지 원문 출력
                st.code(response.text, language='json')
                
                # 자주 발생하는 원인 분석
                err_msg = response.text
                if "ip mismatched" in err_msg:
                    st.warning("👉 원인: 'IP 주소'가 차단되었습니다. 플랫폼 설정에서 IP 제한을 풀어야 합니다.")
                elif "quota" in err_msg:
                    st.warning("👉 원인: 사용 한도(쿼터)가 초과되었습니다.")
                elif "appKey" in err_msg:
                    st.warning("👉 원인: 키 값은 맞는데, 형식이 잘못되었습니다.")

        except Exception as e:
            st.error(f"프로그램 에러: {e}")
