import streamlit as st
import pandas as pd
import datetime
import plotly.express as px

# ---------------------------------------------------------
# PAGE CONFIGURATION & STYLING
# ---------------------------------------------------------
st.set_page_config(
    page_title="Hệ thống Quản lý Khách sạn (HMS)",
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# INITIALIZE SESSION STATE (DATABASE SIMULATION)
# ---------------------------------------------------------
if 'rooms' not in st.state_session_state if hasattr(st, 'state_session_state') else st.session_state:
    st.session_state.rooms = [
        {"room_no": "101", "type": "Standard Single", "price": 500000, "status": "Trống", "guest_name": "", "check_in": None, "services": 0},
        {"room_no": "102", "type": "Standard Single", "price": 500000, "status": "Trống", "guest_name": "", "check_in": None, "services": 0},
        {"room_no": "201", "type": "Deluxe Double", "price": 900000, "status": "Đang ở", "guest_name": "Nguyễn Văn A", "check_in": "2026-09-27", "services": 150000},
        {"room_no": "202", "type": "Deluxe Double", "price": 900000, "status": "Trống", "guest_name": "", "check_in": None, "services": 0},
        {"room_no": "301", "type": "VIP Suite", "price": 1800000, "status": "Đang dọn dẹp", "guest_name": "", "check_in": None, "services": 0},
        {"room_no": "302", "type": "VIP Suite", "price": 1800000, "status": "Đang ở", "guest_name": "Trần Thị B", "check_in": "2026-09-28", "services": 300000},
    ]

if 'history' not in st.session_state:
    st.session_state.history = [
        {"room_no": "101", "guest_name": "Lê Văn C", "total_amount": 750000, "checkout_date": "2026-09-26"},
        {"room_no": "201", "guest_name": "Phạm Văn D", "total_amount": 1100000, "checkout_date": "2026-09-27"}
    ]

# ---------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------
def get_room_df():
    return pd.DataFrame(st.session_state.rooms)

def update_room_status(room_no, new_status, guest_name="", check_in=None, services=0):
    for room in st.session_state.rooms:
        if room['room_no'] == room_no:
            room['status'] = new_status
            room['guest_name'] = guest_name
            room['check_in'] = check_in
            room['services'] = services

# ---------------------------------------------------------
# SIDEBAR NAVIGATION
# ---------------------------------------------------------
st.sidebar.title("🏨 HMS Manager")
st.sidebar.caption("Hệ thống Quản trị Khách sạn Vận hành")

menu = st.sidebar.radio(
    "Danh mục quản lý",
    ["Sơ đồ phòng (Live Grid)", "Check-in / Đặt phòng", "Dịch vụ & Check-out", "Báo cáo Doanh thu & KPIs"]
)

st.sidebar.divider()
st.sidebar.info("💡 **Mẹo Quản lý:** Hãy cập nhật trạng thái phòng ngay khi bộ phận buồng phòng (Housekeeping) hoàn tất dọn dẹp.")

# ---------------------------------------------------------
# 1. LIVE ROOM GRID
# ---------------------------------------------------------
if menu == "Sơ đồ phòng (Live Grid)":
    st.title("📌 Sơ đồ trạng thái phòng thời gian thực")
    
    df_rooms = get_room_df()
    
    # KPI Quick view
    total_rooms = len(df_rooms)
    occupied = len(df_rooms[df_rooms['status'] == 'Đang ở'])
    available = len(df_rooms[df_rooms['status'] == 'Trống'])
    dirty = len(df_rooms[df_rooms['status'] == 'Đang dọn dẹp'])
    occ_rate = round((occupied / total_rooms) * 100, 1)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Tổng số phòng", total_rooms)
    c2.metric("Đang có khách", occupied)
    c3.metric("Sẵn sàng đón khách", available)
    c4.metric("Đang dọn dẹp", dirty)
    c5.metric("Tỷ lệ lấp đầy", f"{occ_rate}%")

    st.divider()

    # Filters
    filter_status = st.selectbox("Lọc theo trạng thái:", ["Tất cả", "Trống", "Đang ở", "Đang dọn dẹp"])
    filtered_df = df_rooms if filter_status == "Tất cả" else df_rooms[df_rooms['status'] == filter_status]

    # Grid Display
    cols = st.columns(3)
    status_colors = {
        "Trống": "#28a745",
        "Đang ở": "#dc3545",
        "Đang dọn dẹp": "#ffc107"
    }

    for idx, room in filtered_df.iterrows():
        col = cols[idx % 3]
        color = status_colors.get(room['status'], '#6c757d')
        
        with col:
            st.markdown(f"""
            <div style="border-left: 6px solid {color}; padding: 12px; background-color: #ffffff; border-radius: 6px; margin-bottom: 15px; border: 1px solid #e0e0e0;">
                <h3 style="margin: 0; color: #333;">Phòng {room['room_no']} - <span style="font-size: 16px; color: {color};">{room['status']}</span></h3>
                <p style="margin: 5px 0;"><b>Loại:</b> {room['type']}</p>
                <p style="margin: 5px 0;"><b>Giá phòng:</b> {room['price']:,} VNĐ/đêm</p>
                <p style="margin: 5px 0;"><b>Khách hàng:</b> {room['guest_name'] if room['guest_name'] else '---'}</p>
            </div>
            """, unsafe_allow_html=True)
            
            if room['status'] == "Đang dọn dẹp":
                if st.button(f"Đánh dấu đã dọn xong #{room['room_no']}", key=f"clean_{room['room_no']}"):
                    update_room_status(room['room_no'], "Trống")
                    st.rerun()

# ---------------------------------------------------------
# 2. CHECK-IN / BOOKING
# ---------------------------------------------------------
elif menu == "Check-in / Đặt phòng":
    st.title("🔑 Nhận phòng & Đặt phòng mới")
    
    df_rooms = get_room_df()
    available_rooms = df_rooms[df_rooms['status'] == "Trống"]

    if available_rooms.empty:
        st.warning("Hiện tại không còn phòng trống sẵn sàng!")
    else:
        with st.form("checkin_form"):
            st.subheader("Thông tin lượt ở mới")
            
            room_choice = st.selectbox(
                "Chọn phòng trống:",
                available_rooms['room_no'].tolist(),
                format_func=lambda x: f"Phòng {x} - {df_rooms[df_rooms['room_no']==x]['type'].values[0]} ({df_rooms[df_rooms['room_no']==x]['price'].values[0]:,} VNĐ)"
            )
            
            guest_name = st.text_input("Họ và tên khách hàng:")
            checkin_date = st.date_input("Ngày nhận phòng:", datetime.date.today())
            
            submit = st.form_submit_button("Xác nhận Check-in")

            if submit:
                if not guest_name.strip():
                    st.error("Vui lòng nhập tên khách hàng!")
                else:
                    update_room_status(room_choice, "Đang ở", guest_name=guest_name, check_in=str(checkin_date), services=0)
                    st.success(f"Đã check-in thành công cho khách **{guest_name}** vào phòng **{room_choice}**!")
                    st.rerun()

# ---------------------------------------------------------
# 3. SERVICES & CHECK-OUT
# ---------------------------------------------------------
elif menu == "Dịch vụ & Check-out":
    st.title("💳 Phát sinh dịch vụ & Thanh toán (Check-out)")
    
    df_rooms = get_room_df()
    occupied_rooms = df_rooms[df_rooms['status'] == "Đang ở"]

    if occupied_rooms.empty:
        st.info("Hiện không có phòng nào đang có khách ở.")
    else:
        selected_room = st.selectbox("Chọn phòng xử lý:", occupied_rooms['room_no'].tolist())
        room_data = occupied_rooms[occupied_rooms['room_no'] == selected_room].iloc[0]

        tab1, tab2 = st.tabs(["Cập nhật Dịch vụ / Mini-bar", "Thanh toán & Check-out"])

        # Tab Dịch vụ
        with tab1:
            st.subheader(f"Thêm phụ phí / dịch vụ cho Phòng {selected_room}")
            service_item = st.selectbox("Chọn loại dịch vụ:", ["Nước uống Mini-bar", "Giặt ủi", "Đồ ăn tại phòng", "Khác"])
            service_cost = st.number_input("Số tiền dịch vụ (VNĐ):", min_value=10000, step=10000, value=50000)
            
            if st.button("Thêm vào hóa đơn"):
                new_services = room_data['services'] + service_cost
                update_room_status(
                    selected_room, 
                    "Đang ở", 
                    guest_name=room_data['guest_name'], 
                    check_in=room_data['check_in'], 
                    services=new_services
                )
                st.success(f"Đã thêm {service_cost:,} VNĐ ({service_item}) vào phòng {selected_room}")
                st.rerun()

        # Tab Check-out
        with tab2:
            st.subheader(f"Hóa đơn thanh toán - Phòng {selected_room}")
            
            room_price = room_data['price']
            service_fee = room_data['services']
            total = room_price + service_fee

            st.write(f"**Tên khách hàng:** {room_data['guest_name']}")
            st.write(f"**Ngày check-in:** {room_data['check_in']}")
            
            col_a, col_b, col_c = st.columns(3)
            col_a.metric("Tiền phòng", f"{room_price:,} VNĐ")
            col_b.metric("Phụ phí/Dịch vụ", f"{service_fee:,} VNĐ")
            col_c.metric("TỔNG THANH TOÁN", f"{total:,} VNĐ")

            if st.button("Xác nhận Thanh toán & Check-out", type="primary"):
                # Lưu lịch sử
                st.session_state.history.append({
                    "room_no": selected_room,
                    "guest_name": room_data['guest_name'],
                    "total_amount": total,
                    "checkout_date": str(datetime.date.today())
                })
                # Đổi trạng thái sang "Đang dọn dẹp" theo chuẩn quy trình KS
                update_room_status(selected_room, "Đang dọn dẹp")
                st.success(f"Phòng {selected_room} đã check-out thành công. Trạng thái phòng chuyển sang 'Đang dọn dẹp'.")
                st.rerun()

# ---------------------------------------------------------
# 4. ANALYTICS & REPORTS
# ---------------------------------------------------------
elif menu == "Báo cáo Doanh thu & KPIs":
    st.title("📊 Báo cáo Vận hành & Hiệu quả Kinh doanh")

    df_history = pd.DataFrame(st.session_state.history)
    df_rooms = get_room_df()

    # Top metrics
    total_revenue = df_history['total_amount'].sum() if not df_history.empty else 0
    total_rooms = len(df_rooms)
    occupied_count = len(df_rooms[df_rooms['status'] == 'Đang ở'])
    
    # Hotel Management Specific KPIs
    adr = df_history['total_amount'].mean() if not df_history.empty else 0  # Average Daily Rate
    revpar = total_revenue / total_rooms if total_rooms > 0 else 0           # Revenue Per Available Room

    m1, m2, m3 = st.columns(3)
    m1.metric("Tổng doanh thu ghi nhận", f"{total_revenue:,} VNĐ")
    m2.metric("ADR (Giá trung bình/phòng)", f"{round(adr):,} VNĐ")
    m3.metric("RevPAR (Doanh thu/phòng hiện có)", f"{round(revpar):,} VNĐ")

    st.divider()

    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.subheader("Cơ cấu trạng thái phòng")
        fig_status = px.pie(
            df_rooms, 
            names='status', 
            title="Tỷ lệ trạng thái phòng hiện tại",
            color='status',
            color_discrete_map={"Trống": "#28a745", "Đang ở": "#dc3545", "Đang dọn dẹp": "#ffc107"}
        )
        st.plotly_chart(fig_status, use_container_width=True)

    with col_chart2:
        st.subheader("Lịch sử giao dịch gần đây")
        if not df_history.empty:
            st.dataframe(
                df_history.rename(columns={
                    "room_no": "Phòng", 
                    "guest_name": "Tên khách", 
                    "total_amount": "Tổng tiền (VNĐ)", 
                    "checkout_date": "Ngày trả phòng"
                }),
                use_container_width=True
            )
        else:
            st.write("Chưa có dữ liệu giao dịch.")
