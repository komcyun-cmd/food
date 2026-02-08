import streamlit as st
import pandas as pd
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import os

# --- [설정] 페이지 기본 설정 ---
st.set_page_config(page_title="나만의 찐맛집 탐색기", page_icon="🍽️", layout="wide")

# --- [함수] 크롤링 드라이버 설정 (가장 중요!) ---
def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # 화면 없이 실행 (서버 필수)
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    
    # 봇 탐지 우회
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")
    
    # Streamlit Cloud 환경 vs 로컬 환경 구분
    try:
        # Streamlit Cloud 등의 리눅스 환경
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=chrome_options)
    except:
        # 로컬(내 PC) 환경
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
    return driver

# --- [함수] 카카오맵 크롤링 로직 ---
# 성능을 위해 @st.cache_data를 사용하여 동일 검색어는 재크롤링 방지
@st.cache_data(show_spinner=False) 
def scrape_kakao(keyword, max_pages=3):
    data = []
    driver = get_driver()
    
    try:
        driver.get("https://map.kakao.com/")
        time.sleep(1)
        
        # 검색
        search_area = driver.find_element(By.ID, "search.keyword.query")
        search_area.send_keys(keyword)
        time.sleep(1) # 입력 안정화
        driver.find_element(By.ID, "search.keyword.submit").click()
        time.sleep(2)
        
        # '장소 더보기' 클릭
        try:
            more_btn = driver.find_element(By.ID, "info.search.place.more")
            driver.execute_script("arguments[0].click();", more_btn)
            time.sleep(1)
        except:
            pass # 결과가 적음
            
        # 페이지 순회
        for page_idx in range(1, max_pages + 1):
            try:
                # 페이지 번호 클릭
                page_btn = driver.find_element(By.ID, f"info.search.page.no{page_idx}")
                driver.execute_script("arguments[0].click();", page_btn)
                time.sleep(1.5)
                
                # BS4 파싱
                html = driver.page_source
                soup = BeautifulSoup(html, 'html.parser')
                place_list = soup.select('.PlaceItem')
                
                for place in place_list:
                    try:
                        name = place.select_one('.link_name').text.strip()
                        try:
                            score = float(place.select_one('.rating > .score > em').text)
                        except:
                            score = 0.0
                        try:
                            review_cnt = int(place.select_one('.rating > .review > em').text.replace(",",""))
                        except:
                            review_cnt = 0
                        addr = place.select_one('.addr').text.strip()
                        cat = place.select_one('.subcategory').text.strip()
                        link = place.select_one('.link_name')['href']
                        
                        data.append([name, score, review_cnt, cat, addr, link])
                    except:
                        continue
            except:
                break # 페이지 끝
                
    except Exception as e:
        st.error(f"크롤링 중 오류 발생: {e}")
    finally:
        driver.quit()
        
    df = pd.DataFrame(data, columns=['식당명', '별점', '리뷰수', '카테고리', '주소', '링크'])
    return df

# --- [UI] 스트림릿 화면 구성 ---
st.title("🕵️‍♀️ 나만의 찐맛집 탐색기 (Zero-Cost)")

with st.sidebar:
    st.header("검색 설정")
    region = st.text_input("검색어 (예: 대전 유성구 맛집)", value="대전 유성구 맛집")
    page_limit = st.slider("수집할 페이지 수", 1, 5, 2)
    
    st.divider()
    st.markdown("### 🔍 필터링 기준")
    min_score = st.slider("최소 별점", 0.0, 5.0, 3.5)
    min_reviews = st.slider("최소 리뷰 수", 0, 300, 10)
    
    run_btn = st.button("데이터 수집 시작! 🚀")

if run_btn:
    with st.status("데이터를 모으고 있습니다... (약 10~20초 소요)", expanded=True) as status:
        st.write("🌐 브라우저 실행 중...")
        df = scrape_kakao(region, page_limit)
        st.write("✅ 수집 완료! 데이터 정제 중...")
        status.update(label="분석 완료!", state="complete", expanded=False)
        
    if not df.empty:
        # 필터링 적용
        filtered_df = df[
            (df['별점'] >= min_score) & 
            (df['리뷰수'] >= min_reviews)
        ].sort_values(by='별점', ascending=False)
        
        st.subheader(f"📊 '{region}' 분석 결과: {len(filtered_df)}곳 발견")
        
        # 데이터프레임 표시 (링크 클릭 가능하게 설정)
        st.dataframe(
            filtered_df,
            column_config={
                "링크": st.column_config.LinkColumn("지도 보기")
            },
            use_container_width=True
        )
        
        # 다운로드 버튼
        st.download_button(
            label="CSV로 다운로드",
            data=filtered_df.to_csv(index=False).encode('utf-8-sig'),
            file_name=f"{region}_맛집.csv",
            mime='text/csv'
        )
    else:
        st.warning("데이터를 찾지 못했습니다. 검색어를 확인해주세요.")

else:
    st.info("왼쪽 사이드바에서 검색어를 입력하고 '시작' 버튼을 눌러주세요.")
