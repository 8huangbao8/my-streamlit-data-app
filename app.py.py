import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os

st.title('鸡舍数据录入系统')
file_path = r"C:\Users\hb\Desktop\原始数据\chicken.xlsx"

# 在代码开头添加会话状态初始化
if 'weight_age' not in st.session_state:
    st.session_state.weight_age = 1
if 'weight_date' not in st.session_state:
    st.session_state.weight_date = datetime.now().date()
if 'weight_house' not in st.session_state:
    st.session_state.weight_house = 1

# 在代码开头添加日常数据的会话状态初始化
if 'daily_age' not in st.session_state:
    st.session_state.daily_age = 1
if 'daily_date' not in st.session_state:
    st.session_state.daily_date = datetime.now().date()
if 'daily_house' not in st.session_state:
    st.session_state.daily_house = 1

def update_weight_age():
    """更新体重数据的日龄"""
    sheets = load_all_sheets()
    st.session_state.weight_age = calculate_age_for_date(
        st.session_state.weight_house, 
        st.session_state.weight_date, 
        sheets
    )

def recalculate_stock(df, initial_stock=54000):
    """重新计算所有记录的存栏数"""
    if df.empty:
        return df
    
    # 确保按日期排序
    df = df.sort_values('日期').reset_index(drop=True)
    
    # 重新计算存栏数
    for i in range(len(df)):
        if i == 0:
            # 第一条记录：初始存栏 - 死亡 - 淘汰
            df.at[i, '存栏数'] = initial_stock - df.iloc[i]['单日死亡(只)'] - df.iloc[i]['单日淘汰(只)']
        else:
            # 后续记录：上一条存栏 - 当前死亡 - 当前淘汰
            previous_stock = df.iloc[i-1]['存栏数']
            current_death = df.iloc[i]['单日死亡(只)']
            current_eliminate = df.iloc[i]['单日淘汰(只)']
            df.at[i, '存栏数'] = previous_stock - current_death - current_eliminate
    
    return df

def load_all_sheets():
    """加载所有工作表"""
    if os.path.exists(file_path):
        sheets = pd.read_excel(file_path, sheet_name=None)
        # 统一处理所有工作表的日期格式
        for sheet_name, df in sheets.items():
            if not df.empty and '日期' in df.columns:
                # 将日期列统一转换为日期格式（不含时间）
                df['日期'] = pd.to_datetime(df['日期']).dt.date
        return sheets
    return {}

def save_all_sheets(sheets_dict):
    """保存所有工作表"""
    with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
        for sheet_name, df in sheets_dict.items():
            # 保存前确保日期格式正确
            if not df.empty and '日期' in df.columns:
                df_copy = df.copy()
                # 确保日期列是datetime类型以便Excel保存
                df_copy['日期'] = pd.to_datetime(df_copy['日期'])
                df_copy.to_excel(writer, sheet_name=sheet_name, index=False)
            else:
                df.to_excel(writer, sheet_name=sheet_name, index=False)

def get_recent_data(sheets, house_num, days=14):
    """获取最近指定天数的数据"""
    sheet_name = str(house_num)
    if sheet_name not in sheets:
        return pd.DataFrame()
    
    df = sheets[sheet_name]
    if df.empty:
        return df
    
    # 确保日期列是datetime类型进行比较
    df_temp = df.copy()
    df_temp['日期_dt'] = pd.to_datetime(df_temp['日期'])
    
    # 获取最近两周的数据
    cutoff_date = datetime.now() - timedelta(days=days)
    recent_data = df_temp[df_temp['日期_dt'] >= pd.to_datetime(cutoff_date)]
    
    # 返回原始数据（不含临时列）
    return df.loc[recent_data.index].sort_values('日期', ascending=False)

def calculate_age(house_num, current_date, sheets):
    """根据鸡舍历史数据计算当前日龄"""
    sheet_name = str(house_num)
    if sheet_name not in sheets:
        return 1  # 如果没有历史数据，默认从第1天开始
    
    df = sheets[sheet_name]
    if df.empty:
        return 1  # 如果没有历史数据，默认从第1天开始
    
    # 确保日期列是datetime类型进行比较
    df_temp = df.copy()
    df_temp['日期_dt'] = pd.to_datetime(df_temp['日期'])
    
    # 获取最近一条记录
    latest_record = df_temp.sort_values('日期_dt', ascending=False).iloc[0]
    latest_date = latest_record['日期']
    latest_age = latest_record['日龄']
    
    # 计算日期差
    days_diff = (pd.to_datetime(current_date) - pd.to_datetime(latest_date)).days
    
    if days_diff < 0:
        st.warning("选择的日期早于最后记录日期，请检查日期输入")
        return latest_age
    
    # 新日龄 = 最后记录日龄 + 日期差
    new_age = latest_age + days_diff
    
    return new_age

