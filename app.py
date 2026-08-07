import re
from PIL import Image
import easyocr
import streamlit as st

# ページ基本設定
st.set_page_config(
    page_title="原神 聖遺物スコア計算", page_icon="⚔️", layout="centered"
)

st.title("⚔️ 原神 聖遺物一括スコア計算")


# OCRリーダーのキャッシュ
@st.cache_resource
def load_ocr():
    return easyocr.Reader(["en"])


reader = load_ocr()


def parse_stat_value(raw_text):
    """数値と%の有無を判定"""
    match = re.search(r"(\d+(?:\.\d+)?)", raw_text)
    if not match:
        return 0.0, False
    val = float(match.group(1))
    has_percent = "%" in raw_text
    return val, has_percent


def auto_crop_mainstat(image):
    """(1052, 130, 1710, 184) の座標を指定した割合(%)に変換して切り抜き"""
    width, height = image.size
    left = int(width * 0.548)
    top = int(height * 0.120)
    right = int(width * 0.890)
    bottom = int(height * 0.170)

    return image.crop((left, top, right, bottom))


def auto_crop_substats(image):
    """サブステータス領域の割合切り抜き"""
    width, height = image.size
    left = int(width * 0.50)
    top = int(height * 0.20)
    right = int(width * 0.95)
    bottom = int(height * 0.50)

    return image.crop((left, top, right, bottom))


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
        # 熟知のみ0.25倍を適用
        selected_val = stats.get("Elemental Mastery", {}).get("val", 0.0) * 0.25

    return selected_val + crit_dmg + (crit_rate * 2)


# --------------------
# UI・操作エリア
# --------------------

show_debug = st.sidebar.checkbox("デバッグ表示（切り抜き領域の確認）")

uploaded_files = st.file_uploader(
    "聖遺物の画像をまとめて選択してください",
    type=["png", "jpg", "jpeg"],
    accept_multiple_files=True,
)

if uploaded_files:
    if (
        "processed_data" not in st.session_state
        or st.session_state.get("file_count") != len(uploaded_files)
    ):
        processed_data = []
        allowed = [
            "CRIT Rate",
            "CRIT DMG",
            "ATK",
            "HP",
            "DEF",
            "Elemental Mastery",
            "Energy Recharge",
        ]

        progress_bar = st.progress(0, text="解析中...")

        for idx, file in enumerate(uploaded_files):
            image = Image.open(file)

            # 1. メインステータス読み取り
            main_crop = auto_crop_mainstat(image)
            main_crop.save("temp_main_crop.png")
            main_result = reader.readtext("temp_main_crop.png")
            main_stat_name = (
                main_result[0][1] if len(main_result) > 0 else "不明"
            )

            # 2. サブステータス読み取り
            sub_crop = auto_crop_substats(image)
            sub_crop.save("temp_sub_crop.png")
            result = reader.readtext("temp_sub_crop.png")

            stats = {}
            for i in range(len(result) - 1):
                name = result[i][1]
                if name in allowed:
                    raw_val_text = result[i + 1][1]
                    val, is_percent = parse_stat_value(raw_val_text)
                    stats[name] = {"val": val, "is_percent": is_percent}

            processed_data.append(
                {
                    "filename": file.name,
                    "main_stat": main_stat_name,
                    "stats": stats,
                    "main_crop": main_crop,
                    "sub_crop": sub_crop,
                }
            )
            progress_bar.progress(
                (idx + 1) / len(uploaded_files),
                text=f"解析中... ({idx+1}/{len(uploaded_files)})",
            )

        st.session_state["processed_data"] = processed_data
        st.session_state["file_count"] = len(uploaded_files)
        progress_bar.empty()

    # デバッグ表示
    if show_debug:
        st.subheader("🔍 デバッグ：切り抜かれた領域")
        for item in st.session_state["processed_data"]:
            st.write(f"**{item['filename']}**")
            st.image(
                item["main_crop"],
                caption=f"メインステ切り抜き: {item['main_stat']}",
                width=200,
            )
            st.image(
                item["sub_crop"], caption="サブステ切り抜き", width=300
            )

    # 計算方法の選択
    st.markdown("---")
    build_type = st.radio(
        "計算方法を選択してください",
        ["攻撃", "熟知", "防御", "元チャ", "HP"],
        horizontal=True,
    )

    # 各要素のスコア計算と並び替え
    data = st.session_state["processed_data"]
    results = []
    for item in data:
        score = calculate_score(item["stats"], build_type)
        results.append({**item, "score": score})

    # スコアの高い順にソート (降順)
    results = sorted(results, key=lambda x: x["score"], reverse=True)

    # 結果表示
    st.subheader("📊 スコア結果一覧（スコア順）")

    for item in results:
        score = item["score"]

        with st.container(border=True):
            col1, col2 = st.columns([3, 1])

            with col1:
                st.markdown(f"**📄 {item['filename']}**")
                st.caption(f"👑 メイン: **{item['main_stat']}**")

                stats = item["stats"]
                details = []
                if "CRIT Rate" in stats and stats["CRIT Rate"]["is_percent"]:
                    details.append(f"率:{stats['CRIT Rate']['val']}%")
                if "CRIT DMG" in stats and stats["CRIT DMG"]["is_percent"]:
                    details.append(f"ダメ:{stats['CRIT DMG']['val']}%")

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