# ============================================================
# 부동산 종합 실무 분석 시스템
#
# 분석대상
# 1. 토지
# 2. 상가
# 3. 공장
# 4. 창고
# 5. 아파트
#
# 주요 기능
# - 개발 / 분양 사업수지
# - 매입 / 임대 수익분석
# - 개발규모 계산
# - 금융비용 계산
# - 사업이익 / ROI
# - 적정 토지가격 역산
# - NOI / Cap Rate / DSCR
# - Cash-on-Cash
# - 민감도 분석
# - CSV 다운로드
# ============================================================


import streamlit as st
import pandas as pd
import plotly.graph_objects as go


# ============================================================
# 1. Streamlit 화면 설정
# ============================================================

st.set_page_config(
    page_title="부동산 종합 실무 분석",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# 2. 기본 상수
# ============================================================

SQM_PER_PYEONG = 3.305785


# ============================================================
# 3. 공통 함수
# ============================================================

def sqm_to_py(value):
    """㎡ → 평"""
    return value / SQM_PER_PYEONG


def py_to_sqm(value):
    """평 → ㎡"""
    return value * SQM_PER_PYEONG


def pct(value):
    """60% → 0.60"""
    return value / 100


def safe_div(a, b):
    """0으로 나누는 오류 방지"""
    if b == 0:
        return 0
    return a / b


def format_eok(value):
    """원을 억원 단위로 표시"""
    return f"{value / 100_000_000:,.1f}억원"


def format_won(value):
    """원 + 억원 표시"""
    return (
        f"{value:,.0f}원 "
        f"({value / 100_000_000:,.1f}억원)"
    )


def format_area(value_m2):
    """㎡ + 평 표시"""
    return (
        f"{value_m2:,.1f}㎡ / "
        f"{sqm_to_py(value_m2):,.1f}평"
    )


def dataframe_to_csv(df):
    """CSV 다운로드"""
    return df.to_csv(
        index=False
    ).encode("utf-8-sig")


# ============================================================
# 4. 개발 / 분양 사업수지 계산
# ============================================================

def calculate_development(p):

    # --------------------------------------------------------
    # 비율 변환
    # --------------------------------------------------------

    building_ratio = pct(
        p["building_ratio"]
    )

    far_ratio = pct(
        p["far_ratio"]
    )

    excluded_ratio = pct(
        p["excluded_ratio"]
    )

    sale_area_ratio = pct(
        p["sale_area_ratio"]
    )

    acquisition_ratio = pct(
        p["acquisition_ratio"]
    )

    debt_ratio = pct(
        p["debt_ratio"]
    )

    interest_rate = pct(
        p["interest_rate"]
    )

    construction_draw_ratio = pct(
        p["construction_draw_ratio"]
    )

    project_years = (
        p["project_months"] / 12
    )

    construction_years = (
        p["construction_months"] / 12
    )


    # ========================================================
    # A. 개발 규모
    # ========================================================

    # 건축면적
    building_area = (
        p["land_area"]
        * building_ratio
    )


    # 용적률 산정 연면적
    far_floor_area = (
        p["land_area"]
        * far_ratio
    )


    # 용적률 제외면적
    excluded_area = (
        far_floor_area
        * excluded_ratio
    )


    # 공사비 산정 연면적
    construction_area = (
        far_floor_area
        + excluded_area
    )


    construction_area_py = (
        sqm_to_py(
            construction_area
        )
    )


    # 분양면적
    sale_area = (
        far_floor_area
        * sale_area_ratio
    )


    sale_area_py = (
        sqm_to_py(
            sale_area
        )
    )


    # 이론상 평균층수
    theoretical_floors = (
        safe_div(
            far_floor_area,
            building_area
        )
    )


    # ========================================================
    # B. 매출
    # ========================================================

    sales_revenue = (
        sale_area_py
        * p["sale_price_py"]
    )


    # ========================================================
    # C. 직접공사비
    # ========================================================

    direct_construction_cost = (
        construction_area_py
        * p["construction_cost_py"]
    )


    # ========================================================
    # D. 기타 사업비
    # ========================================================

    if p["other_cost_mode"] == "간편 비율":

        other_project_cost = (
            direct_construction_cost
            * pct(
                p["other_cost_ratio"]
            )
        )

    else:

        other_project_cost = (
            p["demolition_cost"]
            + p["design_cost"]
            + p["permit_cost"]
            + p["marketing_cost"]
            + p["trust_fee"]
            + p["contingency"]
            + p["other_fixed_cost"]
        )


    # ========================================================
    # E. 토지취득 부대비
    # ========================================================

    acquisition_cost = (
        p["land_price"]
        * acquisition_ratio
    )


    # ========================================================
    # F. 토지 금융비
    # ========================================================

    land_finance_cost = (
        p["land_price"]
        * debt_ratio
        * interest_rate
        * project_years
    )


    # ========================================================
    # G. 건설 금융비
    # ========================================================

    construction_finance_cost = (
        (
            direct_construction_cost
            + other_project_cost
        )
        * construction_draw_ratio
        * debt_ratio
        * interest_rate
        * construction_years
    )


    # ========================================================
    # H. 총사업비
    # ========================================================

    total_project_cost = (
        p["land_price"]
        + acquisition_cost
        + direct_construction_cost
        + other_project_cost
        + land_finance_cost
        + construction_finance_cost
    )


    # ========================================================
    # I. 예상 사업이익
    # ========================================================

    project_profit = (
        sales_revenue
        - total_project_cost
    )


    # 매출 대비 사업이익률
    profit_margin = (
        safe_div(
            project_profit,
            sales_revenue
        )
        * 100
    )


    # 총사업비 대비 ROI
    roi = (
        safe_div(
            project_profit,
            total_project_cost
        )
        * 100
    )


    # ========================================================
    # J. 목표이익
    # ========================================================

    if (
        p["target_profit_mode"]
        == "매출액 대비 목표이익률"
    ):

        target_profit = (
            sales_revenue
            * pct(
                p["target_profit_ratio"]
            )
        )

    else:

        target_profit = (
            p["target_profit_fixed"]
        )


    # ========================================================
    # K. 적정 토지가격
    # ========================================================

    numerator = (
        sales_revenue
        - target_profit
        - direct_construction_cost
        - other_project_cost
        - construction_finance_cost
    )


    denominator = (
        1
        + acquisition_ratio
        + (
            debt_ratio
            * interest_rate
            * project_years
        )
    )


    affordable_land_price = (
        safe_div(
            numerator,
            denominator
        )
    )


    land_price_gap = (
        affordable_land_price
        - p["land_price"]
    )


    # ========================================================
    # L. 손익분기 분양가
    # ========================================================

    break_even_sale_price = (
        safe_div(
            total_project_cost,
            sale_area_py
        )
    )


    # ========================================================
    # M. 평당 토지가격
    # ========================================================

    land_area_py = (
        sqm_to_py(
            p["land_area"]
        )
    )


    current_land_price_py = (
        safe_div(
            p["land_price"],
            land_area_py
        )
    )


    affordable_land_price_py = (
        safe_div(
            affordable_land_price,
            land_area_py
        )
    )


    return {

        "building_area":
            building_area,

        "far_floor_area":
            far_floor_area,

        "excluded_area":
            excluded_area,

        "construction_area":
            construction_area,

        "construction_area_py":
            construction_area_py,

        "sale_area":
            sale_area,

        "sale_area_py":
            sale_area_py,

        "theoretical_floors":
            theoretical_floors,

        "sales_revenue":
            sales_revenue,

        "direct_construction_cost":
            direct_construction_cost,

        "other_project_cost":
            other_project_cost,

        "acquisition_cost":
            acquisition_cost,

        "land_finance_cost":
            land_finance_cost,

        "construction_finance_cost":
            construction_finance_cost,

        "total_project_cost":
            total_project_cost,

        "project_profit":
            project_profit,

        "profit_margin":
            profit_margin,

        "roi":
            roi,

        "target_profit":
            target_profit,

        "affordable_land_price":
            affordable_land_price,

        "land_price_gap":
            land_price_gap,

        "break_even_sale_price":
            break_even_sale_price,

        "current_land_price_py":
            current_land_price_py,

        "affordable_land_price_py":
            affordable_land_price_py
    }


# ============================================================
# 5. 매입 / 임대 수익성 계산
# ============================================================

def calculate_income_property(p):

    purchase_price = (
        p["purchase_price"]
    )


    # ========================================================
    # A. 취득비
    # ========================================================

    acquisition_cost = (
        purchase_price
        * pct(
            p["acquisition_ratio"]
        )
    )


    all_in_cost = (
        purchase_price
        + acquisition_cost
        + p["capex"]
    )


    # ========================================================
    # B. 임대면적
    # ========================================================

    leasable_area_py = (
        sqm_to_py(
            p["leasable_area"]
        )
    )


    # ========================================================
    # C. 월 임대료
    # ========================================================

    if p["rent_mode"] == "평당 월세":

        monthly_rent = (
            leasable_area_py
            * p["rent_per_py"]
        )

    else:

        monthly_rent = (
            p["total_monthly_rent"]
        )


    # ========================================================
    # D. 연간 잠재 수입
    # ========================================================

    annual_base_rent = (
        monthly_rent
        * 12
    )


    annual_other_income = (
        p["monthly_other_income"]
        * 12
    )


    potential_income = (
        annual_base_rent
        + annual_other_income
    )


    # ========================================================
    # E. 공실 반영
    # ========================================================

    occupancy_rate = (
        1
        - pct(
            p["vacancy_rate"]
        )
    )


    effective_income = (
        potential_income
        * occupancy_rate
    )


    # ========================================================
    # F. 운영비
    # ========================================================

    variable_expense = (
        effective_income
        * pct(
            p["operating_expense_ratio"]
        )
    )


    operating_expense = (
        variable_expense
        + p["annual_fixed_expense"]
    )


    # ========================================================
    # G. NOI
    # ========================================================

    noi = (
        effective_income
        - operating_expense
    )


    # ========================================================
    # H. 수익률
    # ========================================================

    gross_yield = (
        safe_div(
            potential_income,
            purchase_price
        )
        * 100
    )


    cap_rate = (
        safe_div(
            noi,
            purchase_price
        )
        * 100
    )


    all_in_cap_rate = (
        safe_div(
            noi,
            all_in_cost
        )
        * 100
    )


    # ========================================================
    # I. 대출금
    # ========================================================

    loan_amount = (
        purchase_price
        * pct(
            p["debt_ratio"]
        )
    )


    annual_interest_rate = (
        pct(
            p["interest_rate"]
        )
    )


    # ========================================================
    # J. 대출 상환액
    # ========================================================

    if p["loan_type"] == "이자만 납부":

        annual_debt_service = (
            loan_amount
            * annual_interest_rate
        )

    else:

        loan_months = (
            p["loan_term_years"]
            * 12
        )


        monthly_rate = (
            annual_interest_rate
            / 12
        )


        if (
            monthly_rate > 0
            and loan_months > 0
        ):

            monthly_payment = (
                loan_amount
                * monthly_rate
                * (
                    1 + monthly_rate
                ) ** loan_months
                /
                (
                    (
                        1 + monthly_rate
                    ) ** loan_months
                    - 1
                )
            )

        elif loan_months > 0:

            monthly_payment = (
                loan_amount
                / loan_months
            )

        else:

            monthly_payment = 0


        annual_debt_service = (
            monthly_payment
            * 12
        )


    # ========================================================
    # K. DSCR
    # ========================================================

    dscr = (
        safe_div(
            noi,
            annual_debt_service
        )
    )


    # ========================================================
    # L. 세전 현금흐름
    # ========================================================

    cash_flow = (
        noi
        - annual_debt_service
    )


    # ========================================================
    # M. 필요 자기자본
    # ========================================================

    deposit_funding = 0


    if p["use_deposit_as_funding"]:

        deposit_funding = (
            p["tenant_deposit"]
        )


    initial_equity = (
        all_in_cost
        - loan_amount
        - deposit_funding
    )


    # ========================================================
    # N. Cash-on-Cash
    # ========================================================

    if initial_equity > 0:

        cash_on_cash = (
            cash_flow
            / initial_equity
            * 100
        )

    else:

        cash_on_cash = 0


    # ========================================================
    # O. 목표 Cap Rate 기준 가치
    # ========================================================

    target_cap_decimal = (
        pct(
            p["target_cap_rate"]
        )
    )


    estimated_value = (
        safe_div(
            noi,
            target_cap_decimal
        )
    )


    value_gap = (
        estimated_value
        - purchase_price
    )


    # ========================================================
    # P. 평당 가격
    # ========================================================

    land_area_py = (
        sqm_to_py(
            p["land_area"]
        )
    )


    gross_area_py = (
        sqm_to_py(
            p["gross_floor_area"]
        )
    )


    land_price_py = (
        safe_div(
            purchase_price,
            land_area_py
        )
    )


    gross_area_price_py = (
        safe_div(
            purchase_price,
            gross_area_py
        )
    )


    # ========================================================
    # Q. 손익분기 임대율
    # ========================================================

    expense_ratio = (
        pct(
            p["operating_expense_ratio"]
        )
    )


    break_even_denominator = (
        potential_income
        * (
            1 - expense_ratio
        )
    )


    break_even_occupancy = (
        safe_div(
            (
                p["annual_fixed_expense"]
                + annual_debt_service
            ),
            break_even_denominator
        )
        * 100
    )


    # ========================================================
    # R. 손익분기 월세
    # ========================================================

    current_occupancy = max(
        occupancy_rate,
        0.0001
    )


    expense_after_ratio = (
        1 - expense_ratio
    )


    required_effective_income = (
        safe_div(
            (
                p["annual_fixed_expense"]
                + annual_debt_service
            ),
            expense_after_ratio
        )
    )


    required_potential_income = (
        safe_div(
            required_effective_income,
            current_occupancy
        )
    )


    required_base_rent = max(
        required_potential_income
        - annual_other_income,
        0
    )


    break_even_rent_per_py_month = (
        safe_div(
            required_base_rent,
            (
                leasable_area_py
                * 12
            )
        )
    )


    return {

        "leasable_area_py":
            leasable_area_py,

        "monthly_rent":
            monthly_rent,

        "potential_income":
            potential_income,

        "effective_income":
            effective_income,

        "operating_expense":
            operating_expense,

        "noi":
            noi,

        "gross_yield":
            gross_yield,

        "cap_rate":
            cap_rate,

        "all_in_cap_rate":
            all_in_cap_rate,

        "acquisition_cost":
            acquisition_cost,

        "all_in_cost":
            all_in_cost,

        "loan_amount":
            loan_amount,

        "annual_debt_service":
            annual_debt_service,

        "dscr":
            dscr,

        "cash_flow":
            cash_flow,

        "initial_equity":
            initial_equity,

        "cash_on_cash":
            cash_on_cash,

        "estimated_value":
            estimated_value,

        "value_gap":
            value_gap,

        "land_price_py":
            land_price_py,

        "gross_area_price_py":
            gross_area_price_py,

        "break_even_occupancy":
            break_even_occupancy,

        "break_even_rent_per_py_month":
            break_even_rent_per_py_month
    }


# ============================================================
# 6. 프로그램 제목
# ============================================================

st.title(
    "🏢 부동산 종합 실무 분석 시스템"
)


st.caption(
    "토지 · 상가 · 공장 · 창고 · 아파트의 "
    "개발사업성과 매입·임대 수익성을 분석합니다."
)


# ============================================================
# 7. 왼쪽 메뉴
# ============================================================

st.sidebar.title(
    "🔎 분석 설정"
)


asset_type = st.sidebar.selectbox(
    "① 분석할 부동산",
    [
        "토지",
        "상가",
        "공장",
        "창고",
        "아파트"
    ]
)


# ------------------------------------------------------------
# 토지는 개발분석만
# 나머지는 개발 / 임대 선택
# ------------------------------------------------------------

if asset_type == "토지":

    analysis_mode = (
        "개발 / 분양 수지분석"
    )

    st.sidebar.info(
        "토지는 개발 / 분양 수지분석으로 진행합니다."
    )

else:

    analysis_mode = st.sidebar.radio(
        "② 분석 방식",
        [
            "개발 / 분양 수지분석",
            "매입 / 임대 수익분석"
        ]
    )


# ============================================================
# 8. 개발 / 분양 사업수지
# ============================================================

if analysis_mode == "개발 / 분양 수지분석":

    st.header(
        f"🏗️ {asset_type} 개발 · 분양 사업성 분석"
    )


    # ========================================================
    # 테스트 기본값
    # 시장 기준이 아니라 앱 테스트용
    # ========================================================

    defaults = {

        "토지": {
            "sale_price": 2000.0,
            "construction_cost": 800.0,
            "sale_ratio": 90
        },

        "상가": {
            "sale_price": 2500.0,
            "construction_cost": 900.0,
            "sale_ratio": 90
        },

        "공장": {
            "sale_price": 1200.0,
            "construction_cost": 600.0,
            "sale_ratio": 100
        },

        "창고": {
            "sale_price": 1100.0,
            "construction_cost": 550.0,
            "sale_ratio": 100
        },

        "아파트": {
            "sale_price": 2500.0,
            "construction_cost": 900.0,
            "sale_ratio": 100
        }
    }


    dv = defaults[
        asset_type
    ]


    # ========================================================
    # 1. 토지 / 사업 기본정보
    # ========================================================

    with st.sidebar.expander(
        "📍 1. 사업 / 토지 기본정보",
        expanded=True
    ):

        project_name = st.text_input(
            "사업명",
            value=f"{asset_type} 개발사업 검토"
        )


        address = st.text_input(
            "소재지"
        )


        zoning = st.text_input(
            "용도지역 / 지구"
        )


        land_area = st.number_input(
            "토지면적 (㎡)",
            min_value=1.0,
            value=3000.0,
            step=10.0
        )


        land_price_eok = st.number_input(
            "토지 매도희망가격 (억원)",
            min_value=0.0,
            value=100.0,
            step=1.0
        )


    # ========================================================
    # 2. 법적 / 개발조건
    # ========================================================

    with st.sidebar.expander(
        "🏢 2. 법적 / 개발 조건",
        expanded=True
    ):

        legal_bcr = st.number_input(
            "확인된 법정 건폐율 (%)",
            min_value=0.0,
            max_value=100.0,
            value=60.0,
            step=1.0
        )


        legal_far = st.number_input(
            "확인된 법정 용적률 (%)",
            min_value=0.0,
            max_value=3000.0,
            value=300.0,
            step=10.0
        )


        building_ratio = st.slider(
            "계획 건폐율 (%)",
            min_value=1,
            max_value=100,
            value=60
        )


        far_ratio = st.slider(
            "계획 용적률 (%)",
            min_value=10,
            max_value=2000,
            value=300,
            step=10
        )


        excluded_ratio = st.slider(
            "용적률 제외면적 비율 (%)",
            min_value=0,
            max_value=100,
            value=20,
            help=(
                "지하주차장, 기계실 등 "
                "용적률에는 포함되지 않지만 "
                "공사비가 발생하는 면적을 "
                "개략적으로 반영합니다."
            )
        )


        sale_area_ratio = st.slider(
            "분양면적 환산비율 (%)",
            min_value=1,
            max_value=150,
            value=dv["sale_ratio"]
        )


    # ========================================================
    # 3. 분양 / 공사조건
    # ========================================================

    with st.sidebar.expander(
        "💵 3. 분양 / 공사 조건",
        expanded=True
    ):

        sale_price_man = st.number_input(
            "평당 분양가 (만원/평)",
            min_value=0.0,
            value=dv["sale_price"],
            step=50.0
        )


        construction_cost_man = st.number_input(
            "평당 공사비 (만원/평)",
            min_value=0.0,
            value=dv["construction_cost"],
            step=10.0
        )


        acquisition_ratio = st.number_input(
            "토지취득 부대비율 (%)",
            min_value=0.0,
            max_value=30.0,
            value=5.0,
            step=0.1
        )


        other_cost_mode = st.radio(
            "기타사업비 입력방법",
            [
                "간편 비율",
                "상세 입력"
            ]
        )


        other_cost_ratio = 0

        demolition_cost = 0
        design_cost = 0
        permit_cost = 0
        marketing_cost = 0
        trust_fee = 0
        contingency = 0
        other_fixed_cost = 0


        if other_cost_mode == "간편 비율":

            other_cost_ratio = st.slider(
                "직접공사비 대비 기타사업비율 (%)",
                min_value=0,
                max_value=100,
                value=20
            )

        else:

            demolition_cost = (
                st.number_input(
                    "철거 / 토목비 (억원)",
                    min_value=0.0,
                    value=0.0
                )
                * 100_000_000
            )


            design_cost = (
                st.number_input(
                    "설계 / 감리비 (억원)",
                    min_value=0.0,
                    value=3.0
                )
                * 100_000_000
            )


            permit_cost = (
                st.number_input(
                    "인허가 / 부담금 (억원)",
                    min_value=0.0,
                    value=2.0
                )
                * 100_000_000
            )


            marketing_cost = (
                st.number_input(
                    "광고 / 분양대행비 (억원)",
                    min_value=0.0,
                    value=2.0
                )
                * 100_000_000
            )


            trust_fee = (
                st.number_input(
                    "신탁 / PF 수수료 (억원)",
                    min_value=0.0,
                    value=1.0
                )
                * 100_000_000
            )


            contingency = (
                st.number_input(
                    "예비비 (억원)",
                    min_value=0.0,
                    value=2.0
                )
                * 100_000_000
            )


            other_fixed_cost = (
                st.number_input(
                    "기타 비용 (억원)",
                    min_value=0.0,
                    value=0.0
                )
                * 100_000_000
            )


    # ========================================================
    # 4. 금융조건
    # ========================================================

    with st.sidebar.expander(
        "🏦 4. PF / 금융 조건",
        expanded=True
    ):

        debt_ratio = st.slider(
            "차입비율 (%)",
            min_value=0,
            max_value=100,
            value=60
        )


        interest_rate = st.number_input(
            "연 이자율 (%)",
            min_value=0.0,
            max_value=30.0,
            value=6.0,
            step=0.1
        )


        project_months = st.number_input(
            "전체 사업기간 (개월)",
            min_value=1,
            max_value=240,
            value=36,
            step=1
        )


        construction_months = st.number_input(
            "공사기간 (개월)",
            min_value=1,
            max_value=180,
            value=24,
            step=1
        )


        construction_draw_ratio = st.slider(
            "공사비 평균 집행률 (%)",
            min_value=0,
            max_value=100,
            value=50
        )


    # ========================================================
    # 5. 목표수익
    # ========================================================

    with st.sidebar.expander(
        "🎯 5. 목표 수익",
        expanded=True
    ):

        target_profit_mode = st.radio(
            "목표이익 계산방식",
            [
                "매출액 대비 목표이익률",
                "목표이익 금액"
            ]
        )


        target_profit_ratio = 0
        target_profit_fixed = 0


        if (
            target_profit_mode
            == "매출액 대비 목표이익률"
        ):

            target_profit_ratio = st.slider(
                "매출 대비 목표 사업이익률 (%)",
                min_value=0.0,
                max_value=50.0,
                value=15.0,
                step=0.5
            )

        else:

            target_profit_fixed = (
                st.number_input(
                    "목표 사업이익 (억원)",
                    min_value=0.0,
                    value=50.0
                )
                * 100_000_000
            )


    # ========================================================
    # 6. 자산별 실무조건
    # ========================================================

    special_rows = []


    with st.sidebar.expander(
        f"🔍 6. {asset_type} 추가정보",
        expanded=False
    ):

        if asset_type == "토지":

            planned_use = st.selectbox(
                "예정 개발용도",
                [
                    "상가",
                    "공장",
                    "창고",
                    "아파트",
                    "복합개발",
                    "기타"
                ]
            )


            special_rows = [
                [
                    "예정 개발용도",
                    planned_use
                ]
            ]


        elif asset_type == "상가":

            commercial_floors = st.number_input(
                "예상 상가 층수",
                min_value=1,
                value=3
            )


            parking_count = st.number_input(
                "예상 주차대수",
                min_value=0,
                value=20
            )


            frontage = st.number_input(
                "예상 전면폭 (m)",
                min_value=0.0,
                value=15.0
            )


            special_rows = [
                [
                    "예상 상가층수",
                    f"{commercial_floors}층"
                ],
                [
                    "예상 주차대수",
                    f"{parking_count}대"
                ],
                [
                    "예상 전면폭",
                    f"{frontage:,.1f}m"
                ]
            ]


        elif asset_type == "공장":

            power_kw = st.number_input(
                "계획 전력용량 (kW)",
                min_value=0.0,
                value=300.0
            )


            clear_height = st.number_input(
                "계획 유효층고 (m)",
                min_value=0.0,
                value=8.0
            )


            road_width = st.number_input(
                "진입도로 폭 (m)",
                min_value=0.0,
                value=8.0
            )


            crane = st.selectbox(
                "호이스트 / 크레인 계획",
                [
                    "확인 필요",
                    "있음",
                    "없음"
                ]
            )


            special_rows = [
                [
                    "전력용량",
                    f"{power_kw:,.0f}kW"
                ],
                [
                    "유효층고",
                    f"{clear_height:,.1f}m"
                ],
                [
                    "진입도로",
                    f"{road_width:,.1f}m"
                ],
                [
                    "호이스트/크레인",
                    crane
                ]
            ]


        elif asset_type == "창고":

            warehouse_type = st.selectbox(
                "창고 유형",
                [
                    "상온",
                    "저온",
                    "냉장",
                    "냉동",
                    "복합"
                ]
            )


            clear_height = st.number_input(
                "유효층고 (m)",
                min_value=0.0,
                value=10.0
            )


            dock_count = st.number_input(
                "Dock 수",
                min_value=0,
                value=4
            )


            floor_load = st.number_input(
                "바닥하중 (톤/㎡)",
                min_value=0.0,
                value=1.5,
                step=0.1
            )


            special_rows = [
                [
                    "창고유형",
                    warehouse_type
                ],
                [
                    "유효층고",
                    f"{clear_height:,.1f}m"
                ],
                [
                    "Dock 수",
                    dock_count
                ],
                [
                    "바닥하중",
                    f"{floor_load:,.1f}톤/㎡"
                ]
            ]


        elif asset_type == "아파트":

            avg_unit_area_py = st.number_input(
                "평균 세대당 공급면적 (평)",
                min_value=1.0,
                value=30.0,
                step=1.0
            )


            parking_per_unit = st.number_input(
                "세대당 계획 주차대수",
                min_value=0.0,
                value=1.2,
                step=0.1
            )


            special_rows = [
                [
                    "평균 세대당 공급면적",
                    f"{avg_unit_area_py:,.1f}평"
                ],
                [
                    "세대당 계획주차",
                    f"{parking_per_unit:,.1f}대"
                ]
            ]


    # ========================================================
    # 입력 데이터 묶음
    # ========================================================

    p = {

        "land_area":
            land_area,

        "land_price":
            land_price_eok
            * 100_000_000,

        "building_ratio":
            building_ratio,

        "far_ratio":
            far_ratio,

        "excluded_ratio":
            excluded_ratio,

        "sale_area_ratio":
            sale_area_ratio,

        "sale_price_py":
            sale_price_man
            * 10_000,

        "construction_cost_py":
            construction_cost_man
            * 10_000,

        "acquisition_ratio":
            acquisition_ratio,

        "other_cost_mode":
            other_cost_mode,

        "other_cost_ratio":
            other_cost_ratio,

        "demolition_cost":
            demolition_cost,

        "design_cost":
            design_cost,

        "permit_cost":
            permit_cost,

        "marketing_cost":
            marketing_cost,

        "trust_fee":
            trust_fee,

        "contingency":
            contingency,

        "other_fixed_cost":
            other_fixed_cost,

        "debt_ratio":
            debt_ratio,

        "interest_rate":
            interest_rate,

        "project_months":
            project_months,

        "construction_months":
            construction_months,

        "construction_draw_ratio":
            construction_draw_ratio,

        "target_profit_mode":
            target_profit_mode,

        "target_profit_ratio":
            target_profit_ratio,

        "target_profit_fixed":
            target_profit_fixed
    }


    # ========================================================
    # 계산 실행
    # ========================================================

    r = calculate_development(
        p
    )


    # ========================================================
    # 사업 기본 정보
    # ========================================================

    st.subheader(
        f"📌 {project_name}"
    )


    info1, info2, info3 = st.columns(3)


    info1.write(
        f"**소재지:** "
        f"{address if address else '-'}"
    )


    info2.write(
        f"**용도지역/지구:** "
        f"{zoning if zoning else '-'}"
    )


    info3.write(
        f"**분석자산:** "
        f"{asset_type}"
    )


    # ========================================================
    # 법정 기준 체크
    # ========================================================

    if (
        building_ratio <= legal_bcr
        and
        far_ratio <= legal_far
    ):

        st.success(
            "계획 건폐율과 용적률은 "
            "입력된 법정 기준 범위 안에 있습니다."
        )

    else:

        st.error(
            "계획 건폐율 또는 계획 용적률이 "
            "입력한 법정 기준을 초과합니다."
        )


    st.caption(
        "※ 본 앱은 사용자가 입력한 법정 기준과 계획값을 "
        "비교합니다. 실제 건축가능 여부를 자동 판정하지 않습니다."
    )


    # ========================================================
    # 핵심 KPI
    # ========================================================

    st.markdown(
        "## 💰 핵심 사업성"
    )


    k1, k2, k3, k4, k5 = st.columns(5)


    k1.metric(
        "현재 토지가격",
        format_eok(
            p["land_price"]
        )
    )


    k2.metric(
        "목표이익 기준 적정 토지가격",
        format_eok(
            r[
                "affordable_land_price"
            ]
        )
    )


    k3.metric(
        "적정가 - 현재가",
        format_eok(
            r[
                "land_price_gap"
            ]
        )
    )


    k4.metric(
        "예상 사업이익",
        format_eok(
            r[
                "project_profit"
            ]
        )
    )


    k5.metric(
        "사업 ROI",
        f"{r['roi']:,.1f}%"
    )


    # ========================================================
    # 아파트 예상 세대수
    # ========================================================

    if asset_type == "아파트":

        estimated_units = (
            safe_div(
                r["sale_area_py"],
                avg_unit_area_py
            )
        )


        estimated_parking = (
            estimated_units
            * parking_per_unit
        )


        st.info(
            f"현재 입력조건을 단순 환산하면 "
            f"약 **{estimated_units:,.0f}세대**, "
            f"계획 주차대수 약 "
            f"**{estimated_parking:,.0f}대**입니다. "
            f"실제 세대수는 평면계획, 코어, 주차, "
            f"인허가 등에 따라 달라집니다."
        )


    # ========================================================
    # 화면 탭
    # ========================================================

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        [
            "📊 종합",
            "📐 개발규모",
            "💰 사업수지",
            "📈 민감도",
            "📥 결과 저장"
        ]
    )


    # ========================================================
    # 종합
    # ========================================================

    with tab1:

        c1, c2, c3, c4 = st.columns(4)


        c1.metric(
            "총 분양매출",
            format_eok(
                r[
                    "sales_revenue"
                ]
            )
        )


        c2.metric(
            "총사업비",
            format_eok(
                r[
                    "total_project_cost"
                ]
            )
        )


        c3.metric(
            "사업이익률",
            f"{r['profit_margin']:,.1f}%"
        )


        c4.metric(
            "손익분기 분양가",
            (
                f"{r['break_even_sale_price'] / 10_000:,.0f}"
                "만원/평"
            )
        )


        chart_items = [

            (
                "토지매입비",
                p["land_price"]
            ),

            (
                "토지취득부대비",
                r["acquisition_cost"]
            ),

            (
                "직접공사비",
                r["direct_construction_cost"]
            ),

            (
                "기타사업비",
                r["other_project_cost"]
            ),

            (
                "토지금융비",
                r["land_finance_cost"]
            ),

            (
                "건설금융비",
                r[
                    "construction_finance_cost"
                ]
            )
        ]


        fig = go.Figure(
            go.Bar(
                y=[
                    name
                    for name, _
                    in chart_items
                ],
                x=[
                    value / 100_000_000
                    for _, value
                    in chart_items
                ],
                orientation="h",
                text=[
                    f"{value / 100_000_000:,.1f}억"
                    for _, value
                    in chart_items
                ],
                textposition="auto"
            )
        )


        fig.update_layout(
            title="사업비 구성",
            xaxis_title="억원",
            yaxis_title="",
            height=430
        )


        st.plotly_chart(
            fig,
            use_container_width=True
        )


    # ========================================================
    # 개발규모
    # ========================================================

    with tab2:

        development_rows = [

            [
                "토지면적",
                format_area(
                    land_area
                )
            ],

            [
                "건축면적",
                format_area(
                    r[
                        "building_area"
                    ]
                )
            ],

            [
                "용적률 산정 연면적",
                format_area(
                    r[
                        "far_floor_area"
                    ]
                )
            ],

            [
                "용적률 제외면적",
                format_area(
                    r[
                        "excluded_area"
                    ]
                )
            ],

            [
                "공사비 산정 연면적",
                format_area(
                    r[
                        "construction_area"
                    ]
                )
            ],

            [
                "예상 분양면적",
                format_area(
                    r[
                        "sale_area"
                    ]
                )
            ],

            [
                "이론상 평균 지상층수",
                f"{r['theoretical_floors']:,.2f}층"
            ],

            [
                "현재 토지 평당가격",
                (
                    f"{r['current_land_price_py'] / 10_000:,.0f}"
                    "만원/평"
                )
            ],

            [
                "적정 토지 평당가격",
                (
                    f"{r['affordable_land_price_py'] / 10_000:,.0f}"
                    "만원/평"
                )
            ]
        ]


        development_df = pd.DataFrame(
            development_rows,
            columns=[
                "항목",
                "결과"
            ]
        )


        st.dataframe(
            development_df,
            use_container_width=True,
            hide_index=True
        )


        if special_rows:

            st.subheader(
                f"{asset_type} 추가정보"
            )


            st.dataframe(
                pd.DataFrame(
                    special_rows,
                    columns=[
                        "항목",
                        "내용"
                    ]
                ),
                use_container_width=True,
                hide_index=True
            )


    # ========================================================
    # 사업수지
    # ========================================================

    with tab3:

        cost_rows = [

            [
                "매출",
                "총 분양매출",
                r["sales_revenue"]
            ],

            [
                "토지",
                "토지매입비",
                p["land_price"]
            ],

            [
                "토지",
                "토지취득 부대비",
                r["acquisition_cost"]
            ],

            [
                "공사",
                "직접공사비",
                r[
                    "direct_construction_cost"
                ]
            ],

            [
                "사업비",
                "기타사업비",
                r["other_project_cost"]
            ],

            [
                "금융",
                "토지금융비",
                r["land_finance_cost"]
            ],

            [
                "금융",
                "건설금융비",
                r[
                    "construction_finance_cost"
                ]
            ],

            [
                "합계",
                "총사업비",
                r["total_project_cost"]
            ],

            [
                "수익",
                "예상 사업이익",
                r["project_profit"]
            ],

            [
                "목표",
                "목표이익",
                r["target_profit"]
            ],

            [
                "토지가격",
                "적정 토지가격",
                r[
                    "affordable_land_price"
                ]
            ]
        ]


        cost_df = pd.DataFrame(
            cost_rows,
            columns=[
                "구분",
                "항목",
                "금액"
            ]
        )


        cost_df["억원"] = (
            cost_df["금액"]
            / 100_000_000
        ).round(2)


        st.dataframe(
            cost_df[
                [
                    "구분",
                    "항목",
                    "억원"
                ]
            ],
            use_container_width=True,
            hide_index=True
        )


    # ========================================================
    # 민감도 분석
    # ========================================================

    with tab4:

        st.write(
            "분양가와 공사비 변화에 따른 "
            "**목표이익 기준 적정 토지가격(억원)**입니다."
        )


        sale_changes = [
            -10,
            -5,
            0,
            5,
            10
        ]


        construction_changes = [
            -10,
            -5,
            0,
            5,
            10
        ]


        matrix = []


        for sale_change in sale_changes:

            row = []


            for construction_change in construction_changes:

                temp = p.copy()


                temp["sale_price_py"] = (
                    p["sale_price_py"]
                    * (
                        1
                        + sale_change / 100
                    )
                )


                temp["construction_cost_py"] = (
                    p["construction_cost_py"]
                    * (
                        1
                        + construction_change / 100
                    )
                )


                temp_result = (
                    calculate_development(
                        temp
                    )
                )


                row.append(
                    temp_result[
                        "affordable_land_price"
                    ]
                    / 100_000_000
                )


            matrix.append(
                row
            )


        sensitivity_df = pd.DataFrame(
            matrix,
            index=[
                f"분양가 {x:+d}%"
                for x in sale_changes
            ],
            columns=[
                f"공사비 {x:+d}%"
                for x in construction_changes
            ]
        )


        st.dataframe(
            sensitivity_df.round(1),
            use_container_width=True
        )


        heatmap = go.Figure(
            go.Heatmap(
                z=matrix,
                x=[
                    f"{x:+d}%"
                    for x in construction_changes
                ],
                y=[
                    f"{x:+d}%"
                    for x in sale_changes
                ],
                text=[
                    [
                        f"{value:,.1f}억"
                        for value in row
                    ]
                    for row in matrix
                ],
                texttemplate="%{text}",
                colorscale="RdYlGn",
                colorbar=dict(
                    title="억원"
                )
            )
        )


        heatmap.update_layout(
            title=(
                "분양가 × 공사비 변화에 따른 "
                "적정 토지가격"
            ),
            xaxis_title="공사비 변화",
            yaxis_title="분양가 변화",
            height=500
        )


        st.plotly_chart(
            heatmap,
            use_container_width=True
        )


    # ========================================================
    # 결과 저장
    # ========================================================

    with tab5:

        export_rows = [

            ["자산유형", asset_type],

            ["분석방식", analysis_mode],

            ["사업명", project_name],

            ["소재지", address],

            ["용도지역/지구", zoning],

            ["토지면적㎡", land_area],

            [
                "현재토지가격",
                p["land_price"]
            ],

            [
                "건축면적㎡",
                r["building_area"]
            ],

            [
                "용적률산정연면적㎡",
                r["far_floor_area"]
            ],

            [
                "공사비산정연면적㎡",
                r["construction_area"]
            ],

            [
                "예상분양면적㎡",
                r["sale_area"]
            ],

            [
                "총분양매출",
                r["sales_revenue"]
            ],

            [
                "총사업비",
                r["total_project_cost"]
            ],

            [
                "예상사업이익",
                r["project_profit"]
            ],

            [
                "사업ROI%",
                r["roi"]
            ],

            [
                "목표이익",
                r["target_profit"]
            ],

            [
                "적정토지가격",
                r[
                    "affordable_land_price"
                ]
            ]
        ]


        export_df = pd.DataFrame(
            export_rows,
            columns=[
                "항목",
                "값"
            ]
        )


        st.dataframe(
            export_df,
            use_container_width=True,
            hide_index=True
        )


        st.download_button(
            "📥 분석결과 CSV 다운로드",
            data=dataframe_to_csv(
                export_df
            ),
            file_name=(
                f"{asset_type}_개발사업_분석결과.csv"
            ),
            mime="text/csv",
            use_container_width=True
        )