def check_duplicate_daily_record(sheets, house_num, date):
    """检查日常数据是否存在重复记录"""
    sheet_name = str(house_num)
    if sheet_name in sheets and not sheets[sheet_name].empty:
        df = sheets[sheet_name]
        input_date = pd.to_datetime(date).date()
        
        # 检查是否有相同日期的记录
        duplicate_records = df[df['日期'] == input_date]
        if not duplicate_records.empty:
            return True, duplicate_records
    return False, None

def delete_record(sheets, sheet_name, record_index):
    """删除指定记录"""
    if sheet_name in sheets:
        df = sheets[sheet_name]
        if not df.empty and 0 <= record_index < len(df):
            # 删除记录
            deleted_record = df.iloc[record_index].copy()
            df = df.drop(df.index[record_index]).reset_index(drop=True)
            sheets[sheet_name] = df
            save_all_sheets(sheets)
            return True, deleted_record
    return False, None

def update_record(sheets, sheet_name, record_index, updated_data):
    """更新指定记录"""
    if sheet_name in sheets:
        df = sheets[sheet_name]
        if not df.empty and 0 <= record_index < len(df):
            # 更新记录
            for column, value in updated_data.items():
                df.at[df.index[record_index], column] = value
            sheets[sheet_name] = df
            save_all_sheets(sheets)
            return True
    return False

tab1, tab2, tab3, tab4 = st.tabs(["日常数据", "体重数据", "采购饲料", "数据维护"])

def calculate_age_for_date(house_num, target_date, sheets):
    """根据鸡舍历史数据计算指定日期的准确日龄"""
    sheet_name = str(house_num)
    
    # 如果没有该鸡舍的数据，从第1天开始
    if sheet_name not in sheets or sheets[sheet_name].empty:
        return 1
    
    df = sheets[sheet_name]
    
    # 确保日期列是datetime类型进行比较
    df_temp = df.copy()
    df_temp['日期_dt'] = pd.to_datetime(df_temp['日期'])
    target_date_dt = pd.to_datetime(target_date)
    
    # 按日期排序
    df_temp = df_temp.sort_values('日期_dt')
    
    # 情况1：如果目标日期早于所有记录，需要推算
    if target_date_dt < df_temp['日期_dt'].min():
        first_record = df_temp.iloc[0]
        first_date = first_record['日期']
        first_age = first_record['日龄']
        
        # 计算日期差（目标日期比第一条记录早多少天）
        days_diff = (pd.to_datetime(first_date) - target_date_dt).days
        
        # 日龄 = 第一条记录的日龄 - 日期差
        calculated_age = first_age - days_diff
        
        # 日龄不能小于1
        return max(1, calculated_age)
    
    # 情况2：如果目标日期晚于所有记录，基于最后一条记录推算
    elif target_date_dt > df_temp['日期_dt'].max():
        last_record = df_temp.iloc[-1]
        last_date = last_record['日期']
        last_age = last_record['日龄']
        
        # 计算日期差
        days_diff = (target_date_dt - pd.to_datetime(last_date)).days
        
        # 日龄 = 最后记录的日龄 + 日期差
        return last_age + days_diff
    
    # 情况3：如果目标日期在已有记录范围内，找到最接近的记录
    else:
        # 找到目标日期之前最近的记录
        previous_records = df_temp[df_temp['日期_dt'] <= target_date_dt]
        if not previous_records.empty:
            closest_record = previous_records.iloc[-1]  # 最后一条，即最接近的记录
            closest_date = closest_record['日期']
            closest_age = closest_record['日龄']
            
            # 计算日期差
            days_diff = (target_date_dt - pd.to_datetime(closest_date)).days
            
            # 日龄 = 最近记录的日龄 + 日期差
            return closest_age + days_diff
        else:
            return 1

