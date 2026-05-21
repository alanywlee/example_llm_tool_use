from __future__ import annotations

import re


KM_KEYWORDS = [
    "政策", "SOP", "流程", "FAQ", "文件", "知識庫", "KM", "規定",
    "報銷", "權限", "資安", "客服", "案件", "升級", "RCA",
    "方案", "價格", "產品", "比較", "摘要", "整理", "查", "搜尋",
    "剛剛", "上面", "前面", "它", "這個", "那些",
]

CALCULATION_KEYWORDS = [
    "計算", "算", "多少", "幾 %", "幾%", "百分比", "比例",
    "平均", "總和", "合計", "折扣", "打折", "利率",
    "複利", "加總", "差多少", "稅後", "未稅", "含稅",
]

MATH_SYMBOL_PATTERN = re.compile(r"\d\s*[+\-*/%()]\s*\d")


def needs_km_search(user_input: str) -> bool:
    return any(keyword in user_input for keyword in KM_KEYWORDS)


def needs_calculation(user_input: str) -> bool:
    if any(keyword in user_input for keyword in CALCULATION_KEYWORDS):
        return True
    if MATH_SYMBOL_PATTERN.search(user_input):
        return True
    return False


def select_skills_for_turn(user_input: str) -> list[str]:
    selected = []

    if needs_km_search(user_input):
        selected.append("enterprise_km_search")

    if needs_calculation(user_input):
        selected.append("calculator")

    return selected
