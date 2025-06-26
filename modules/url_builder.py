# modules/url_builder.py
from urllib.parse import quote

def prepare_params(
    email: str,
    or_keywords_input: str,
    and_keywords_input: str,
    start_year: int,
    end_year: int,
    include_types_values: list = None
):
    """
    Streamlit UI의 원본 입력값들을 받아,
    API 쿼리 함수에 바로 전달할 수 있는 깔끔한 딕셔너리로 변환합니다.
    """
    or_keywords = [k.strip() for k in or_keywords_input.split(',') if k.strip()]
    and_keywords = [k.strip() for k in and_keywords_input.split(',') if k.strip()]
    year_range = f"{start_year}-{end_year}"

    return {
        "email": email,
        "or_keywords": or_keywords,
        "and_keywords": and_keywords,
        "year_range": year_range,
        "include_types": include_types_values
    }

def create_broad_query(email, or_keywords, and_keywords=None, year_range=None, include_types=None):
    """[넓게 검색] OR 조건을 default.search로 검색합니다."""
    filters = []
    base_url = "https://api.openalex.org/works"
    if or_keywords:
        or_terms = [f'"{k}"' if ' ' in k else k for k in or_keywords]
        filters.append(f"default.search:{'|'.join(or_terms)}")
    if and_keywords:
        for keyword in and_keywords:
            term = f'"{keyword}"' if ' ' in keyword else keyword
            filters.append(f"title_and_abstract.search:{term}")
    if include_types:
        filters.append(f"type:{'|'.join(include_types)}")
    if year_range:
        filters.append(f"publication_year:{year_range}")
    final_filter_string = ",".join(filters)
    encoded_filter = quote(final_filter_string)
    return f"{base_url}?filter={encoded_filter}&mailto={email}"

def create_precise_query(email, or_keywords, and_keywords=None, year_range=None, include_types=None):
    """[정확하게 검색] OR 조건을 title_and_abstract.search로 검색합니다."""
    filters = []
    base_url = "https://api.openalex.org/works"
    if or_keywords:
        or_terms = [f'"{k}"' if ' ' in k else k for k in or_keywords]
        filters.append(f"title_and_abstract.search:{'|'.join(or_terms)}")
    if and_keywords:
        for keyword in and_keywords:
            term = f'"{keyword}"' if ' ' in keyword else keyword
            filters.append(f"title_and_abstract.search:{term}")
    if include_types:
        filters.append(f"type:{'|'.join(include_types)}")
    if year_range:
        filters.append(f"publication_year:{year_range}")
    final_filter_string = ",".join(filters)
    encoded_filter = quote(final_filter_string)
    return f"{base_url}?filter={encoded_filter}&mailto={email}"