def get_initial_stock(house_num, sheets):
    """获取鸡舍的初始存栏数"""
    sheet_name = str(house_num)
    if sheet_name in sheets and not sheets[sheet_name].empty:
        df = sheets[sheet_name]
        # 返回最早记录的存栏数 + 死亡 + 淘汰（推算初始值）
        first_record = df.sort_values('日期').iloc[0]
        return first_record['存栏数'] + first_record['单日死亡(只)'] + first_record['单日淘汰(只)']
    return 54000  # 默认初始存栏

def get_record_description(record, data_type):
    """根据数据类型获取记录描述"""
    try:
        if data_type == "日常数据":
            date_str = record['日期'].strftime('%Y-%m-%d') if hasattr(record['日期'], 'strftime') else str(record['日期'])
            return f"耗料:{record.get('单日耗料(kg)', 'N/A')}kg 死亡:{record.get('单日死亡(只)', 'N/A')}只"
        elif data_type in ["体重数据", "称重数据"]:
            date_str = record['日期'].strftime('%Y-%m-%d') if hasattr(record['日期'], 'strftime') else str(record['日期'])
            return f"鸡笼:{record.get('鸡笼编号', 'N/A')} {record.get('层数', 'N/A')} 均重:{record.get('均重(g)', 'N/A')}g"
        elif data_type == "采购记录":
            date_str = record['日期'].strftime('%Y-%m-%d') if hasattr(record['日期'], 'strftime') else str(record['日期'])
            return f"采购:{record.get('采购饲料(kg)', 'N/A')}kg {record.get('料号', 'N/A')}"
        return ""
    except Exception as e:
        return f"数据格式异常: {str(e)}"

