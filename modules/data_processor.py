import pandas as pd
import json

# --- 1. 데이터 로딩 및 기본 준비 함수 ---
def load_and_prepare_df(filepath: str) -> pd.DataFrame:
    """JSONL 파일을 불러와 데이터프레임으로 만들고, 중복을 제거합니다."""
    print("Step 1: 데이터 로딩 및 중복 제거...")
    all_papers = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    all_papers.append(json.loads(line))
                except json.JSONDecodeError:
                    print(f"경고: JSON 파싱 에러 발생. 해당 라인을 건너뜁니다.")
                    continue
        if not all_papers:
            print("경고: 파일에서 데이터를 읽어오지 못했습니다.")
            return pd.DataFrame()

        raw_df = pd.DataFrame(all_papers)
        if 'id' not in raw_df.columns:
            print("에러: 'id' 컬럼이 없어 중복을 제거할 수 없습니다.")
            return raw_df

        df = raw_df.drop_duplicates(subset=['id'], keep='first').copy()
        print(f"-> 정제 시작 데이터: {len(df)} 행")
        return df
    except FileNotFoundError:
        print(f"에러: '{filepath}' 파일을 찾을 수 없습니다.")
        return pd.DataFrame()


# --- 2. 개별 정제 함수들 ---

def refine_authors(df: pd.DataFrame) -> pd.DataFrame:
    """authorships 컬럼을 정제하여 저자/기관 관련 6개 컬럼을 추가합니다."""
    print("-> 저자/기관 정보 정제 중...")
    new_cols = ['First_Author_Name', 'First_Author_Institution', 'Corresponding_Author_Names',
                'Corresponding_Institution_Names', 'All_Authors', 'All_Institutions']
    for col in new_cols:
        df[col] = ''

    for index, row in df.iterrows():
        try:
            authorships = row.get('authorships', [])
            if not isinstance(authorships, list): continue

            corr_ids = row.get('corresponding_author_ids', [])
            first_author_name, first_author_institution = '', ''
            corr_author_names, all_author_names = [], []
            corr_institution_names, all_institution_names = set(), set()

            for author_info in authorships:
                author_id = author_info.get('author', {}).get('id')
                author_name = author_info.get('author', {}).get('display_name', '')
                institutions = author_info.get('institutions', [])
                inst_names_str = "; ".join(sorted([inst.get('display_name', '') for inst in institutions if inst.get('display_name')]))

                if author_name: all_author_names.append(author_name)
                if inst_names_str:
                    for inst_name in inst_names_str.split('; '): all_institution_names.add(inst_name)

                if author_info.get('author_position') == 'first':
                    first_author_name, first_author_institution = author_name, inst_names_str

                if corr_ids and author_id in corr_ids:
                    corr_author_names.append(author_name)
                    if inst_names_str:
                        for inst_name in inst_names_str.split('; '): corr_institution_names.add(inst_name)

            df.at[index, 'First_Author_Name'] = first_author_name
            df.at[index, 'First_Author_Institution'] = first_author_institution
            df.at[index, 'Corresponding_Author_Names'] = "; ".join(sorted(corr_author_names))
            df.at[index, 'Corresponding_Institution_Names'] = "; ".join(sorted(list(corr_institution_names)))
            df.at[index, 'All_Authors'] = "; ".join(all_author_names)
            df.at[index, 'All_Institutions'] = "; ".join(sorted(list(all_institution_names)))
        except Exception as e:
            print(f"경고: 저자 정보 처리 중 에러 (index: {index}): {e}")
            continue
    return df


def refine_topics_and_keywords(df: pd.DataFrame) -> pd.DataFrame:
    """topics, primary_topic, keywords 컬럼을 정제합니다."""
    print("-> 주제/키워드 정보 정제 중...")

    def format_item(item_dict):
        try:
            if not isinstance(item_dict, dict): return ""
            name = item_dict.get('display_name', 'N/A')
            score = round(item_dict.get('score', 0), 3)
            return f"{name} ({score})"
        except Exception: return ""

    df['Primary_Topic(Score)'] = df['primary_topic'].apply(format_item)
    df['Top_Topics(Scores)'] = df['topics'].apply(lambda lst: "; ".join([format_item(t) for t in lst]) if isinstance(lst, list) else "")
    df['Keywords(Scores)'] = df['keywords'].apply(lambda lst: "; ".join([format_item(k) for k in sorted(lst, key=lambda x: x.get('score', 0), reverse=True)]) if isinstance(lst, list) else "")
    return df

