import re
import easyocr
import numpy as np
from PIL import Image
import streamlit as st

# ページ基本設定
st.set_page_config(page_title="原神 聖遺物スコア計算", layout="centered")

st.title("原神 聖遺物一括スコア計算")

# ステータス名の日本語変換マッピング
STAT_NAME_MAP = {
    "ATK": "攻撃",
    "CRIT Rate": "会心率",
    "CRIT DMG": "会心ダメ",
    "Elemental Mastery": "熟知",
    "DEF": "防御",
    "Energy Recharge": "元チャ",
    "HP": "HP",
}

# 部位（種類）のマッピング
ARTIFACT_TYPES = {
    "Flower of Life": "花",
    "Plume of Death": "羽",
    "Sands of Eon": "時計",
    "Goblet of Eonothem": "杯",
    "Circlet of Logos": "冠",
}


# OCRリーダーのキャッシュ
@st.cache_resource
def load_ocr():
    return easyocr.Reader(["en"])


reader = load_ocr()


def translate_text(text):
    """OCRで読み取った英字テキストを日本語表記に変換"""
    translated = text
    for eng, jpn in STAT_NAME_MAP.items():
        translated = re.sub(rf"\b{eng}\b", jpn, translated, flags=re.IGNORECASE)
    return translated


def parse_artifact_type(raw_text):
    """部位テキストから該当する日本語部位名を判定"""
    for eng, jpn in ARTIFACT_TYPES.items():
        if eng.lower() in raw_text.lower():
            return jpn
    return "読み取れなかったもの"


def read_text_from_image(pil_image):
    """PIL画像をNumPy配列に変換してからOCR実行"""
    if pil_image is None:
        return []
    np_image = np.array(pil_image)
    return reader.readtext(np_image, detail=0)  # テキスト文字列の配列のみ取得


def parse_substats_from_text_list(text_list):
    """認識されたテキスト文字列のリスト全体からサブステータスと数値を一括抽出"""
    full_text = " ".join(text_list)
    stats = {}

    # 各ステータスの検知パターン (正規表現)
    patterns = {
        "CRIT Rate": r"(CRIT\s*Rate|CRIT\s*Rate%?|Crit\s*Rate)[^\d]*(\d+(?:\.\d+)?)",
        "CRIT DMG": r"(CRIT\s*DMG|CRIT\s*Dmg|Crit\s*DMG)[^\d]*(\d+(?:\.\d+)?)",
        "ATK": r"(ATK)[^\d]*(\d+(?:\.\d+)?)",
        "DEF": r"(DEF)[^\d]*(\d+(?:\.\d+)?)",
        "HP": r"(HP)[^\d]*(\d+(?:\.\d+)?)",
        "Energy Recharge": r"(Energy\s*Recharge|Energy\s*Rech\w*)[^\d]*(\d+(?:\.\d+)?)",
        "Elemental Mastery": r"(Elemental\s*Mastery|Elemental\s*Mas\w*)[^\d]*(\d+(?:\.\d+)?)",
    }

    for stat_key, pattern in patterns.items():
        match = re.search(pattern, full_text, re.IGNORECASE)
        if match:
            val_str = match.group(2)
            try:
                val = float(val_str)
            except ValueError:
                continue

            # マッチした文字列前後のコンテキストからパーセント有無を判定
            match_segment = full_text[match.start():match.end() + 5]
            has_percent = "%" in match_segment

            stats[stat_key] = {"val": val, "is_percent": has_percent}

    return stats, full_text


# --- 切り抜き関数（高精度） ---
def high_crop_mainstat(image):
    width, height = image.size
    return image.crop((
        int(width * 0.500),
        int(height * 0.100),
        int(width * 0.950),
        int(height * 0.250),
    ))


def high_crop_substats(image):
    width, height = image.size
    return image.crop((
        int(width * 0.450),
        int(height * 0.180),
        int(width * 0.980),
        int(height * 0.600),
    ))