# 修改后的日常数据标签页
with tab1:
    st.subheader("日常数据录入")
    
    # 使用columns而不是form来实现实时更新
    col1, col2 = st.columns(2)
    with col1:
        date = st.date_input("日期", st.session_state.daily_date, key="daily_date_input")
        house_num = st.selectbox("鸡舍编号", range(1,17), index=st.session_state.daily_house-1, key="daily_house_select")
    
    with col2:
        feed = st.number_input("单日耗料(kg)", 0.0, 20000.0, 0.0, key="feed_input")
        death = st.number_input("单日死亡(只)", 0, 1000, 0, key="death_input")
        eliminate = st.number_input("单日淘汰(只)", 0, 1000, 0, key="eliminate_input")
    
    # 实时更新日龄
    st.session_state.daily_date = date
    st.session_state.daily_house = house_num
    sheets = load_all_sheets()
    st.session_state.daily_age = calculate_age_for_date(house_num, date, sheets)
    
    # 实时显示日龄信息
    st.info(f"**自动计算日龄：{st.session_state.daily_age} 天**")
    
    # 显示日龄计算说明
    with st.expander("日龄计算说明"):
        st.markdown(f"""
        **当前日期**: {date}
        **计算出的日龄**: {st.session_state.daily_age}天
        
        **计算逻辑**:
        - 系统会根据鸡舍{house_num}的历史数据自动推算
        - 如果录入历史日期，日龄会自动向前推算
        - 如果录入未来日期，日龄会自动向后推算
        - 确保整个时间线的日龄连续性
        """)
    
    # 检查重复记录
    is_duplicate, duplicate_data = check_duplicate_daily_record(sheets, house_num, date)
    if is_duplicate:
        st.error(f"警告：鸡舍{house_num}在{date}已有数据记录！")
        st.write("已存在的记录：")
        duplicate_display = duplicate_data.copy()
        st.dataframe(duplicate_display, use_container_width=True)
        st.warning("请检查日期是否正确，或前往'数据维护'页面修改现有记录")
    
    # 提交按钮
    if st.button("提交日常数据", type="primary"):
        # 再次检查重复记录
        is_duplicate, duplicate_data = check_duplicate_daily_record(sheets, house_num, date)
        if is_duplicate:
            st.error("无法提交：存在重复记录！请修改日期或前往数据维护页面删除重复记录")
        else:
            try:
                sheet_name = str(house_num)
                
                if sheet_name in sheets:
                    df = sheets[sheet_name]
                else:
                    df = pd.DataFrame(columns=["日期","鸡舍编号","日龄","单日耗料(kg)","单日死亡(只)","单日淘汰(只)","存栏数"])
                
                # 使用实时计算的日龄
                final_age = st.session_state.daily_age
                
                # 创建新行数据 - 直接使用date对象
                new_row = pd.DataFrame([{
                    "日期": date,  # 直接使用date对象，不含时间
                    "鸡舍编号": house_num,
                    "日龄": final_age,
                    "单日耗料(kg)": feed,
                    "单日死亡(只)": death,
                    "单日淘汰(只)": eliminate,
                    "存栏数": 0  # 先设为0，后面统一计算
                }])
                
                # 将新数据添加到DataFrame
                df = pd.concat([df, new_row], ignore_index=True)
                
                # 确保日期列是datetime类型以便排序
                df['日期'] = pd.to_datetime(df['日期'])
                
                # 按日期（日龄）从小到大排序
                df = df.sort_values('日期').reset_index(drop=True)
                
                # 重新计算所有记录的存栏数
                initial_stock = get_initial_stock(house_num, sheets)
                df = recalculate_stock(df, initial_stock)
                
                # 保存排序后的数据
                sheets[sheet_name] = df
                save_all_sheets(sheets)
                st.success("日常数据保存成功！数据已按日期排序。")
                
                # 显示数据变化信息
                st.info(f"数据更新说明：")
                st.markdown(f"""
                - **新增记录**: {date}，日龄{final_age}天
                - **重新计算**: 所有记录的存栏数已更新
                - **时间顺序**: 数据已按日期重新排序
                - **初始存栏**: 推算为{initial_stock}只
                """)
                
                # 显示最近数据
                st.subheader(f"鸡舍{house_num}最近数据")
                recent_data = get_recent_data(sheets, house_num, days=30)  # 显示30天数据
                if not recent_data.empty:
                    # 格式化日期显示 - 确保只显示年月日
                    recent_data_display = recent_data.copy()
                    recent_data_display['日期'] = recent_data_display['日期'].apply(
                        lambda x: x.strftime('%Y-%m-%d') if isinstance(x, (datetime, pd.Timestamp)) else str(x)
                    )
                    st.dataframe(recent_data_display, use_container_width=True)
                    
                    # 显示统计信息
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("平均日耗料", f"{recent_data['单日耗料(kg)'].mean():.1f}kg")
                    with col2:
                        st.metric("总死亡数", int(recent_data['单日死亡(只)'].sum()))
                    with col3:
                        st.metric("总淘汰数", int(recent_data['单日淘汰(只)'].sum()))
                    with col4:
                        current_stock = df.iloc[-1]["存栏数"] if not df.empty else 0
                        st.metric("当前存栏", int(current_stock))
                else:
                    st.info("暂无历史数据")
                    
            except Exception as e:
                st.error(f"保存失败: {e}")

