# modules/data_fetcher.py
import requests
import json
import time
import math
from datetime import datetime
import streamlit as st # Streamlit의 위젯을 사용하기 위해 import

def fetch_and_save_incrementally(api_url: str, filename: str):
    """
    OpenAlex API에서 데이터를 가져와 즉시 파일에 추가하고,
    Streamlit 화면에 프로그레스 바와 진행 상황 텍스트를 직접 출력합니다.
    """
    start_time = datetime.now()
    st.info(f"데이터 수집을 시작합니다... (시작 시간: {start_time.strftime('%Y-%m-%d %H:%M:%S')})")

    try:
        response_p1 = requests.get(api_url)
        response_p1.raise_for_status()
        data_p1 = response_p1.json()

        total_results = data_p1['meta']['count']
        per_page = data_p1['meta']['per_page']

        if total_results == 0:
            st.warning("검색 결과가 없습니다.")
            return

        total_pages = math.ceil(total_results / per_page)
        st.write(f"총 {total_results}개의 결과를 {total_pages} 페이지에 걸쳐 '{filename}' 파일에 저장합니다.")

        # 파일을 'w'(쓰기) 모드로 열어서, 실행할 때마다 새로 만듭니다.
        with open(filename, 'w', encoding='utf-8') as f:
            results_p1 = data_p1.get('results', [])
            for work in results_p1:
                f.write(json.dumps(work, ensure_ascii=False) + '\n')

            items_saved = len(results_p1)

            # ★★★ Streamlit용 진행 상황 표시 위젯 생성 ★★★
            progress_bar = st.progress(0) # 0%에서 시작하는 프로그레스 바
            status_text = st.empty() # 진행 상황 텍스트를 덮어쓸 빈 공간

            # 첫 페이지 진행률 업데이트
            progress_bar.progress(items_saved / total_results)
            status_text.text(f"수집 진행률: {items_saved} / {total_results} 건")

            # 두 번째 페이지부터 마지막까지 반복
            for page_num in range(2, total_pages + 1):
                paginated_url = f"{api_url}&page={page_num}"
                response = requests.get(paginated_url)
                response.raise_for_status()
                page_data = response.json()

                page_results = page_data.get('results', [])
                if not page_results:
                    st.error(f"\n{page_num}페이지에서 데이터를 가져오는데 실패했습니다.")
                    break

                for work in page_results:
                    f.write(json.dumps(work, ensure_ascii=False) + '\n')

                items_saved += len(page_results)

                # ★★★ 프로그레스 바와 텍스트 업데이트 ★★★
                progress_bar.progress(items_saved / total_results)
                status_text.text(f"수집 진행률: {items_saved} / {total_results} 건")

                time.sleep(0.1)

        end_time = datetime.now()
        elapsed_time = end_time - start_time

        status_text.text(f"수집 완료! 총 {items_saved}건") # 최종 메시지로 업데이트
        st.success(f"작업 완료! 총 {items_saved}개의 데이터를 성공적으로 저장했습니다.")
        st.write(f"총 소요 시간: {elapsed_time}")

    except requests.exceptions.RequestException as e:
        st.error(f"API 요청 중 에러가 발생했습니다: {e}")
    except Exception as e:
        st.error(f"알 수 없는 오류가 발생했습니다: {e}")