# --- 切り抜き関数（通常） ---
def normal_crop_type(image):
    width, height = image.size
    return image.crop((
        int(width * (1200 / 1920)),
        int(height * (200 / 1080)),
        int(width * (1650 / 1920)),
        int(height * (320 / 1080)),
    ))


def normal_crop_mainstat(image):
    width, height = image.size
    return image.crop((
        int(width * (1200 / 1920)),
        int(height * (280 / 1080)),
        int(width * (1600 / 1920)),
        int(height * (440 / 1080)),
    ))


def normal_crop_substats(image):
    width, height = image.size
    return image.crop((
        int(width * (1200 / 1920)),
        int(height * (550 / 1080)),
        int(width * (1700 / 1920)),
        int(height * (820 / 1080)),
    ))


def calculate_score(stats, build):
    """スコア計算ロジック"""
    crit_rate = (
        stats.get("CRIT Rate", {}).get("val", 0.0)
        if stats.get("CRIT Rate", {}).get("is_percent")
        else 0.0
    )
    crit_dmg = (
        stats.get("CRIT DMG", {}).get("val", 0.0)
        if stats.get("CRIT DMG", {}).get("is_percent")
        else 0.0
    )

    selected_val = 0.0
    if build == "攻撃" and stats.get("ATK", {}).get("is_percent"):
        selected_val = stats["ATK"]["val"]
    elif build == "防御" and stats.get("DEF", {}).get("is_percent"):
        selected_val = stats["DEF"]["val"]
    elif build == "HP" and stats.get("HP", {}).get("is_percent"):
        selected_val = stats["HP"]["val"]
    elif build == "元チャ" and stats.get("Energy Recharge", {}).get("is_percent"):
        selected_val = stats["Energy Recharge"]["val"]
    elif build == "熟知":
        selected_val = stats.get("Elemental Mastery", {}).get("val", 0.0) * 0.25

    return selected_val + crit_dmg + (crit_rate * 2)


# --------------------
# UI・操作エリア
# --------------------

st.sidebar.header("設定")
mode = st.sidebar.radio(
    "判定モード", ["通常判定", "高精度判定"], help="画像の表示形式に合わせて選択"
)
show_debug = st.sidebar.checkbox("デバッグ表示（切り抜き領域とRAW文字列の確認）")

uploaded_files = st.file_uploader(
    f"聖遺物の画像をまとめて選択してください ({mode})",
    type=["png", "jpg", "jpeg"],
    accept_multiple_files=True,
)