with tab2:
    st.subheader("体重数据录入")
    
    # 使用columns而不是form来实现实时更新
    col1, col2 = st.columns(2)
    with col1:
        date = st.date_input("称重日期", st.session_state.weight_date, key="weight_date_input")
        house_num = st.selectbox("称重鸡舍", range(1,17), index=st.session_state.weight_house-1, key="weight_house_select")
        cage_num = st.number_input("鸡笼编号", 1, 100, 15, key="cage_num")
    
    # 实时更新日龄
    st.session_state.weight_date = date
    st.session_state.weight_house = house_num
    sheets = load_all_sheets()
    st.session_state.weight_age = calculate_age_for_date(house_num, date, sheets)
    
    with col2:
        # 实时显示日龄
        st.info(f"**自动计算日龄：{st.session_state.weight_age} 天**")
        
        # 显示日龄计算详情
        with st.expander("日龄计算详情"):
            st.markdown(f"""
            **称重日期**: {date}
            **鸡舍编号**: {house_num}
            **计算日龄**: {st.session_state.weight_age}天
            
            **计算依据**:
            - 系统根据鸡舍{house_num}的日常数据记录自动推算
            - 确保日龄与日常数据的时间线一致
            - 支持历史日期和未来日期的准确计算
            """)
    
    st.subheader("四层体重数据")
    col3, col4 = st.columns(2)
    with col3:
        layer1_count = st.number_input("1层样本数量", 1, 100, 23, key="l1")
        layer1_weight = st.number_input("1层总重量(kg)", 0.0, 50.0, 4.0, key="w1")
        layer3_count = st.number_input("3层样本数量", 1, 100, 23, key="l3")
        layer3_weight = st.number_input("3层总重量(kg)", 0.0, 50.0, 4.0, key="w3")
    with col4:
        layer2_count = st.number_input("2层样本数量", 1, 100, 23, key="l2")
        layer2_weight = st.number_input("2层总重量(kg)", 0.0, 50.0, 4.0, key="w2")
        layer4_count = st.number_input("4层样本数量", 1, 100, 23, key="l4")
        layer4_weight = st.number_input("4层总重量(kg)", 0.0, 50.0, 4.0, key="w4")
    
    # 实时显示体重统计信息
    st.subheader("📊 实时统计信息")
    stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)
    
    with stat_col1:
        total_samples = layer1_count + layer2_count + layer3_count + layer4_count
        st.metric("总样本数", total_samples)
    
    with stat_col2:
        total_weight = layer1_weight + layer2_weight + layer3_weight + layer4_weight
        st.metric("总重量(kg)", f"{total_weight:.2f}")
    
    with stat_col3:
        if total_samples > 0:
            avg_weight_kg = total_weight / total_samples
            avg_weight_g = avg_weight_kg * 1000
            st.metric("平均重量", f"{avg_weight_g:.1f}g")
        else:
            st.metric("平均重量", "0g")
    
    with stat_col4:
        st.metric("计算日龄", f"{st.session_state.weight_age}天")
    
    # 提交按钮
    if st.button("提交四层体重数据", type="primary"):
        try:
            sheets = load_all_sheets()
            sheet_name = "称重数据"
            
            # 使用实时计算的日龄
            final_age_weight = st.session_state.weight_age
            
            if sheet_name in sheets:
                df = sheets[sheet_name]
            else:
                df = pd.DataFrame(columns=["日期","鸡舍编号","鸡笼编号","层数","样本数量","总重量(kg)","均重(g)","日龄"])
            
            new_rows = []
            layers_data = [
                ("1层", layer1_count, layer1_weight),
                ("2层", layer2_count, layer2_weight),
                ("3层", layer3_count, layer3_weight),
                ("4层", layer4_count, layer4_weight)
            ]
            
            for layer, count, weight in layers_data:
                if count > 0:  # 只保存有样本的数据
                    avg_weight = (weight / count * 1000) if count > 0 else 0
                    new_rows.append({
                        "日期": date,  # 直接使用date对象，不含时间
                        "鸡舍编号": house_num,
                        "鸡笼编号": cage_num,
                        "层数": layer,
                        "样本数量": count,
                        "总重量(kg)": weight,
                        "均重(g)": round(avg_weight, 1),
                        "日龄": final_age_weight
                    })
            
            if new_rows:
                df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
                
                # 确保日期列是datetime类型以便排序
                df['日期'] = pd.to_datetime(df['日期'])
                
                # 按日期排序
                df = df.sort_values('日期').reset_index(drop=True)
                
                sheets[sheet_name] = df
                save_all_sheets(sheets)
                
                st.success("✅ 四层体重数据保存成功！")
                
                # 显示保存确认信息
                st.info(f"**保存详情**: {date} 鸡舍{house_num} 日龄{final_age_weight}天")
                
            else:
                st.warning("⚠️ 没有有效的体重数据可保存，请至少输入一层的样本数据")
            
        except Exception as e:
            st.error(f"保存失败: {e}")

