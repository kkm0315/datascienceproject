import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px

# 한글 깨짐 걱정 없는 기본 폰트만 사용
import matplotlib
matplotlib.rcParams['font.family'] = 'DejaVu Sans'
matplotlib.rcParams['axes.unicode_minus'] = False

BOOK_META = "book_meta.csv"
LOAN_FILES = ["loan_2022.csv", "loan_2023.csv", "loan_2024.csv"]
LOAN_RETURN_STAT = "loan_return_stat_2022_2024.csv"

# 분야코드-분야명 매핑 (히트맵에서는 코드만 사용)
SUBJECT_CODE_MAP = {
    "A": "총류",
    "B": "철학",
    "C": "종교",
    "D": "사회과학",
    "E": "어학",
    "F": "순수과학",
    "G": "응용과학",
    "H": "예술",
    "I": "문학",
    "J": "역사"
}

@st.cache_data
def load_data():
    book_meta = pd.read_csv(BOOK_META, encoding='utf-8')
    loans = pd.concat([pd.read_csv(f, encoding='utf-8') for f in LOAN_FILES], ignore_index=True)
    for f in LOAN_FILES:
        y = f.split("_")[1].split(".")[0]
        loans.loc[loans['대출일자'].astype(str).str.startswith(y), '연도'] = y
    loan_return = pd.read_csv(LOAN_RETURN_STAT, encoding='utf-8')
    return book_meta, loans, loan_return

def get_subject_code(callnum):
    if pd.isnull(callnum):
        return None
    c = str(callnum).strip().upper()
    code = c[0] if c and c[0] in SUBJECT_CODE_MAP else None
    return code

def is_valid_dept(name):
    if pd.isnull(name): return False
    s = str(name)
    return (
        "도서관" not in s and "합계" not in s and "비율" not in s and "센터" not in s and s.strip() != ""
    )

book_meta, loans, loan_return = load_data()
st.set_page_config(page_title="연암공과대 도서관 대시보드", layout="wide")
st.title("연암공과대학교 도서관 데이터 분석 대시보드 📊")

menu = st.sidebar.radio(
    "분석 주제 선택",
    (
        "① 연도별/학과별 대출 트렌드와 인기 도서 변화",
        "② 신간 vs 구간 도서 대출 패턴 차이",
        "③ 학과별·주제별 도서 선호도/희소·휴면도서",
        "④ 일자별 대출/반납 패턴 & 계절효과"
    )
)

# 1. 연도별/학과별 대출 트렌드와 인기 도서 변화
if menu.startswith("①"):
    st.header("① 연도별/학과별 대출 트렌드와 인기 도서 변화")
    loans['연도'] = loans['대출일자'].astype(str).str[:4]
    dept_col = "소속" if "소속" in loans.columns else loans.columns[loans.columns.str.contains("소속|학과|부서")][0]
    trend = loans.groupby(['연도', dept_col]).size().reset_index(name='대출건수')
    fig = px.line(trend, x='연도', y='대출건수', color=dept_col, markers=True, title="연도별/학과별 대출건수 추이")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### 연도별 Top 10 인기 도서")
    top_n = 10
    years = sorted(loans['연도'].dropna().unique())
    for y in years:
        try:
            top = loans[loans['연도'] == y]['서명'].value_counts().head(top_n)
            st.write(f"**{y}년 Top {top_n} 도서**")
            st.dataframe(top.reset_index().rename(columns={'index': '서명', '서명': '대출수'}))
        except Exception as e:
            st.warning(f"{y}년 데이터 오류: {e}")

    st.markdown("### 저자/출판사별 인기 변화")
    try:
        if '저자' not in loans.columns and '저자' in book_meta.columns:
            loans_merge = pd.merge(loans, book_meta[['등록번호', '저자', '출판사']], on='등록번호', how='left')
        else:
            loans_merge = loans.copy()
        if '저자' in loans_merge.columns:
            top_authors = loans_merge.groupby(['연도','저자']).size().reset_index(name='대출수')
            fig = px.bar(top_authors.sort_values('대출수', ascending=False).groupby('연도').head(5),
                        x='연도', y='대출수', color='저자', barmode='group', title='연도별 인기 저자 Top 5')
            st.plotly_chart(fig, use_container_width=True)
        if '출판사' in loans_merge.columns:
            top_pubs = loans_merge.groupby(['연도','출판사']).size().reset_index(name='대출수')
            fig = px.bar(top_pubs.sort_values('대출수', ascending=False).groupby('연도').head(5),
                        x='연도', y='대출수', color='출판사', barmode='group', title='연도별 인기 출판사 Top 5')
            st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"저자/출판사별 인기 변화 계산 오류: {e}")

