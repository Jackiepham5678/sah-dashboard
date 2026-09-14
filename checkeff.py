import streamlit as st
import pandas as pd
import pyodbc
from datetime import datetime
import io

st.set_page_config(page_title="SAH Dashboard", layout="wide")

# CSS
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    .metric-box {
        background: #E7E6E6;
        border: 2px solid #A6A6A6;
        border-radius: 5px;
        padding: 12px;
        text-align: center;
        margin: 5px 0;
    }
    
    .compact-productivity-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border: 3px solid #5568d3;
        border-radius: 10px;
        padding: 15px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 15px;
        height: 120px;
    }
    
    .compact-bonus-box {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        border: 3px solid #0d7a6f;
        border-radius: 10px;
        padding: 15px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 120px;
    }
    
    .emoji-icon {
        font-size: 50px;
        animation: bounce 2s infinite;
    }
    
    @keyframes bounce {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-8px); }
    }
    
    /* Custom table styling */
    [data-testid="stDataFrame"] {
        text-align: center !important;
        font-size: 13px !important;
    }
    
    [data-testid="stDataFrame"] td,
    [data-testid="stDataFrame"] th {
        text-align: center !important;
        vertical-align: middle !important;
        font-weight: 500 !important;
    }
    
    [data-testid="stDataFrame"] th {
        font-weight: 600 !important;
    }
</style>
""", unsafe_allow_html=True)

# Fixed credentials
USER = "JACKYPHAM"
PWD = "IE072026"

# =============== DECODE FUNCTION ===============
def decode_ebcdic_columns(df):
    """Decode EBCDIC columns"""
    df_decoded = df.copy()
    
    for col in df_decoded.columns:
        if df_decoded[col].dtype == 'object':
            try:
                df_decoded[col] = df_decoded[col].apply(
                    lambda x: x.strip() if isinstance(x, str) else x
                )
            except:
                pass
    
    return df_decoded

# =============== CALCULATE BONUS FUNCTION ===============
def calculate_bonus(df_result, work_hours):
    """
    Tính thưởng năng suất với giới hạn theo workcenter
    
    Công thức:
    - Nếu năng suất > 40%: Thưởng = (Năng suất capped - 30%) × Thời gian làm việc × 67
    - Nếu năng suất ≤ 40%: Thưởng = 0
    
    Giới hạn:
    - BATE1: Max 170%
    - Còn lại: Max 150%
    """
    total_productivity_for_bonus = 0
    
    for idx, row in df_result.iterrows():
        productivity = row['Năng suất (%)']
        workcenter = str(row['Workcenter']).strip().upper()
        
        # Áp dụng cap theo workcenter
        if workcenter == 'BATE1':
            capped_productivity = min(productivity, 170)
        else:
            capped_productivity = min(productivity, 150)
        
        total_productivity_for_bonus += capped_productivity
    
    # Tính thưởng
    if total_productivity_for_bonus > 40:
        bonus = (total_productivity_for_bonus - 30) * work_hours * 67
        return max(0, bonus)
    else:
        return 0

# Initialize session state
if 'df_table' not in st.session_state:
    st.session_state.df_table = pd.DataFrame({
        'Item': [''] * 10,
        'Số lượng theo item': [0] * 10,
        'Công đoạn': [''] * 10,
        'Workcenter': [''] * 10,
        'Routing (min/kit)': [0.0] * 10,
        'SAH (hour)': [0.0] * 10,
        'Năng suất (%)': [0.0] * 10
    })

if 'calculated' not in st.session_state:
    st.session_state.calculated = False

# =============== SIDEBAR ===============
with st.sidebar:
    st.header("⚙️ Cài Đặt")
    
    work_hours = st.number_input(
        "⏰ Thời gian làm việc (giờ)", 
        min_value=1.0, 
        value=8.0, 
        step=0.5
    )
    
    num_workers = st.number_input(
        "👥 Số người làm việc theo nhóm", 
        min_value=1, 
        value=2, 
        step=1
    )
    
    st.markdown("---")
    st.header("🎯 Thao Tác")
    
    run_btn = st.button(
        "▶️ RUN", 
        type="primary", 
        use_container_width=True,
        help="Lấy Routing và Tính SAH"
    )
    
    clear_btn = st.button(
        "🗑️ CLEAR DATA", 
        use_container_width=True,
        help="Xóa toàn bộ dữ liệu"
    )
    
    st.markdown("---")

# =============== MAIN AREA ===============
st.markdown("## 📊 EFFICIENCY CALCULATION")

# =============== COMPACT DISPLAY (2 COLUMNS) ===============
if st.session_state.calculated:
    df_result = st.session_state.df_table[st.session_state.df_table['Item'].str.strip() != ''].copy()
    
    if len(df_result) > 0:
        total_productivity = df_result['Năng suất (%)'].sum()
        
        # Tính thưởng với công thức mới
        bonus = calculate_bonus(df_result, work_hours)
        
        if total_productivity >= 100:
            emoji = "😊"
            emoji_color = "#00FF00"
            status = "Xuất sắc!"
        else:
            emoji = "😢"
            emoji_color = "#FF0000"
            status = "Cần cải thiện"
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown(f"""
            <div class="compact-productivity-box">
                <div>
                    <div style="font-size:14px;color:white;font-weight:bold;margin-bottom:5px;">📈 NĂNG SUẤT TỔNG</div>
                    <div style="font-size:40px;color:white;font-weight:bold;">{total_productivity:.1f}%</div>
                    <div style="font-size:12px;color:rgba(255,255,255,0.8);margin-top:3px;">{status}</div>
                </div>
                <div class="emoji-icon" style="color:{emoji_color};">
                    {emoji}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            if bonus > 0:
                formula_text = "Tiền về ví (có giới hạn cap)"
            else:
                formula_text = "Năng suất ≤ 40%"
            
            st.markdown(f"""
            <div class="compact-bonus-box">
                <div style="font-size:14px;color:white;font-weight:bold;margin-bottom:5px;">💰 THƯỞNG NĂNG SUẤT</div>
                <div style="font-size:40px;color:white;font-weight:bold;">₫{bonus:,.0f}</div>
                <div style="font-size:11px;color:rgba(255,255,255,0.8);margin-top:3px;">{formula_text}</div>
            </div>
            """, unsafe_allow_html=True)