with tab3:
    with st.form("purchase_form"):
        date = st.date_input("采购日期", datetime.now(), key="purchase_date")
        house_num = st.selectbox("采购鸡舍", range(1,17), key="purchase_house")
        feed_amount = st.number_input("采购饲料(kg)", 0, 50000, 0)
        feed_type = st.selectbox("料号", ["510", "510DC", "511", "513"])
        
        submitted = st.form_submit_button("提交采购记录")
        
        if submitted:
            try:
                sheets = load_all_sheets()
                sheet_name = "采购饲料记录"
                
                if sheet_name in sheets:
                    df = sheets[sheet_name]
                else:
                    df = pd.DataFrame(columns=["日期", "鸡舍编号", "采购饲料(kg)", "料号"])
                
                new_row = pd.DataFrame([{
                    "日期": date,  # 直接使用date对象，不含时间
                    "鸡舍编号": house_num,
                    "采购饲料(kg)": feed_amount,
                    "料号": feed_type
                }])
                
                df = pd.concat([df, new_row], ignore_index=True)
                sheets[sheet_name] = df
                save_all_sheets(sheets)
                st.success(f"采购记录保存成功！鸡舍{house_num}采购{feed_amount}kg {feed_type}饲料")
                
                # 显示最近采购记录
                st.subheader(f"鸡舍{house_num}最近采购记录")
                if sheet_name in sheets:
                    purchase_df = sheets[sheet_name]
                    # 确保日期列是datetime类型进行比较
                    purchase_df_temp = purchase_df.copy()
                    purchase_df_temp['日期_dt'] = pd.to_datetime(purchase_df_temp['日期'])
                    
                    recent_purchase_data = purchase_df_temp[
                        (purchase_df_temp['鸡舍编号'] == house_num) & 
                        (purchase_df_temp['日期_dt'] >= (datetime.now() - timedelta(days=14)))
                    ].sort_values('日期_dt', ascending=False)
                    
                    if not recent_purchase_data.empty:
                        # 格式化显示 - 只显示年月日
                        recent_purchase_display = purchase_df.loc[recent_purchase_data.index].copy()
                        recent_purchase_display['日期'] = recent_purchase_display['日期'].apply(
                            lambda x: x.strftime('%Y-%m-%d') if isinstance(x, (datetime, pd.Timestamp)) else str(x)
                        )
                        st.dataframe(recent_purchase_display, use_container_width=True)
                        
                        # 显示采购统计
                        total_purchased = recent_purchase_data['采购饲料(kg)'].sum()
                        st.metric("近两周采购总量", f"{total_purchased}kg")
                    else:
                        st.info("暂无近期采购记录")
                
            except Exception as e:
                st.error(f"保存失败: {e}")

