# app.py
import streamlit as st
import datetime
import os
import pandas as pd
import io
from modules import url_builder
from modules import data_fetcher
from modules import data_processor

# ==============================================================================
# 1. UI (화면 구성)
# ==============================================================================

# 기본 검색어 설정
DEFAULT_OR_KEYWORDS = (
    "MRAM, PRAM, RRAM, FeRAM, OxRAM, CBRAM, "
    "\"Resistive Random-Access Memory\", \"Magnetoresistive Random-Access Memory\", "
    "\"Ferroelectric Random-Access Memory\", \"non-volatile memory\", \"nonvolatile memory\", "
    "\"emerging memory\", \"next-generation memory\", \"storage class memory\", "
    "\"novel memory\", \"advanced memory\", memristor, memristive"
)

st.set_page_config(layout="wide")
st.title(" OpenAlex 논문 데이터 수집")

# 작업 단계를 관리하기 위한 세션 상태 초기화
if 'step' not in st.session_state:
    st.session_state.step = "start"

# --- 입력 섹션: 작업 완료(done) 또는 시작 전(start) 상태일 때만 표시 ---
if st.session_state.step in ["start", "done"]:
    with st.container(border=True):
        st.header("1. 검색 조건 설정")
        col1, col2 = st.columns(2)

        with col1:
            or_keywords_input = st.text_area("OR 키워드 (하나라도 포함)", value=DEFAULT_OR_KEYWORDS, height=250)
        with col2:
            and_keywords_input = st.text_area("AND 키워드 (모두 포함)", "neuromorphic", height=100)

             # --- 2. 검색 기간 설정 (슬라이더 방식) ---
            st.markdown("---") # 구분선 추가
            st.subheader("2. 검색 기간")
            current_year = datetime.datetime.now().year

            # st.slider를 사용하여 연도 범위 선택
            selected_years = st.slider(
                "검색할 연도 범위를 선택하세요.",
                min_value=1980,
                max_value=current_year + 1,
                value=(2015, current_year) # 기본값
            )

            # 슬라이더 결과에서 시작/종료 연도 추출
            start_year, end_year = selected_years

        with st.expander("상세 검색 조건 펼치기"):
            type_options = {
                '학술 논문 (Article)': 'article', '학회 발표 자료 (Conference Paper)': 'conference',
                '도서 챕터 (Book Chapter)': 'book-chapter', '리뷰 (Review)': 'review', '학위 논문 (Dissertation)': 'dissertation'
            }
            selected_includes = st.multiselect("포함할 문서 유형", options=list(type_options.keys()), default=['학술 논문 (Article)', '학회 발표 자료 (Conference Paper)'])
            include_types_values = [type_options[key] for key in selected_includes]

            search_mode_option = st.radio("검색 범위", ('넓게 검색 (포괄적)', '정확하게 검색 (핵심적)'), horizontal=True,
                help="- 넓게 검색: 제목, 초록, 키워드, 주제 등에서 검색\n- 정확하게 검색: 제목과 초록에서만 검색")

            email = st.text_input("API 사용 이메일 주소", "test@example.com", help="반드시 본인의 이메일 주소를 입력해야 검색결과를 받을 수 있습니다.")

    # --- 데이터 수집 시작 버튼 ---
    if st.button("1. 데이터 수집 시작", type="primary", use_container_width=True):
        st.session_state.step = "collecting"
        # UI 입력 값들을 세션에 저장
        st.session_state.ui_inputs = {
        "email": email,
        "or_keywords_input": or_keywords_input,
        "and_keywords_input": and_keywords_input,
        "start_year": start_year,
        "end_year": end_year,
        "include_types_values": include_types_values,
        "search_mode": 'broad' if '넓게' in search_mode_option else 'precise'
    }
        st.rerun()

# ==============================================================================
# 2. 데이터 수집 단계
# ==============================================================================
if st.session_state.step == "collecting":
    with st.spinner("URL 생성 및 데이터 수집 중..."):
        # 저장된 입력 값으로 URL 생성
        inputs = st.session_state.ui_inputs.copy()
        search_mode = inputs.pop('search_mode')

        params = url_builder.prepare_params(**inputs)
        if search_mode == 'broad':
            api_url = url_builder.create_broad_query(**params)
        else:
            api_url = url_builder.create_precise_query(**params)

        st.subheader("📈 데이터 수집 현황")
        DATA_DIR = "data"
        if not os.path.exists(DATA_DIR): os.makedirs(DATA_DIR)
        output_filepath = os.path.join(DATA_DIR, "collected_data.jsonl")

        data_fetcher.fetch_and_save_incrementally(api_url, output_filepath)

        st.session_state['data_filepath'] = output_filepath
        st.session_state.step = "processing" # 다음 단계로 전환
        st.rerun()

# ==============================================================================
# 3. 데이터 정제 단계
# ==============================================================================
if st.session_state.step == "processing":
    filepath = st.session_state['data_filepath']
    with st.spinner(f"'{filepath}' 파일을 정제하는 중입니다..."):
        # data_processor의 마스터 함수 호출
        final_df = data_processor.process_and_refine_data(filepath)
        st.session_state['final_df'] = final_df
        st.session_state.step = "done"
    st.rerun()

# ==============================================================================
# 4. 최종 결과 표시 및 다운로드/초기화
# ==============================================================================
if st.session_state.step == "done":
    st.subheader("📊 최종 정제 데이터")
    st.dataframe(st.session_state['final_df'])
    st.info(f"총 {len(st.session_state['final_df'])}개의 논문 데이터가 처리되었습니다.")

    col1_dl, col2_reset = st.columns(2)
    with col1_dl:
        @st.cache_data
        def convert_df_to_excel(df):
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Sheet1')
            processed_data = output.getvalue()
            return processed_data

        excel_data = convert_df_to_excel(st.session_state['final_df'])
        st.download_button(
            label="📥 엑셀 파일로 다운로드", data=excel_data, file_name="최종_보고서_OpenAlex.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

    with col2_reset:
        if st.button("새 검색 시작", type="secondary", use_container_width=True):
            if 'data_filepath' in st.session_state:
                filepath = st.session_state['data_filepath']
                if os.path.exists(filepath):
                    os.remove(filepath)
                    st.toast(f"'{filepath}' 데이터 파일이 삭제되었습니다.")

            for key in list(st.session_state.keys()):
                del st.session_state[key]

            st.rerun()