st.markdown("---")

# =============== EDITABLE EXCEL TABLE ===============
st.markdown("### 📋 Nhập dữ liệu")

edited_df = st.data_editor(
    st.session_state.df_table,
    use_container_width=True,
    num_rows="dynamic",
    height=400,
    column_config={
        "Item": st.column_config.TextColumn(
            "Item", 
            width="medium",
            required=True
        ),
        "Số lượng theo item": st.column_config.NumberColumn(
            "Số lượng theo item", 
            width="medium",
            min_value=0, 
            format="%d"
        ),
        "Công đoạn": st.column_config.TextColumn(
            "Công đoạn", 
            width="small"
        ),
        "Workcenter": st.column_config.TextColumn(
            "Workcenter", 
            width="small"
        ),
        "Routing (min/kit)": st.column_config.NumberColumn(
            "Routing (min/kit)", 
            width="medium",
            format="%.2f", 
            disabled=True
        ),
        "SAH (hour)": st.column_config.NumberColumn(
            "SAH (hour)", 
            width="small",
            format="%.2f", 
            disabled=True
        ),
        "Năng suất (%)": st.column_config.NumberColumn(
            "Năng suất (%)", 
            width="medium",
            format="%.1f", 
            disabled=True
        ),
    },
    hide_index=True,
)

st.session_state.df_table = edited_df

# =============== CLEAR DATA ===============
if clear_btn:
    st.session_state.df_table = pd.DataFrame({
        'Item': [''] * 10,
        'Số lượng theo item': [0] * 10,
        'Công đoạn': [''] * 10,
        'Workcenter': [''] * 10,
        'Routing (min/kit)': [0.0] * 10,
        'SAH (hour)': [0.0] * 10,
        'Năng suất (%)': [0.0] * 10
    })
    st.session_state.calculated = False
    st.success("✅ Đã xóa!")
    st.rerun()

