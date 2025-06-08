import pandas as pd

def make_embedding_text(row):
    def safe(val):
        if pd.isna(val) or not val or str(val).strip() == "" or str(val).strip().lower() == "nan":
            return "-"
        return val
    return (
        f"{safe(row['FCLTY_NM'])}은(는) {safe(row['CTPRVN_NM'])} {safe(row['SIGNGU_NM'])}의 {safe(row['RDNMADR_NM'])}에서 "
        f"{safe(row['FSTVL_BEGIN_DE'])}부터 {safe(row['FSTVL_END_DE'])}까지 열립니다. "
        f"주최: {safe(row['MNNST_NM'])}. 주요 프로그램: {safe(row['FSTVL_CN'])}. "
        f"문의: {safe(row['TEL_NO'])}. 홈페이지: {safe(row['HMPG_ADDR'])}."
    )