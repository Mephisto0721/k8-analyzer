import streamlit as st
import pandas as pd
from collections import Counter
import random

st.set_page_config(page_title="快乐8分析", page_icon="🎱", layout="wide")
st.title("体彩快乐8历史分析")

# 1. 读取数据
@st.cache_data
def load_data():
    try:
        df = pd.read_csv('data/k8.csv')
        return df
    except Exception as e:
        st.error(f"读取数据失败，请确认 data/k8.csv 是否存在！错误：{e}")
        st.stop()

df = load_data()

# 2. 提取每期的20个号码
all_draws = df['numbers'].astype(str).str.split(' ').tolist()
# 展平所有号码，用于统计频率
all_numbers_flat = [int(num) for draw in all_draws for num in draw if num and num.isdigit()]
freq_counter = Counter(all_numbers_flat)

# 3. 展示频率统计
st.header("📊 号码频率统计 (1-80)")
freq_data = [{"号码": i, "出现次数": freq_counter.get(i, 0)} for i in range(1, 81)]
freq_df = pd.DataFrame(freq_data)
st.bar_chart(freq_df.set_index("号码"))

# 4. 展示最新几期数据
st.header("📋 最新开奖数据")
st.dataframe(df.tail(10), use_container_width=True)

# ==========================================
# 5. 智能选号与历史记录（单注生成 + 保存）
# ==========================================
st.markdown("---")
st.header("🎯 智能选号辅助 (仅供娱乐)")
st.caption("注意：彩票开奖是独立随机事件，以下号码仅由历史数据统计生成，不代表预测结果，请理性对待。")

# 初始化 Session State，用于保存历史记录和当前生成的号码
if 'history_records' not in st.session_state:
    st.session_state.history_records = []
if 'current_pick' not in st.session_state:
    st.session_state.current_pick = None

# 用户设置
col1, col2 = st.columns(2)
with col1:
    play_type = st.selectbox("选择玩法：", ["选十 (挑10个号码)", "选二十 (挑20个号码)"])
with col2:
    strategy = st.selectbox("选择选号策略：", ["冷热结合（推荐）", "随机生成（纯机选）"])

# 计算冷热号（用于冷热结合策略）
recent_df = df.tail(30)
recent_numbers = [int(num) for draw in recent_df['numbers'].astype(str).str.split(' ') for num in draw if num.isdigit()]
hot_counter = Counter(recent_numbers)
hot_nums = [num for num, count in hot_counter.most_common(15)]

# 计算遗漏（冷号）
def calc_omission_k8(df):
    last_seen = {i: -1 for i in range(1, 81)}
    for idx, row in df.iterrows():
        nums = [int(n) for n in str(row['numbers']).split(' ') if n.isdigit()]
        for n in nums:
            last_seen[n] = idx
    total = len(df)
    omission = {n: (total if pos == -1 else total - 1 - pos) for n, pos in last_seen.items()}
    return omission

omission_dict = calc_omission_k8(df)
cold_nums = sorted(omission_dict, key=omission_dict.get, reverse=True)[:15]

# 生成单注号码的逻辑
if st.button("生成一注号码"):
    num_count = 10 if "选十" in play_type else 20
    
    if strategy == "冷热结合（推荐）":
        picks = set()
        picks.update(random.sample(hot_nums, min(2, len(hot_nums))))
        picks.update(random.sample(cold_nums, min(2, len(cold_nums))))
        while len(picks) < num_count:
            picks.add(random.randint(1, 80))
        final_picks = sorted(list(picks))
    else:
        final_picks = sorted(random.sample(range(1, 81), num_count))
        
    num_str = " ".join(f"{n:02d}" for n in final_picks)
    
    # 暂存当前生成的号码
    st.session_state.current_pick = {
        "号码": num_str,
        "玩法": play_type,
        "策略": strategy
    }

# 展示当前生成的号码，并提供保存按钮
if st.session_state.current_pick:
    st.success("当前生成的号码如下：")
    st.code(st.session_state.current_pick["号码"], language=None)
    st.caption(f"玩法：{st.session_state.current_pick['玩法']} | 策略：{st.session_state.current_pick['策略']}")
    
    if st.button("💾 保存到历史记录"):
        # 补充一个编号
        record = st.session_state.current_pick.copy()
        record["序号"] = len(st.session_state.history_records) + 1
        st.session_state.history_records.append(record)
        st.session_state.current_pick = None # 保存后清空暂存，防止重复保存
        st.rerun() # 刷新页面，让历史记录立刻显示出来

# 6. 展示历史生成记录
if st.session_state.history_records:
    st.markdown("---")
    st.subheader("📋 历史生成记录")
    
    hist_df = pd.DataFrame(st.session_state.history_records)
    # 调整列顺序，把序号放最前面
    cols = ['序号'] + [c for c in hist_df.columns if c != '序号']
    hist_df = hist_df[cols]
    
    tab1, tab2 = st.tabs(["当前历史列表", "下载/清空"])
    
    with tab1:
        st.dataframe(hist_df, use_container_width=True, hide_index=True)
        
        all_numbers = "\n".join(hist_df['号码'].astype(str).tolist())
        st.markdown("**👇 长按下方文本框，即可一键复制全部历史号码：**")
        st.code(all_numbers, language=None)
        
    with tab2:
        col_a, col_b = st.columns(2)
        with col_a:
            csv_data = hist_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 下载历史记录为 CSV",
                data=csv_data,
                file_name="k8_generated_history.csv",
                mime="text/csv"
            )
        with col_b:
            if st.button("🗑️ 清空历史记录"):
                st.session_state.history_records = []
                st.session_state.current_pick = None
                st.rerun()

st.caption("⚠️ 本工具仅供个人学习与娱乐，不构成任何购彩建议，请理性购彩。")