if uploaded_files:
    session_key = f"processed_data_{mode}"

    if (
        session_key not in st.session_state
        or st.session_state.get(f"file_count_{mode}") != len(uploaded_files)
    ):
        processed_data = []
        progress_bar = st.progress(0, text="解析中...")

        for idx, file in enumerate(uploaded_files):
            image = Image.open(file).convert("RGB")

            if mode == "通常判定":
                type_crop = normal_crop_type(image)
                main_crop = normal_crop_mainstat(image)
                sub_crop = normal_crop_substats(image)

                type_res = read_text_from_image(type_crop)
                raw_type_text = " ".join(type_res) if type_res else ""
                artifact_type = parse_artifact_type(raw_type_text)

            else:  # 高精度判定
                type_crop = None
                main_crop = high_crop_mainstat(image)
                sub_crop = high_crop_substats(image)
                artifact_type = "未設定"

            # メインステ解析
            main_res = read_text_from_image(main_crop)
            raw_main_text = " ".join(main_res) if main_res else "不明"
            main_stat_name = translate_text(raw_main_text)

            # サブステ解析 (新しいロジック)
            sub_res = read_text_from_image(sub_crop)
            stats, raw_sub_text = parse_substats_from_text_list(sub_res)

            processed_data.append({
                "filename": file.name,
                "artifact_type": artifact_type,
                "main_stat": main_stat_name,
                "stats": stats,
                "raw_sub_text": raw_sub_text,
                "type_crop": type_crop,
                "main_crop": main_crop,
                "sub_crop": sub_crop,
            })
            progress_bar.progress(
                (idx + 1) / len(uploaded_files),
                text=f"解析中... ({idx+1}/{len(uploaded_files)})",
            )

        st.session_state[session_key] = processed_data
        st.session_state[f"file_count_{mode}"] = len(uploaded_files)
        progress_bar.empty()

    data = st.session_state[session_key]

    # デバッグ表示
    if show_debug:
        st.subheader("デバッグ情報")
        for item in data:
            st.write(f"**ファイル名: {item['filename']}**")
            st.write(f"**OCR取得テキスト**: `{item['raw_sub_text']}`")
            st.write(f"**抽出サブステ**: `{item['stats']}`")
            col_a, col_b = st.columns(2)
            with col_a:
                if item["type_crop"]:
                    st.image(
                        item["type_crop"],
                        caption=f"部位: {item['artifact_type']}",
                        width=200,
                    )
                st.image(
                    item["main_crop"],
                    caption=f"メイン: {item['main_stat']}",
                    width=200,
                )
            with col_b:
                st.image(item["sub_crop"], caption="サブステ領域", width=250)
            st.markdown("---")

    st.markdown("---")

    # 通常判定時の部位絞り込みフィルター
    selected_type = "すべて"
    if mode == "通常判定":
        selected_type = st.selectbox(
            "部位で絞り込み",
            [
                "すべて",
                "花",
                "羽",
                "時計",
                "杯",
                "冠",
                "読み取れなかったもの",
            ],
        )

    # 計算方法の選択
    build_type = st.radio(
        "計算方法を選択してください",
        ["攻撃", "熟知", "防御", "元チャ", "HP"],
        horizontal=True,
    )

    # 各要素のスコア計算と並び替え
    results = []
    for item in data:
        if mode == "通常判定" and selected_type != "すべて":
            if item["artifact_type"] != selected_type:
                continue

        score = calculate_score(item["stats"], build_type)
        results.append({**item, "score": score})

    # スコアの高い順にソート (降順)
    results = sorted(results, key=lambda x: x["score"], reverse=True)

    # 結果表示
    st.subheader(
        f"スコア結果一覧（スコア順 / 該当件数: {len(results)}件）"
    )

    for item in results:
        score = item["score"]

        with st.container(border=True):
            col1, col2 = st.columns([3, 1])

            with col1:
                st.markdown(f"**{item['filename']}**")

                type_info = (
                    f" / 部位: **{item['artifact_type']}**"
                    if mode == "通常判定"
                    else ""
                )
                st.caption(f"メイン: **{item['main_stat']}**{type_info}")

                stats = item["stats"]
                details = []
                if "CRIT Rate" in stats and stats["CRIT Rate"]["is_percent"]:
                    details.append(f"会心率:{stats['CRIT Rate']['val']}%")
                if "CRIT DMG" in stats and stats["CRIT DMG"]["is_percent"]:
                    details.append(f"会心ダメ:{stats['CRIT DMG']['val']}%")

                target_key = {
                    "攻撃": "ATK",
                    "防御": "DEF",
                    "HP": "HP",
                    "元チャ": "Energy Recharge",
                    "熟知": "Elemental Mastery",
                }[build_type]

                if target_key in stats:
                    st_val = stats[target_key]
                    if build_type == "熟知" or st_val["is_percent"]:
                        unit = "" if build_type == "熟知" else "%"
                        details.append(f"{build_type}:{st_val['val']}{unit}")

                detail_text = (
                    " / ".join(details) if details else "対象ステータスなし"
                )
                st.caption(f"サブ: ({detail_text})")

            with col2:
                score_str = f"{score:.1f}"
                if score >= 40:
                    st.metric(
                        label="スコア", value=score_str, delta="高スコア"
                    )
                else:
                    st.metric(label="スコア", value=score_str)