def refine_abstract(df: pd.DataFrame) -> pd.DataFrame:
    """abstract_inverted_index를 복원하여 Abstract 컬럼을 추가합니다."""
    print("-> 초록 정보 복원 중...")
    def reconstruct(inverted_index):
        try:
            if not isinstance(inverted_index, dict): return ""
            indexed_words = sorted([(idx, word) for word, indices in inverted_index.items() for idx in indices])
            return " ".join([word for idx, word in indexed_words])
        except Exception: return ""
    df['Abstract'] = df['abstract_inverted_index'].apply(reconstruct)
    return df

def refine_percentile(df: pd.DataFrame) -> pd.DataFrame:
    """citation_normalized_percentile을 정제하여 3개 컬럼을 추가합니다."""
    print("-> 인용 백분위 정보 정제 중...")
    def extract_info(p_dict):
        try:
            if not isinstance(p_dict, dict): return None, None, None
            return p_dict.get('value'), p_dict.get('is_in_top_1_percent'), p_dict.get('is_in_top_10_percent')
        except Exception: return None, None, None
    (df['Citation_Percentile'], df['Is_Top_1_Percent'], df['Is_Top_10_Percent']) = zip(*df['citation_normalized_percentile'].apply(extract_info))
    return df


def refine_journal(df: pd.DataFrame) -> pd.DataFrame:
    """primary_location을 정제하여 저널/출판사 관련 3개 컬럼을 추가합니다."""
    print("-> 저널/출판사 정보 정제 중...")
    def extract_info(loc_dict):
        try:
            if not isinstance(loc_dict, dict): return None, None, None
            source = loc_dict.get('source', {}) or {}
            return source.get('display_name'), source.get('host_organization_name'), source.get('issn_l')
        except Exception: return None, None, None
    (df['Journal_Name'], df['Publisher'], df['ISSN-L']) = zip(*df['primary_location'].apply(extract_info))
    return df


# --- 3. 최종 정리 함수 ---
def finalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """최종적으로 컬럼을 선택하고 순서를 재정렬한 후, 복잡한 데이터를 문자열로 변환하여 엑셀 저장 준비를 합니다."""
    print("-> 최종 컬럼 선택 및 순서 정렬, 데이터 변환 중...")
    new_column_order = [
    # === 식별자 및 링크 정보 ===
    'doi',
    'id',

    # === 사용자가 가장 먼저 볼 핵심 정보 ===
    'title', 'publication_year', 'Journal_Name', 'Publisher', 'ISSN-L',

    # 저자 / 기관 정보
    'First_Author_Name', 'First_Author_Institution',
    'Corresponding_Author_Names', 'Corresponding_Institution_Names',
    'All_Authors', 'All_Institutions',

    # === 내용 및 주제 ===
    'Abstract',
    'Primary_Topic(Score)',
    'Top_Topics(Scores)',
    'Keywords(Scores)',

    # === 영향력 지표 ===
    'cited_by_count',
    'fwci',
    'Citation_Percentile',
    'Is_Top_1_Percent',
    'Is_Top_10_Percent',
]
    all_current_columns = df.columns.tolist()
    remaining_columns = [col for col in all_current_columns if col not in new_column_order]
    final_ordered_columns = new_column_order + remaining_columns

    # 존재하는 컬럼만 선택
    existing_cols = [col for col in final_ordered_columns if col in df.columns]
    df_reordered = df[existing_cols]

    df_to_save = df_reordered.copy()
    for col in df_to_save.columns:
        if not df_to_save[col].isnull().all():
            if isinstance(df_to_save[col].dropna().iloc[0], (dict, list)):
                df_to_save[col] = df_to_save[col].apply(lambda x: json.dumps(x, ensure_ascii=False) if isinstance(x, (dict, list)) else x)

    return df_to_save

# ==============================================================================
# ★★★ 섹션 2: 모든 것을 총괄하는 '마스터' 함수 ★★★
# ==============================================================================
def process_and_refine_data(filepath: str) -> pd.DataFrame:
    """
    하나의 함수 호출로, 데이터 로딩부터 모든 정제 및 최종 정리까지
    전체 파이프라인을 실행합니다.
    """
    # 1. 데이터 로딩 및 준비
    df = load_and_prepare_df(filepath)
    if df.empty:
        return pd.DataFrame() # 빈 데이터프레임이면 바로 종료

    # 2. 각 정제 함수를 순서대로 호출하여 데이터프레임을 계속 업데이트
    df = refine_authors(df)
    df = refine_topics_and_keywords(df)
    df = refine_abstract(df)
    df = refine_percentile(df)
    df = refine_journal(df)

    # 3. 최종 정리 함수 호출
    final_df = finalize_dataframe(df)

    print("\n모든 데이터 처리 파이프라인이 성공적으로 완료되었습니다!")
    return final_df