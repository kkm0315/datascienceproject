import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.express as px

def classify_call_number(call_no, output='code'):
    if not isinstance(call_no, str) or not call_no:
        return "기타" if output == "name" else "ETC"
    code = call_no.strip()[0]
    code_map = {
        "0": ("000", "총류"),
        "1": ("100", "철학"),
        "2": ("200", "종교"),
        "3": ("300", "사회과학"),
        "4": ("400", "자연과학"),
        "5": ("500", "기술과학"),
        "6": ("600", "예술"),
        "7": ("700", "언어"),
        "8": ("800", "문학"),
        "9": ("900", "역사")
    }
    return code_map.get(code, ("ETC", "기타"))[0 if output == 'code' else 1]

@st.cache_data
def load_data():
    df22 = pd.read_csv("loan_2022.csv", encoding="utf-8")
    df23 = pd.read_csv("loan_2023.csv", encoding="utf-8")
    df24 = pd.read_csv("loan_2024.csv", encoding="utf-8")
    meta = pd.read_csv("book_meta.csv", encoding="utf-8")
    df22["연도"] = 2022
    df23["연도"] = 2023
    df24["연도"] = 2024
    loan = pd.concat([df22, df23, df24], ignore_index=True)
    return loan, meta

loan, meta = load_data()

current_year = 2025
meta["출판년도"] = meta["출판년도"].astype(str).str[:4].replace("nan", np.nan)
meta["출판년도"] = pd.to_numeric(meta["출판년도"], errors="coerce")
meta["신간/구간"] = np.where(
    meta["출판년도"].notnull() & (current_year - meta["출판년도"] <= 3), "신간", "구간"
)

loan = pd.merge(
    loan,
    meta[["등록번호", "출판년도", "신간/구간"]],
    on="등록번호",
    how="left"
)

exclude_orgs = [
    "AI.DX센터", "AI·DX 센터", "AI·DX센터", "AI·DX 센터", "AIㆍDX센터",
    "교무처", "교수학습지원센터", "기타", "기획처", "도서관", "보건실",
    "사무처", "산학융복합교육센터", "산학협력단", "입학학생처(입학)", "입학학생처(학생)",
    "취장업지원처", "학생상담실", "혁신지원사업팀"
]

departments = sorted([d for d in loan["소속"].dropna().unique()
                      if not any(org.replace(" ", "") in d.replace(" ", "") for org in exclude_orgs)])

st.title("연암공과대학교 도서관: 학과별 대출 분석 대시보드")
dept = st.selectbox("학과를 선택하세요", departments)

tab1, tab2, tab3 = st.tabs([
    "연도별/학과별 대출 트렌드 & 인기 도서",
    "신간/구간 분야별 인기 및 인기도서",
    "분야별 전체 인기 주제"
])

with tab1:
    st.subheader(f"학과: {dept} | 연도별 대출 트렌드")
    df_dept = loan[loan["소속"] == dept]
    trend = df_dept.groupby("연도").size().reset_index(name="대출건수")
    fig1 = px.bar(trend, x="연도", y="대출건수", text="대출건수", title="연도별 대출건수")
    st.plotly_chart(fig1)
    st.markdown("---")
    st.subheader("연도별 Top 10 인기 도서")
    year = st.selectbox("연도 선택", sorted(df_dept["연도"].unique(), reverse=True))
    top_books = (
        df_dept[df_dept["연도"] == year]
        .groupby(["등록번호", "서명"])
        .size()
        .reset_index(name="대출횟수")
        .sort_values("대출횟수", ascending=False)
        .head(10)
    )
    # 인덱스 제거
    st.dataframe(top_books[["서명", "대출횟수"]].reset_index(drop=True), use_container_width=True)
    fig2 = px.bar(top_books, x="서명", y="대출횟수", text="대출횟수", title=f"{year}년 Top 10 도서")
    fig2.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig2)

with tab2:
    st.subheader(f"학과: {dept} | 신간/구간 분야별 인기 및 인기도서")
    df_dept = loan[loan["소속"] == dept].copy()
    df_dept["분야명"] = df_dept["청구기호"].apply(lambda x: classify_call_number(x, output="name"))
    type_choice = st.radio("신간/구간 선택", ["신간", "구간"], horizontal=True)
    연도_list = sorted(df_dept["연도"].dropna().unique(), reverse=True)
    year2 = st.selectbox("분야별 대출 연도 선택", 연도_list, key="subject_year2")
    n_field = st.slider("TOP N (많이 대출된 분야)", min_value=3, max_value=10, value=10, key="topn_subject")
    filtered = df_dept[(df_dept["신간/구간"] == type_choice) & (df_dept["연도"] == year2)]
    top_fields = (
        filtered.groupby("분야명")
        .size()
        .reset_index(name="대출건수")
        .sort_values("대출건수", ascending=False)
        .head(n_field)
    )
    # 인덱스 제거
    st.dataframe(top_fields.reset_index(drop=True), use_container_width=True)
    fig3 = px.bar(
        top_fields, x="분야명", y="대출건수", text="대출건수",
        title=f"{year2}년 {type_choice} 분야별 대출건수 TOP {n_field}"
    )
    fig3.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig3)

    분야_list = top_fields["분야명"].tolist()
    if 분야_list:
        분야 = st.selectbox(f"{type_choice} 인기분야 중 도서별 순위 보기", 분야_list, key=f"{type_choice}_분야")
        st.markdown(f"##### 분야: {분야} | 인기 도서 TOP 10")
        top_books = (
            filtered[filtered["분야명"] == 분야]
            .groupby(["등록번호", "서명"])
            .size()
            .reset_index(name="대출횟수")
            .sort_values("대출횟수", ascending=False)
            .head(10)
        )
        # 인덱스 제거
        st.dataframe(top_books[["서명", "대출횟수"]].reset_index(drop=True), use_container_width=True)
        fig4 = px.bar(
            top_books, x="서명", y="대출횟수", text="대출횟수",
            title=f"{year2}년 {type_choice} {분야} 분야 인기 도서 TOP 10"
        )
        fig4.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig4)
    else:
        st.info("선택한 조건의 데이터가 없습니다.")

with tab3:
    st.subheader(f"학과: {dept} | 분야(주제)별 전체 인기 대출 현황")
    df_dept = loan[loan["소속"] == dept].copy()
    df_dept["분야명"] = df_dept["청구기호"].apply(lambda x: classify_call_number(x, output="name"))
    year3 = st.selectbox("분야별 대출 연도 선택", sorted(df_dept["연도"].unique(), reverse=True), key="subject_year3")
    n2 = st.slider("TOP N (많이 대출된 분야)", min_value=3, max_value=10, value=10, key="all_topn_subject")
    top_subjects = (
        df_dept[df_dept["연도"] == year3]
        .groupby("분야명")
        .size()
        .reset_index(name="대출건수")
        .sort_values("대출건수", ascending=False)
        .head(n2)
    )
    # 인덱스 제거
    st.dataframe(top_subjects.reset_index(drop=True), use_container_width=True)
    fig5 = px.bar(top_subjects, x="분야명", y="대출건수", text="대출건수",
                  title=f"{year3}년 분야별 인기 TOP {n2}")
    fig5.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig5)