# =============== RUN ===============
if run_btn:
    df_input = edited_df[edited_df['Item'].str.strip() != ''].copy()
    
    if len(df_input) == 0:
        st.error("⚠️ Nhập Item!")
    else:
        with st.spinner("🔄 Đang xử lý..."):
            try:
                connection_string = (
                    "Driver={iSeries Access ODBC Driver};"
                    f"System=MILPROD;"
                    f"DefaultLibraries=JDETSTDTA;"
                    f"Uid={USER};"
                    f"Pwd={PWD};"
                    "ForceTranslation=0;"
                )
                conn = pyodbc.connect(connection_string)
                
                routing_count = 0
                
                for idx, row in df_input.iterrows():
                    item = row['Item'].strip()
                    congdoan = row['Công đoạn'].strip()
                    wc = row['Workcenter'].strip()
                    
                    if not item:
                        continue
                    
                    query = f"""
                    SELECT
                        BRDSTID, 
                        BRDFGITEMNO, 
                        BRDFGITEMCLASS, 
                        BRDROUTINGIDENTIFIER, 
                        BRDOPERATIONSEQUENCE, 
                        BRDPRODUCTIONFACILITYID,  
                        BRDRUNLABORTIMEUSEBYBOMGROSS, 
                        BRDOPERATIONDESCRIPTION, 
                        BRDSETUPCREWSIZE
                    FROM
                        RGNFILL.RTGBOMD
                    WHERE
                        BRDFGITEMNO = '{item}'
                    """
                    
                    if congdoan:
                        query += f" AND BRDOPERATIONSEQUENCE = '{congdoan}'"
                    if wc:
                        query += f" AND BRDPRODUCTIONFACILITYID = '{wc}'"
                    
                    query += " ORDER BY BRDOPERATIONSEQUENCE"
                    
                    df_routing = pd.read_sql(query, conn)
                    
                    if len(df_routing) > 0:
                        df_decoded = decode_ebcdic_columns(df_routing)
                        
                        # Lấy workcenter từ DB nếu chưa nhập
                        if not wc:
                            wc_from_db = df_decoded['BRDPRODUCTIONFACILITYID'].iloc[0]
                            st.session_state.df_table.loc[idx, 'Workcenter'] = wc_from_db
                        
                        routing_raw = df_decoded['BRDRUNLABORTIMEUSEBYBOMGROSS'].iloc[0]
                        routing = (routing_raw / 100) * 60
                        
                        st.session_state.df_table.loc[idx, 'Routing (min/kit)'] = round(routing, 2)
                        
                        qty = row['Số lượng theo item']
                        sah = (routing * qty / 60) if routing > 0 and qty > 0 else 0
                        st.session_state.df_table.loc[idx, 'SAH (hour)'] = round(sah, 2)
                        
                        if work_hours > 0 and num_workers > 0:
                            productivity = (sah / (work_hours * num_workers)) * 100
                            st.session_state.df_table.loc[idx, 'Năng suất (%)'] = round(productivity, 1)
                        else:
                            st.session_state.df_table.loc[idx, 'Năng suất (%)'] = 0.0
                        
                        routing_count += 1
                
                conn.close()
                
                st.session_state.calculated = True
                st.success(f"✅ Xử lý {routing_count} dòng!")
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ {str(e)}")