# ============================================================
# 9. 매입 / 임대 수익 분석
# ============================================================

else:

    st.header(
        f"💵 {asset_type} 매입 · 임대 수익분석"
    )


    # ========================================================
    # 테스트 기본값
    # ========================================================

    defaults = {

        "상가": {
            "land_area": 500.0,
            "gross_area": 800.0,
            "leasable_area": 600.0,
            "price": 40.0,
            "rent": 10.0
        },

        "공장": {
            "land_area": 3300.0,
            "gross_area": 1500.0,
            "leasable_area": 1500.0,
            "price": 50.0,
            "rent": 3.0
        },

        "창고": {
            "land_area": 5000.0,
            "gross_area": 2500.0,
            "leasable_area": 2400.0,
            "price": 80.0,
            "rent": 4.0
        },

        "아파트": {
            "land_area": 1000.0,
            "gross_area": 3000.0,
            "leasable_area": 2500.0,
            "price": 100.0,
            "rent": 5.0
        }
    }


    dv = defaults[
        asset_type
    ]


    # ========================================================
    # 1. 물건 기본정보
    # ========================================================

    with st.sidebar.expander(
        "📍 1. 물건 기본정보",
        expanded=True
    ):

        property_name = st.text_input(
            "물건명",
            value=f"{asset_type} 매입 검토"
        )


        address = st.text_input(
            "소재지",
            key="income_address"
        )


        zoning = st.text_input(
            "용도지역 / 지구",
            key="income_zoning"
        )


        land_area = st.number_input(
            "토지면적 (㎡)",
            min_value=1.0,
            value=dv["land_area"],
            step=10.0
        )


        gross_floor_area = st.number_input(
            "건물 연면적 (㎡)",
            min_value=1.0,
            value=dv["gross_area"],
            step=10.0
        )


        leasable_area = st.number_input(
            "임대 가능면적 (㎡)",
            min_value=1.0,
            value=dv["leasable_area"],
            step=10.0
        )


        purchase_price_eok = st.number_input(
            "매입가격 / 매도희망가격 (억원)",
            min_value=0.0,
            value=dv["price"],
            step=1.0
        )


    # ========================================================
    # 2. 임대 조건
    # ========================================================

    with st.sidebar.expander(
        "💵 2. 임대 조건",
        expanded=True
    ):

        rent_mode = st.radio(
            "임대료 입력방법",
            [
                "평당 월세",
                "월세 총액"
            ]
        )


        rent_per_py = 0
        total_monthly_rent = 0


        if rent_mode == "평당 월세":

            rent_per_py = (
                st.number_input(
                    "월 임대료 (만원/평)",
                    min_value=0.0,
                    value=dv["rent"],
                    step=0.1
                )
                * 10_000
            )

        else:

            total_monthly_rent = (
                st.number_input(
                    "월 임대료 총액 (만원)",
                    min_value=0.0,
                    value=1000.0,
                    step=100.0
                )
                * 10_000
            )


        tenant_deposit = (
            st.number_input(
                "총 임대보증금 (억원)",
                min_value=0.0,
                value=2.0,
                step=0.5
            )
            * 100_000_000
        )


        vacancy_rate = st.slider(
            "예상 공실률 (%)",
            min_value=0.0,
            max_value=100.0,
            value=5.0,
            step=0.5
        )


        monthly_other_income = (
            st.number_input(
                "기타 월수입 (만원)",
                min_value=0.0,
                value=0.0,
                step=10.0
            )
            * 10_000
        )


    # ========================================================
    # 3. 운영 / 취득비
    # ========================================================

    with st.sidebar.expander(
        "🧾 3. 운영 / 취득 비용",
        expanded=True
    ):

        operating_expense_ratio = st.slider(
            "유효수입 대비 운영비율 (%)",
            min_value=0.0,
            max_value=100.0,
            value=15.0,
            step=0.5
        )


        annual_fixed_expense = (
            st.number_input(
                "연간 고정비용 (만원)",
                min_value=0.0,
                value=1000.0,
                step=100.0
            )
            * 10_000
        )


        acquisition_ratio = st.number_input(
            "취득 부대비율 (%)",
            min_value=0.0,
            max_value=30.0,
            value=5.0,
            step=0.1
        )


        capex = (
            st.number_input(
                "리모델링 / 추가투자비 (억원)",
                min_value=0.0,
                value=0.0,
                step=0.5
            )
            * 100_000_000
        )


    # ========================================================
    # 4. 금융조건
    # ========================================================

    with st.sidebar.expander(
        "🏦 4. 금융 조건",
        expanded=True
    ):

        debt_ratio = st.slider(
            "대출비율 / LTV (%)",
            min_value=0,
            max_value=100,
            value=60
        )


        interest_rate = st.number_input(
            "대출금리 (%)",
            min_value=0.0,
            max_value=30.0,
            value=5.5,
            step=0.1
        )


        loan_type = st.radio(
            "대출 상환방식",
            [
                "이자만 납부",
                "원리금 균등상환"
            ]
        )


        loan_term_years = st.number_input(
            "대출기간 (년)",
            min_value=1,
            max_value=50,
            value=20,
            step=1
        )


        use_deposit_as_funding = st.checkbox(
            "임대보증금을 초기 자금원으로 반영",
            value=True
        )


    # ========================================================
    # 5. 가치평가
    # ========================================================

    with st.sidebar.expander(
        "🎯 5. 가치 평가",
        expanded=True
    ):

        target_cap_rate = st.number_input(
            "목표 Cap Rate (%)",
            min_value=0.1,
            max_value=30.0,
            value=5.0,
            step=0.1
        )


    # ========================================================
    # 6. 자산별 현장 체크
    # ========================================================

    special_rows = []


    with st.sidebar.expander(
        f"🔍 6. {asset_type} 현장 체크",
        expanded=False
    ):

        if asset_type == "상가":

            floor_location = st.text_input(
                "주요 층",
                value="1층"
            )


            frontage = st.number_input(
                "전면폭 (m)",
                min_value=0.0,
                value=10.0
            )


            parking = st.number_input(
                "주차대수",
                min_value=0,
                value=5
            )


            special_rows = [
                [
                    "주요 층",
                    floor_location
                ],
                [
                    "전면폭",
                    f"{frontage:,.1f}m"
                ],
                [
                    "주차대수",
                    f"{parking}대"
                ]
            ]


        elif asset_type == "공장":

            factory_registration = st.selectbox(
                "공장등록",
                [
                    "확인 필요",
                    "등록 / 가능",
                    "미등록 / 불가"
                ]
            )


            power_kw = st.number_input(
                "전력용량 (kW)",
                min_value=0.0,
                value=300.0
            )


            clear_height = st.number_input(
                "유효층고 (m)",
                min_value=0.0,
                value=8.0
            )


            crane = st.selectbox(
                "호이스트 / 크레인",
                [
                    "확인 필요",
                    "있음",
                    "없음"
                ]
            )


            road_width = st.number_input(
                "진입도로 폭 (m)",
                min_value=0.0,
                value=8.0
            )


            special_rows = [
                [
                    "공장등록",
                    factory_registration
                ],
                [
                    "전력용량",
                    f"{power_kw:,.0f}kW"
                ],
                [
                    "유효층고",
                    f"{clear_height:,.1f}m"
                ],
                [
                    "호이스트/크레인",
                    crane
                ],
                [
                    "진입도로",
                    f"{road_width:,.1f}m"
                ]
            ]


        elif asset_type == "창고":

            warehouse_type = st.selectbox(
                "창고 유형",
                [
                    "상온",
                    "저온",
                    "냉장",
                    "냉동",
                    "복합"
                ]
            )


            clear_height = st.number_input(
                "유효층고 (m)",
                min_value=0.0,
                value=10.0
            )


            dock_count = st.number_input(
                "Dock 수",
                min_value=0,
                value=4
            )


            truck_access = st.selectbox(
                "대형차 진입",
                [
                    "확인 필요",
                    "가능",
                    "제한"
                ]
            )


            floor_load = st.number_input(
                "바닥하중 (톤/㎡)",
                min_value=0.0,
                value=1.5,
                step=0.1
            )


            special_rows = [
                [
                    "창고유형",
                    warehouse_type
                ],
                [
                    "유효층고",
                    f"{clear_height:,.1f}m"
                ],
                [
                    "Dock 수",
                    dock_count
                ],
                [
                    "대형차 진입",
                    truck_access
                ],
                [
                    "바닥하중",
                    f"{floor_load:,.1f}톤/㎡"
                ]
            ]


        elif asset_type == "아파트":

            unit_count = st.number_input(
                "세대수",
                min_value=1,
                value=30
            )


            completion_year = st.number_input(
                "준공연도",
                min_value=1900,
                max_value=2100,
                value=2015
            )


            parking = st.number_input(
                "주차대수",
                min_value=0,
                value=30
            )


            special_rows = [
                [
                    "세대수",
                    f"{unit_count}세대"
                ],
                [
                    "준공연도",
                    completion_year
                ],
                [
                    "주차대수",
                    f"{parking}대"
                ]
            ]


    # ========================================================
    # 계산 입력
    # ========================================================

    p = {

        "land_area":
            land_area,

        "gross_floor_area":
            gross_floor_area,

        "leasable_area":
            leasable_area,

        "purchase_price":
            purchase_price_eok
            * 100_000_000,

        "rent_mode":
            rent_mode,

        "rent_per_py":
            rent_per_py,

        "total_monthly_rent":
            total_monthly_rent,

        "tenant_deposit":
            tenant_deposit,

        "vacancy_rate":
            vacancy_rate,

        "monthly_other_income":
            monthly_other_income,

        "operating_expense_ratio":
            operating_expense_ratio,

        "annual_fixed_expense":
            annual_fixed_expense,

        "acquisition_ratio":
            acquisition_ratio,

        "capex":
            capex,

        "debt_ratio":
            debt_ratio,

        "interest_rate":
            interest_rate,

        "loan_type":
            loan_type,

        "loan_term_years":
            loan_term_years,

        "use_deposit_as_funding":
            use_deposit_as_funding,

        "target_cap_rate":
            target_cap_rate
    }


    # ========================================================
    # 계산
    # ========================================================

    r = calculate_income_property(
        p
    )


    # ========================================================
    # 물건 정보
    # ========================================================

    st.subheader(
        f"📌 {property_name}"
    )


    info1, info2, info3 = st.columns(3)


    info1.write(
        f"**소재지:** "
        f"{address if address else '-'}"
    )


    info2.write(
        f"**용도지역/지구:** "
        f"{zoning if zoning else '-'}"
    )


    info3.write(
        f"**자산유형:** {asset_type}"
    )


    # ========================================================
    # KPI
    # ========================================================

    st.markdown(
        "## 💰 핵심 수익성"
    )


    k1, k2, k3, k4, k5 = st.columns(5)


    k1.metric(
        "매입가격",
        format_eok(
            p[
                "purchase_price"
            ]
        )
    )


    k2.metric(
        "연간 NOI",
        format_eok(
            r["noi"]
        )
    )


    k3.metric(
        "Cap Rate",
        f"{r['cap_rate']:,.2f}%"
    )


    k4.metric(
        "현금수익률",
        f"{r['cash_on_cash']:,.2f}%"
    )


    k5.metric(
        "DSCR",
        f"{r['dscr']:,.2f}"
    )


    # ========================================================
    # 가치평가
    # ========================================================

    st.markdown(
        "## 🎯 수익환원 가치"
    )


    v1, v2, v3, v4 = st.columns(4)


    v1.metric(
        "목표 Cap Rate 기준 가치",
        format_eok(
            r["estimated_value"]
        )
    )


    v2.metric(
        "가치 - 매입가격",
        format_eok(
            r["value_gap"]
        )
    )


    v3.metric(
        "손익분기 임대율",
        f"{r['break_even_occupancy']:,.1f}%"
    )


    v4.metric(
        "손익분기 평당 월세",
        (
            f"{r['break_even_rent_per_py_month'] / 10_000:,.2f}"
            "만원/평"
        )
    )


    # ========================================================
    # 경고
    # ========================================================

    if r["dscr"] < 1:

        st.warning(
            "현재 입력조건에서는 "
            "NOI가 연간 대출상환액보다 작게 계산됩니다."
        )


    if r["initial_equity"] <= 0:

        st.warning(
            "대출과 보증금이 전체 취득원가 이상으로 계산되어 "
            "자기자본수익률 해석에 주의가 필요합니다."
        )


    # ========================================================
    # 화면 탭
    # ========================================================

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        [
            "📊 종합",
            "💵 수익분석",
            "🏢 물건분석",
            "📈 민감도",
            "📥 결과 저장"
        ]
    )


    # ========================================================
    # 종합
    # ========================================================

    with tab1:

        c1, c2, c3 = st.columns(3)


        c1.metric(
            "잠재 연간 총수입",
            format_eok(
                r[
                    "potential_income"
                ]
            )
        )


        c2.metric(
            "공실반영 유효수입",
            format_eok(
                r[
                    "effective_income"
                ]
            )
        )


        c3.metric(
            "총 취득원가",
            format_eok(
                r[
                    "all_in_cost"
                ]
            )
        )


        chart_names = [
            "유효수입",
            "운영비",
            "NOI",
            "대출상환액",
            "세전 현금흐름"
        ]


        chart_values = [
            r["effective_income"]
            / 100_000_000,

            r["operating_expense"]
            / 100_000_000,

            r["noi"]
            / 100_000_000,

            r["annual_debt_service"]
            / 100_000_000,

            r["cash_flow"]
            / 100_000_000
        ]


        fig = go.Figure(
            go.Bar(
                x=chart_names,
                y=chart_values,
                text=[
                    f"{x:,.2f}억"
                    for x in chart_values
                ],
                textposition="auto"
            )
        )


        fig.update_layout(
            title="연간 수익구조",
            yaxis_title="억원",
            height=430
        )


        st.plotly_chart(
            fig,
            use_container_width=True
        )


    # ========================================================
    # 수익분석
    # ========================================================

    with tab2:

        rows = [

            [
                "잠재 연간 총수입",
                r["potential_income"]
            ],

            [
                "공실 반영 유효수입",
                r["effective_income"]
            ],

            [
                "운영비",
                r["operating_expense"]
            ],

            [
                "NOI",
                r["noi"]
            ],

            [
                "취득 부대비",
                r["acquisition_cost"]
            ],

            [
                "총 취득원가",
                r["all_in_cost"]
            ],

            [
                "대출금액",
                r["loan_amount"]
            ],

            [
                "연간 대출상환액",
                r[
                    "annual_debt_service"
                ]
            ],

            [
                "필요 자기자본",
                r["initial_equity"]
            ],

            [
                "세전 현금흐름",
                r["cash_flow"]
            ]
        ]


        income_df = pd.DataFrame(
            rows,
            columns=[
                "항목",
                "금액"
            ]
        )


        income_df["억원"] = (
            income_df["금액"]
            / 100_000_000
        ).round(2)


        st.dataframe(
            income_df[
                [
                    "항목",
                    "억원"
                ]
            ],
            use_container_width=True,
            hide_index=True
        )


        y1, y2, y3 = st.columns(3)


        y1.metric(
            "Gross Yield",
            f"{r['gross_yield']:,.2f}%"
        )


        y2.metric(
            "Cap Rate",
            f"{r['cap_rate']:,.2f}%"
        )


        y3.metric(
            "총 취득원가 기준 Cap Rate",
            f"{r['all_in_cap_rate']:,.2f}%"
        )


    # ========================================================
    # 물건분석
    # ========================================================

    with tab3:

        rows = [

            [
                "토지면적",
                format_area(
                    land_area
                )
            ],

            [
                "건물 연면적",
                format_area(
                    gross_floor_area
                )
            ],

            [
                "임대 가능면적",
                format_area(
                    leasable_area
                )
            ],

            [
                "토지면적 기준 평당 매입가",
                (
                    f"{r['land_price_py'] / 10_000:,.0f}"
                    "만원/평"
                )
            ],

            [
                "연면적 기준 평당 매입가",
                (
                    f"{r['gross_area_price_py'] / 10_000:,.0f}"
                    "만원/평"
                )
            ],

            [
                "공실률",
                f"{vacancy_rate:,.1f}%"
            ],

            [
                "운영비율",
                f"{operating_expense_ratio:,.1f}%"
            ],

            [
                "대출비율",
                f"{debt_ratio:,.1f}%"
            ],

            [
                "DSCR",
                f"{r['dscr']:,.2f}"
            ],

            [
                "현금수익률",
                f"{r['cash_on_cash']:,.2f}%"
            ]
        ]


        st.dataframe(
            pd.DataFrame(
                rows,
                columns=[
                    "항목",
                    "결과"
                ]
            ),
            use_container_width=True,
            hide_index=True
        )


        if special_rows:

            st.subheader(
                f"{asset_type} 현장 체크사항"
            )


            st.dataframe(
                pd.DataFrame(
                    special_rows,
                    columns=[
                        "확인항목",
                        "내용"
                    ]
                ),
                use_container_width=True,
                hide_index=True
            )


    # ========================================================
    # 민감도
    # ========================================================

    with tab4:

        st.write(
            "임대료와 목표 Cap Rate 변화에 따른 "
            "**수익환원가치(억원)** 입니다."
        )


        rent_changes = [
            -10,
            -5,
            0,
            5,
            10
        ]


        cap_changes = [
            -1.0,
            -0.5,
            0.0,
            0.5,
            1.0
        ]


        matrix = []


        for rent_change in rent_changes:

            row = []


            for cap_change in cap_changes:

                temp = p.copy()


                if (
                    temp["rent_mode"]
                    == "평당 월세"
                ):

                    temp["rent_per_py"] = (
                        p["rent_per_py"]
                        * (
                            1
                            + rent_change / 100
                        )
                    )

                else:

                    temp[
                        "total_monthly_rent"
                    ] = (
                        p[
                            "total_monthly_rent"
                        ]
                        * (
                            1
                            + rent_change / 100
                        )
                    )


                temp[
                    "target_cap_rate"
                ] = max(
                    0.1,
                    target_cap_rate
                    + cap_change
                )


                temp_result = (
                    calculate_income_property(
                        temp
                    )
                )


                row.append(
                    temp_result[
                        "estimated_value"
                    ]
                    / 100_000_000
                )


            matrix.append(row)


        sensitivity_df = pd.DataFrame(
            matrix,
            index=[
                f"임대료 {x:+d}%"
                for x in rent_changes
            ],
            columns=[
                f"Cap {x:+.1f}%p"
                for x in cap_changes
            ]
        )


        st.dataframe(
            sensitivity_df.round(1),
            use_container_width=True
        )


        heatmap = go.Figure(
            go.Heatmap(
                z=matrix,
                x=[
                    f"{x:+.1f}%p"
                    for x in cap_changes
                ],
                y=[
                    f"{x:+d}%"
                    for x in rent_changes
                ],
                text=[
                    [
                        f"{value:,.1f}억"
                        for value in row
                    ]
                    for row in matrix
                ],
                texttemplate="%{text}",
                colorscale="RdYlGn",
                colorbar=dict(
                    title="억원"
                )
            )
        )


        heatmap.update_layout(
            title=(
                "임대료 × 목표 Cap Rate "
                "수익환원가치"
            ),
            xaxis_title="목표 Cap Rate 변화",
            yaxis_title="임대료 변화",
            height=500
        )


        st.plotly_chart(
            heatmap,
            use_container_width=True
        )


    # ========================================================
    # 결과 저장
    # ========================================================

    with tab5:

        export_rows = [

            ["자산유형", asset_type],

            ["분석방식", analysis_mode],

            ["물건명", property_name],

            ["소재지", address],

            ["용도지역/지구", zoning],

            ["토지면적㎡", land_area],

            [
                "건물연면적㎡",
                gross_floor_area
            ],

            [
                "임대가능면적㎡",
                leasable_area
            ],

            [
                "매입가격",
                p["purchase_price"]
            ],

            [
                "잠재연간총수입",
                r["potential_income"]
            ],

            [
                "유효수입",
                r["effective_income"]
            ],

            [
                "NOI",
                r["noi"]
            ],

            [
                "CapRate%",
                r["cap_rate"]
            ],

            [
                "대출금액",
                r["loan_amount"]
            ],

            [
                "DSCR",
                r["dscr"]
            ],

            [
                "초기필요자기자본",
                r["initial_equity"]
            ],

            [
                "현금수익률%",
                r["cash_on_cash"]
            ],

            [
                "목표CapRate기준가치",
                r["estimated_value"]
            ],

            [
                "가치-매입가격",
                r["value_gap"]
            ]
        ]


        export_df = pd.DataFrame(
            export_rows,
            columns=[
                "항목",
                "값"
            ]
        )


        st.dataframe(
            export_df,
            use_container_width=True,
            hide_index=True
        )


        st.download_button(
            "📥 분석결과 CSV 다운로드",
            data=dataframe_to_csv(
                export_df
            ),
            file_name=(
                f"{asset_type}_임대수익_분석결과.csv"
            ),
            mime="text/csv",
            use_container_width=True
        )


# ============================================================
# 10. 프로그램 공통 안내
# ============================================================

st.divider()


st.info(
    """
### 프로그램 사용 시 유의사항

이 프로그램은 부동산 실무에서
초기 사업성 및 투자수익성을 빠르게 검토하기 위한
**의사결정 보조도구**입니다.

**개발사업**

법정 건폐율·용적률은 사용자가 확인한 값을 직접 입력합니다.

실제 건축 가능규모는
도로조건, 주차기준, 높이제한, 일조,
건축선, 지구단위계획, 각종 심의 및
개별 인허가조건 등에 따라 달라질 수 있습니다.

**임대수익 분석**

NOI, Cap Rate, DSCR 및 현금수익률은
사용자가 입력한 임대료, 공실률,
운영비와 금융조건을 기준으로 계산합니다.

**금융**

개발사업 금융비는 초기 사업성 검토를 위한
단순화된 모델입니다.

실제 PF와 담보대출은
취급수수료, 브릿지론, 본PF,
대출 실행시기 및 상환조건 등을
추가 검토해야 합니다.

본 프로그램의 테스트 기본값은
법적 기준이나 시장 표준값을 의미하지 않습니다.
실제 물건 분석 시 확인된 값을 입력하세요.
"""
)