# 2. 신간 vs 구간 도서 대출 패턴 차이
elif menu.startswith("②"):
    st.header("② 신간 vs 구간 도서 대출 패턴 차이")
    loans = loans.merge(book_meta[['등록번호', '출판년도']], on='등록번호', how='left')
    loans['출판년도'] = pd.to_numeric(loans['출판년도'], errors='coerce')
    loans['연도'] = loans['대출일자'].astype(str).str[:4].astype(int)
    loans['도서_구분'] = np.where(loans['연도'] - loans['출판년도'] <= 3, '신간', '구간')
    pie = loans['도서_구분'].value_counts()
    st.plotly_chart(px.pie(pie, names=pie.index, values=pie.values, title="신간 vs 구간 대출 비율"), use_container_width=True)
    count_by_year = loans.groupby(['연도', '도서_구분']).size().reset_index(name='대출건수')
    st.plotly_chart(px.bar(count_by_year, x='연도', y='대출건수', color='도서_구분', barmode='group', title="연도별 신간/구간 대출량"), use_container_width=True)

    st.markdown("#### 연도별 Top 10 신간/구간 도서")
    for cat in ['신간', '구간']:
        st.write(f"**{cat} Top 10**")
        df_cat = loans[loans['도서_구분'] == cat]
        top = df_cat['서명'].value_counts().head(10)
        st.dataframe(top.reset_index().rename(columns={'index':'서명', '서명':'대출수'}))

# 3. 학과별·주제별 도서 선호도와 희소/휴면도서
elif menu.startswith("③"):
    st.header("③ 학과별·주제별 도서 선호도와 희소/휴면도서")
    st.markdown("- loan_20xx.csv의 소속, 청구기호 활용 / 분야코드(영문) 기준 - 한글명은 하단 설명")

    loans['분야코드'] = loans['청구기호'].apply(get_subject_code)
    valid = loans[(loans['분야코드'].isin(list(SUBJECT_CODE_MAP.keys()))) & loans['소속'].apply(is_valid_dept)]
    pivot = valid.pivot_table(index='소속', columns='분야코드', values='서명', aggfunc='count', fill_value=0)
    annot = pivot.applymap(lambda x: '' if x == 0 else int(x))

    plt.figure(figsize=(max(10, len(pivot.columns)*1.1), max(6, len(pivot)*0.5)))
    ax = sns.heatmap(
        pivot,
        annot=annot, fmt='', linewidths=0.5, linecolor='gray', cmap='YlGnBu',
        cbar=True, annot_kws={"fontsize":10}
    )
    plt.ylabel("학과", fontsize=13)
    plt.xlabel("분야코드", fontsize=13)
    plt.title("학과별 분야코드 대출건수", fontsize=14)
    plt.xticks(rotation=30, ha='right', fontsize=11)
    plt.yticks(fontsize=10)
    st.pyplot(plt.gcf())
    plt.clf()

    # 코드-분야명 설명 같이 보여주기
    st.markdown("""
    분야코드-분야명  
    A: 총류, B: 철학, C: 종교, D: 사회과학, E: 어학, F: 순수과학, G: 응용과학, H: 예술, I: 문학, J: 역사
    """)

    # 희소/휴면분야 테이블 (학과/분야별 대출 1회 이하)
    st.markdown("##### 대출 1회 이하 희소/휴면분야 (학과/분야코드별)")
    sparse = (
        valid.groupby(['소속', '분야코드']).size()
        .reset_index(name='대출건수')
        .query('대출건수 <= 1')
        .rename(columns={'소속':'학과'})
    )
    st.dataframe(sparse)

# 4. 일자별 대출/반납 패턴 및 계절 효과 분석
elif menu.startswith("④"):
    st.header("④ 일자별 대출/반납 패턴 및 계절 효과 분석")
    st.markdown("loan_return_stat_2022_2024.csv의 [기관, 신분, 대출권수/반납권수] 데이터 기준")
    cols = loan_return.columns
    loc1 = [c for c in cols if "기관" in c or "loc1" in c][0]
    cc = [c for c in cols if "신분" in c or "CcCodeName" in c][0]
    loan_col = [c for c in cols if "대출권수" in c][0]
    return_col = [c for c in cols if "반납권수" in c][0]
    total = loan_return.groupby([loc1, cc])[[loan_col, return_col]].sum().reset_index()
    st.write("기관·신분별 대출/반납건수")
    st.dataframe(total)
    fig = px.bar(total, x=cc, y=loan_col, color=loc1, title="신분별 대출권수")
    st.plotly_chart(fig, use_container_width=True)
    fig = px.bar(total, x=cc, y=return_col, color=loc1, title="신분별 반납권수")
    st.plotly_chart(fig, use_container_width=True)