# =============== DISPLAY RESULTS ===============
if st.session_state.calculated:
    st.markdown("---")
    
    df_result = st.session_state.df_table[st.session_state.df_table['Item'].str.strip() != ''].copy()
    
    if len(df_result) > 0:
        total_qty = df_result['Số lượng theo item'].sum()
        total_sah = df_result['SAH (hour)'].sum()
        avg_routing = df_result['Routing (min/kit)'].mean()
        total_productivity = df_result['Năng suất (%)'].sum()
        
        st.markdown("### 📊 Thông Tin Chi Tiết")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(f'<div class="metric-box"><div style="font-size:12px;color:#333;">Thời gian làm việc (giờ)</div><div style="font-size:28px;font-weight:bold;">{work_hours:.0f}</div></div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown(f'<div class="metric-box"><div style="font-size:12px;color:#333;">Số người làm việc</div><div style="font-size:28px;font-weight:bold;">{num_workers}</div></div>', unsafe_allow_html=True)
        
        with col3:
            st.markdown(f'<div class="metric-box"><div style="font-size:12px;color:#333;">Tổng SAH (hour)</div><div style="font-size:28px;font-weight:bold;color:#0066CC;">{total_sah:.2f}</div></div>', unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("### 📋 Bảng Tổng Hợp")
        
        total_row = pd.DataFrame([{
            'Item': 'Tổng',
            'Số lượng theo item': int(total_qty),
            'Công đoạn': '',
            'Workcenter': '',
            'Routing (min/kit)': round(avg_routing, 2),
            'SAH (hour)': round(total_sah, 2),
            'Năng suất (%)': round(total_productivity, 1)
        }])
        
        df_display = pd.concat([total_row, df_result], ignore_index=True)
        
        # Custom styling với HTML
        def highlight_first_row(row):
            if row.name == 0:
                return ['background-color: #FFD700; font-weight: bold; text-align: center'] * len(row)
            else:
                return ['text-align: center'] * len(row)
        
        styled_df = df_display.style.apply(highlight_first_row, axis=1)
        
        st.dataframe(
            styled_df,
            use_container_width=True, 
            height=400, 
            hide_index=True,
            column_config={
                "Item": st.column_config.TextColumn(width="medium"),
                "Số lượng theo item": st.column_config.NumberColumn(width="medium", format="%d"),
                "Công đoạn": st.column_config.TextColumn(width="small"),
                "Workcenter": st.column_config.TextColumn(width="small"),
                "Routing (min/kit)": st.column_config.NumberColumn(width="medium", format="%.2f"),
                "SAH (hour)": st.column_config.NumberColumn(width="small", format="%.2f"),
                "Năng suất (%)": st.column_config.NumberColumn(width="medium", format="%.1f%%"),
            }
        )
        
        # Hiển thị thông tin cap
        st.info("ℹ️ **Lưu ý tính thưởng:** BATE1 max 170%, các WC khác max 150% (hiển thị % vẫn giữ nguyên)")
        
        st.markdown("### 💾 Xuất Dữ Liệu")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df_display.to_excel(writer, sheet_name='SAH', index=False)
                
                workbook = writer.book
                worksheet = writer.sheets['SAH']
                
                from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
                
                # Header styling
                header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
                header_font = Font(color="FFFFFF", bold=True, size=11)
                
                for cell in worksheet[1]:
                    cell.fill = header_fill
                    cell.font = header_font
                    cell.alignment = Alignment(horizontal='center', vertical='center')
                
                # Total row styling (Yellow)
                total_fill = PatternFill(start_color="FFD700", end_color="FFD700", fill_type="solid")
                total_font = Font(bold=True, size=11)
                
                for cell in worksheet[2]:
                    cell.fill = total_fill
                    cell.font = total_font
                    cell.alignment = Alignment(horizontal='center', vertical='center')
                
                # Border
                thin = Side(border_style="thin", color="D4D4D4")
                border = Border(top=thin, left=thin, right=thin, bottom=thin)
                
                for row in worksheet.iter_rows():
                    for cell in row:
                        cell.border = border
                        cell.alignment = Alignment(horizontal='center', vertical='center')
                
                # Column widths - Nhỏ lại như cũ
                worksheet.column_dimensions['A'].width = 18
                worksheet.column_dimensions['B'].width = 20
                worksheet.column_dimensions['C'].width = 15
                worksheet.column_dimensions['D'].width = 15
                worksheet.column_dimensions['E'].width = 18
                worksheet.column_dimensions['F'].width = 15
                worksheet.column_dimensions['G'].width = 15
            
            st.download_button("📊 Excel", buffer.getvalue(), f"SAH_{datetime.now():%Y%m%d_%H%M}.xlsx", use_container_width=True)
        
        with col2:
            st.download_button("📄 CSV", df_display.to_csv(index=False, encoding='utf-8-sig'), f"SAH_{datetime.now():%Y%m%d_%H%M}.csv", use_container_width=True)
        
        with col3:
            st.download_button("🔗 JSON", df_display.to_json(orient='records', force_ascii=False, indent=2), f"SAH_{datetime.now():%Y%m%d_%H%M}.json", use_container_width=True)