# 修复后的数据维护标签页
with tab4:
    st.subheader("📊 数据维护中心")
    
    # 选择数据类型
    data_type = st.selectbox(
        "选择数据类型",
        ["日常数据", "体重数据", "采购记录"],
        key="data_type_select"
    )
    
    sheets = load_all_sheets()
    
    if data_type == "日常数据":
        sheet_names = [str(i) for i in range(1, 17)]
        sheet_display_names = [f"鸡舍{i}" for i in range(1, 17)]
    elif data_type == "体重数据":
        sheet_names = ["称重数据"]
        sheet_display_names = ["称重数据"]
    elif data_type == "采购记录":
        sheet_names = ["采购饲料记录"]
        sheet_display_names = ["采购饲料记录"]
    
    if sheet_names:
        selected_sheet = st.selectbox(
            "选择数据表",
            sheet_names,
            format_func=lambda x: sheet_display_names[sheet_names.index(x)],
            key="sheet_select"
        )
        
        if selected_sheet in sheets and not sheets[selected_sheet].empty:
            df = sheets[selected_sheet]
            
            # 确保日期列只显示年月日
            df_display = df.copy()
            if '日期' in df_display.columns:
                df_display['日期'] = df_display['日期'].apply(
                    lambda x: x.strftime('%Y-%m-%d') if hasattr(x, 'strftime') else str(x)
                )
            
            st.subheader(f"{sheet_display_names[sheet_names.index(selected_sheet)]} 数据记录")
            
            # 显示数据表格
            st.dataframe(df_display, use_container_width=True)
            
            # 记录操作区域
            st.markdown("---")
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("🗑️ 删除记录")
                if len(df) > 0:
                    # 创建选项列表
                    options = list(range(len(df)))
                    option_labels = []
                    for i in options:
                        try:
                            record = df_display.iloc[i]
                            date_str = record['日期'] if '日期' in record else '未知日期'
                            description = get_record_description(record, data_type)
                            option_labels.append(f"记录{i+1}: {date_str} - {description}")
                        except Exception as e:
                            option_labels.append(f"记录{i+1}: 数据异常")
                    
                    record_to_delete = st.selectbox(
                        "选择要删除的记录",
                        options,
                        key="delete_record_select",
                        format_func=lambda x: option_labels[x]
                    )
                    
                    if st.button("删除选中记录", type="secondary", key="delete_btn"):
                        success, deleted_record = delete_record(sheets, selected_sheet, record_to_delete)
                        if success:
                            deleted_date = deleted_record['日期'].strftime('%Y-%m-%d') if hasattr(deleted_record['日期'], 'strftime') else str(deleted_record['日期'])
                            st.success(f"✅ 记录删除成功！删除的记录：{deleted_date}")
                            st.rerun()
                        else:
                            st.error("❌ 删除失败")
            
            with col2:
                st.subheader("✏️ 修改记录")
                if len(df) > 0:
                    # 创建选项列表
                    options = list(range(len(df)))
                    option_labels = []
                    for i in options:
                        try:
                            record = df_display.iloc[i]
                            date_str = record['日期'] if '日期' in record else '未知日期'
                            description = get_record_description(record, data_type)
                            option_labels.append(f"记录{i+1}: {date_str} - {description}")
                        except Exception as e:
                            option_labels.append(f"记录{i+1}: 数据异常")
                    
                    record_to_edit = st.selectbox(
                        "选择要修改的记录",
                        options,
                        key="edit_record_select",
                        format_func=lambda x: option_labels[x]
                    )
                    
                    if st.button("修改选中记录", type="primary", key="edit_btn"):
                        st.session_state.editing_record = record_to_edit
                        st.session_state.editing_sheet = selected_sheet
                        st.session_state.editing_data_type = data_type
                        st.rerun()
            
            # 修改记录表单
            if 'editing_record' in st.session_state and st.session_state.editing_sheet == selected_sheet:
                st.markdown("---")
                st.subheader("📝 修改记录详情")
                
                record_index = st.session_state.editing_record
                selected_record = df.iloc[record_index]
                
                with st.form("edit_record_form"):
                    st.write(f"**正在修改：** {df_display.iloc[record_index]['日期']} 的记录")
                    
                    # 根据数据类型显示不同的编辑字段
                    if data_type == "日常数据":
                        col1, col2 = st.columns(2)
                        with col1:
                            # 日期显示为字符串，不可编辑
                            display_date = selected_record['日期'].strftime('%Y-%m-%d') if hasattr(selected_record['日期'], 'strftime') else str(selected_record['日期'])
                            st.text_input("日期", value=display_date, disabled=True)
                            house_edit = st.number_input("鸡舍编号", value=int(selected_record['鸡舍编号']), min_value=1, max_value=16, disabled=True)
                            age_edit = st.number_input("日龄", value=int(selected_record['日龄']), min_value=1, max_value=100)
                        
                        with col2:
                            feed_edit = st.number_input("单日耗料(kg)", value=float(selected_record['单日耗料(kg)']), min_value=0.0, max_value=10000.0)
                            death_edit = st.number_input("单日死亡(只)", value=int(selected_record['单日死亡(只)']), min_value=0, max_value=1000)
                            eliminate_edit = st.number_input("单日淘汰(只)", value=int(selected_record['单日淘汰(只)']), min_value=0, max_value=1000)
                        
                        if st.form_submit_button("保存修改"):
                            updated_data = {
                                '日龄': age_edit,
                                '单日耗料(kg)': feed_edit,
                                '单日死亡(只)': death_edit,
                                '单日淘汰(只)': eliminate_edit
                            }
                            
                    elif data_type == "体重数据":
                        col1, col2 = st.columns(2)
                        with col1:
                            display_date = selected_record['日期'].strftime('%Y-%m-%d') if hasattr(selected_record['日期'], 'strftime') else str(selected_record['日期'])
                            st.text_input("日期", value=display_date, disabled=True)
                            house_edit = st.number_input("鸡舍编号", value=int(selected_record['鸡舍编号']), min_value=1, max_value=16, disabled=True)
                            cage_edit = st.number_input("鸡笼编号", value=int(selected_record['鸡笼编号']), min_value=1, max_value=100)
                            age_edit = st.number_input("日龄", value=int(selected_record['日龄']), min_value=1, max_value=100)
                        
                        with col2:
                            layer_edit = st.selectbox("层数", ["1层", "2层", "3层", "4层"], 
                                                    index=["1层", "2层", "3层", "4层"].index(selected_record['层数']) if selected_record['层数'] in ["1层", "2层", "3层", "4层"] else 0)
                            count_edit = st.number_input("样本数量", value=int(selected_record['样本数量']), min_value=1, max_value=100)
                            weight_edit = st.number_input("总重量(kg)", value=float(selected_record['总重量(kg)']), min_value=0.0, max_value=50.0)
                            avg_weight_edit = st.number_input("均重(g)", value=float(selected_record['均重(g)']), min_value=0.0, max_value=5000.0)
                        
                        if st.form_submit_button("保存修改"):
                            updated_data = {
                                '鸡笼编号': cage_edit,
                                '层数': layer_edit,
                                '样本数量': count_edit,
                                '总重量(kg)': weight_edit,
                                '均重(g)': avg_weight_edit,
                                '日龄': age_edit
                            }
                            
                    elif data_type == "采购记录":
                        col1, col2 = st.columns(2)
                        with col1:
                            display_date = selected_record['日期'].strftime('%Y-%m-%d') if hasattr(selected_record['日期'], 'strftime') else str(selected_record['日期'])
                            st.text_input("日期", value=display_date, disabled=True)
                            house_edit = st.number_input("鸡舍编号", value=int(selected_record['鸡舍编号']), min_value=1, max_value=16, disabled=True)
                        
                        with col2:
                            feed_amount_edit = st.number_input("采购饲料(kg)", value=int(selected_record['采购饲料(kg)']), min_value=0, max_value=50000)
                            feed_type_edit = st.selectbox("料号", ["510", "510DC", "511", "513"], 
                                                         index=["510", "510DC", "511", "513"].index(selected_record['料号']) if selected_record['料号'] in ["510", "510DC", "511", "513"] else 0)
                        
                        if st.form_submit_button("保存修改"):
                            updated_data = {
                                '采购饲料(kg)': feed_amount_edit,
                                '料号': feed_type_edit
                            }
                    
                    # 保存修改
                    if 'updated_data' in locals():
                        success = update_record(sheets, selected_sheet, record_index, updated_data)
                        if success:
                            st.success("✅ 记录修改成功！")
                            # 如果是日常数据，重新计算存栏数
                            if data_type == "日常数据":
                                house_num = int(selected_record['鸡舍编号'])
                                sheet_name = str(house_num)
                                if sheet_name in sheets:
                                    df_house = sheets[sheet_name]
                                    initial_stock = get_initial_stock(house_num, sheets)
                                    df_house = recalculate_stock(df_house, initial_stock)
                                    sheets[sheet_name] = df_house
                                    save_all_sheets(sheets)
                                    st.info("🔄 存栏数已重新计算")
                            
                            # 清除编辑状态
                            if 'editing_record' in st.session_state:
                                del st.session_state.editing_record
                                del st.session_state.editing_sheet
                                del st.session_state.editing_data_type
                            st.rerun()
                        else:
                            st.error("❌ 修改失败")
                    
                    # 取消修改按钮
                    if st.form_submit_button("取消修改"):
                        if 'editing_record' in st.session_state:
                            del st.session_state.editing_record
                            del st.session_state.editing_sheet
                            del st.session_state.editing_data_type
                        st.rerun()
        
        else:
            st.info(f"📭 {sheet_display_names[sheet_names.index(selected_sheet)]} 暂无数据记录")

# 独立的数据查看功能
st.markdown("---")
st.subheader("🔍 数据查看")

view_col1, view_col2 = st.columns(2)
with view_col1:
    view_house = st.selectbox("选择鸡舍查看数据", range(1,17), key="view_house")
with view_col2:
    view_days = st.selectbox("查看天数", [7, 14, 30, 60], index=1, key="view_days")

if st.button("查看数据", key="view_data_btn"):
    sheets = load_all_sheets()
    recent_data = get_recent_data(sheets, view_house, view_days)
    
    if not recent_data.empty:
        st.subheader(f"鸡舍{view_house}最近{view_days}天数据")
        recent_data_display = recent_data.copy()
        # 确保日期只显示年月日
        recent_data_display['日期'] = recent_data_display['日期'].apply(
            lambda x: x.strftime('%Y-%m-%d') if hasattr(x, 'strftime') else str(x)
        )
        st.dataframe(recent_data_display, use_container_width=True)
    else:
        st.info(f"📭 鸡舍{view_house}暂无最近{view_days}天的数据")