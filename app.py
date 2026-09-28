````python
import os
import datetime
from decimal import Decimal

import streamlit as st
import pandas as pd
import plotly.express as px
import pymysql


# =========================================================
# 1. PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="Hệ thống Quản lý Khách sạn (HMS)",
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="expanded"
)


# =========================================================
# 2. CSS
# =========================================================

st.markdown(
    """
    <style>
        .metric-card {
            background-color: #f8f9fa;
            border-radius: 8px;
            padding: 15px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }

        .room-card {
            background-color: white;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 15px;
            border: 1px solid #e0e0e0;
        }

        div[data-testid="stMetric"] {
            background-color: #f8f9fa;
            border-radius: 8px;
            padding: 10px;
        }
    </style>
    """,
    unsafe_allow_html=True
)


# =========================================================
# 3. MYSQL AIVEN CONFIGURATION
# =========================================================

DB_USER = "avnadmin"

DB_PASSWORD = "AVNS_DFTmGqDGhpod7tVs9_v"

DB_HOST = "mysql-1905d98b-su27062005-0289.b.aivencloud.com"

DB_PORT = 24833

DB_NAME = "defaultdb"


# =========================================================
# 4. SSL / CA CONFIGURATION
# =========================================================
#
# Nếu bạn tải ca.pem từ Aiven:
#
# project/
# ├── app.py
# ├── requirements.txt
# └── ca.pem
#
# Code sẽ tự động sử dụng ca.pem.
#
# Nếu chưa có ca.pem, code vẫn sử dụng SSL/TLS.
# =========================================================

CA_FILE = "ca.pem"


def get_ssl_config():
    """
    Cấu hình SSL cho kết nối Aiven MySQL.
    """

    if os.path.exists(CA_FILE):

        return {
            "ca": CA_FILE,
            "check_hostname": True
        }

    # Nếu chưa có CA certificate.
    # Kết nối vẫn được mã hóa bằng TLS.
    return {
        "check_hostname": False
    }


# =========================================================
# 5. DATABASE CONNECTION
# =========================================================

@st.cache_resource
def get_connection():
    """
    Tạo kết nối MySQL tới Aiven.

    @st.cache_resource giúp Streamlit tái sử dụng
    connection giữa các lần rerun.
    """

    connection = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,

        # Không tự commit để có thể sử dụng transaction
        autocommit=False,

        connect_timeout=15,
        read_timeout=30,
        write_timeout=30,

        ssl=get_ssl_config()
    )

    return connection


# =========================================================
# 6. DATABASE INITIALIZATION
# =========================================================

def initialize_database():

    connection = get_connection()

    try:

        with connection.cursor() as cursor:

            # -------------------------------------------------
            # TABLE: ROOMS
            # -------------------------------------------------

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS rooms (
                    id INT AUTO_INCREMENT PRIMARY KEY,

                    room_no VARCHAR(20)
                        NOT NULL UNIQUE,

                    room_type VARCHAR(100)
                        NOT NULL,

                    price DECIMAL(15,2)
                        NOT NULL DEFAULT 0,

                    status VARCHAR(50)
                        NOT NULL DEFAULT 'Trống',

                    guest_name VARCHAR(255)
                        DEFAULT NULL,

                    check_in DATE
                        DEFAULT NULL,

                    services_total DECIMAL(15,2)
                        NOT NULL DEFAULT 0,

                    created_at TIMESTAMP
                        DEFAULT CURRENT_TIMESTAMP,

                    updated_at TIMESTAMP
                        DEFAULT CURRENT_TIMESTAMP
                        ON UPDATE CURRENT_TIMESTAMP,

                    INDEX idx_room_status (status)
                )
                """
            )

            # -------------------------------------------------
            # TABLE: SERVICES
            # -------------------------------------------------

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS services (
                    id INT AUTO_INCREMENT PRIMARY KEY,

                    room_no VARCHAR(20)
                        NOT NULL,

                    guest_name VARCHAR(255)
                        DEFAULT NULL,

                    service_name VARCHAR(255)
                        NOT NULL,

                    amount DECIMAL(15,2)
                        NOT NULL DEFAULT 0,

                    service_date DATETIME
                        NOT NULL DEFAULT CURRENT_TIMESTAMP,

                    INDEX idx_service_room (room_no),

                    INDEX idx_service_date (service_date)
                )
                """
            )

            # -------------------------------------------------
            # TABLE: TRANSACTIONS
            # -------------------------------------------------

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS transactions (
                    id INT AUTO_INCREMENT PRIMARY KEY,

                    room_no VARCHAR(20)
                        NOT NULL,

                    guest_name VARCHAR(255)
                        NOT NULL,

                    room_price DECIMAL(15,2)
                        NOT NULL DEFAULT 0,

                    service_fee DECIMAL(15,2)
                        NOT NULL DEFAULT 0,

                    total_amount DECIMAL(15,2)
                        NOT NULL DEFAULT 0,

                    check_in_date DATE
                        DEFAULT NULL,

                    checkout_date DATE
                        NOT NULL,

                    created_at TIMESTAMP
                        DEFAULT CURRENT_TIMESTAMP,

                    INDEX idx_transaction_room (room_no),

                    INDEX idx_transaction_date (checkout_date)
                )
                """
            )

        connection.commit()

    except Exception:

        connection.rollback()

        raise


# =========================================================
# 7. DATABASE QUERY HELPERS
# =========================================================

def fetch_all(query, params=None):

    connection = get_connection()

    try:

        with connection.cursor() as cursor:

            cursor.execute(
                query,
                params or ()
            )

            return cursor.fetchall()

    except pymysql.MySQLError:

        # Thử kết nối lại nếu connection hết hạn
        connection.ping(
            reconnect=True
        )

        with connection.cursor() as cursor:

            cursor.execute(
                query,
                params or ()
            )

            return cursor.fetchall()


def fetch_one(query, params=None):

    connection = get_connection()

    try:

        with connection.cursor() as cursor:

            cursor.execute(
                query,
                params or ()
            )

            return cursor.fetchone()

    except pymysql.MySQLError:

        connection.ping(
            reconnect=True
        )

        with connection.cursor() as cursor:

            cursor.execute(
                query,
                params or ()
            )

            return cursor.fetchone()


def execute_query(
    query,
    params=None
):

    connection = get_connection()

    try:

        with connection.cursor() as cursor:

            cursor.execute(
                query,
                params or ()
            )

        connection.commit()

    except Exception:

        connection.rollback()

        raise


# =========================================================
# 8. SEED DATA
# =========================================================

def seed_database():

    connection = get_connection()

    try:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT COUNT(*) AS total
                FROM rooms
                """
            )

            room_count = cursor.fetchone()["total"]

            # ---------------------------------------------
            # ROOM SAMPLE DATA
            # ---------------------------------------------

            if room_count == 0:

                rooms = [

                    (
                        "101",
                        "Standard Single",
                        500000,
                        "Trống",
                        None,
                        None,
                        0
                    ),

                    (
                        "102",
                        "Standard Single",
                        500000,
                        "Trống",
                        None,
                        None,
                        0
                    ),

                    (
                        "201",
                        "Deluxe Double",
                        900000,
                        "Đang ở",
                        "Nguyễn Văn A",
                        "2026-09-27",
                        150000
                    ),

                    (
                        "202",
                        "Deluxe Double",
                        900000,
                        "Trống",
                        None,
                        None,
                        0
                    ),

                    (
                        "301",
                        "VIP Suite",
                        1800000,
                        "Đang dọn dẹp",
                        None,
                        None,
                        0
                    ),

                    (
                        "302",
                        "VIP Suite",
                        1800000,
                        "Đang ở",
                        "Trần Thị B",
                        "2026-09-28",
                        300000
                    )
                ]

                cursor.executemany(
                    """
                    INSERT INTO rooms (
                        room_no,
                        room_type,
                        price,
                        status,
                        guest_name,
                        check_in,
                        services_total
                    )
                    VALUES (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s
                    )
                    """,
                    rooms
                )

            # ---------------------------------------------
            # TRANSACTION SAMPLE DATA
            # ---------------------------------------------

            cursor.execute(
                """
                SELECT COUNT(*) AS total
                FROM transactions
                """
            )

            transaction_count = cursor.fetchone()["total"]

            if transaction_count == 0:

                transactions = [

                    (
                        "101",
                        "Lê Văn C",
                        500000,
                        250000,
                        750000,
                        "2026-09-25",
                        "2026-09-26"
                    ),

                    (
                        "201",
                        "Phạm Văn D",
                        900000,
                        200000,
                        1100000,
                        "2026-09-26",
                        "2026-09-27"
                    )
                ]

                cursor.executemany(
                    """
                    INSERT INTO transactions (
                        room_no,
                        guest_name,
                        room_price,
                        service_fee,
                        total_amount,
                        check_in_date,
                        checkout_date
                    )
                    VALUES (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s
                    )
                    """,
                    transactions
                )

        connection.commit()

    except Exception:

        connection.rollback()

        raise


# =========================================================
# 9. ROOM FUNCTIONS
# =========================================================

def get_room_df():

    rows = fetch_all(
        """
        SELECT
            id,
            room_no,
            room_type,
            price,
            status,
            guest_name,
            check_in,
            services_total
        FROM rooms
        ORDER BY CAST(room_no AS UNSIGNED)
        """
    )

    df = pd.DataFrame(rows)

    if not df.empty:

        df["price"] = pd.to_numeric(
            df["price"],
            errors="coerce"
        ).fillna(0)

        df["services_total"] = pd.to_numeric(
            df["services_total"],
            errors="coerce"
        ).fillna(0)

    return df


def get_room(room_no):

    return fetch_one(
        """
        SELECT *
        FROM rooms
        WHERE room_no = %s
        """,
        (room_no,)
    )


def update_room_status(
    room_no,
    new_status,
    guest_name=None,
    check_in=None,
    services=0
):

    execute_query(
        """
        UPDATE rooms
        SET
            status = %s,
            guest_name = %s,
            check_in = %s,
            services_total = %s
        WHERE room_no = %s
        """,
        (
            new_status,
            guest_name,
            check_in,
            services,
            room_no
        )
    )


# =========================================================
# 10. CHECK-IN
# =========================================================

def check_in_room(
    room_no,
    guest_name,
    checkin_date
):

    connection = get_connection()

    try:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT status
                FROM rooms
                WHERE room_no = %s
                FOR UPDATE
                """,
                (room_no,)
            )

            room = cursor.fetchone()

            if not room:

                raise Exception(
                    "Không tìm thấy phòng."
                )

            if room["status"] != "Trống":

                raise Exception(
                    "Phòng này không còn trống."
                )

            cursor.execute(
                """
                UPDATE rooms
                SET
                    status = 'Đang ở',
                    guest_name = %s,
                    check_in = %s,
                    services_total = 0
                WHERE room_no = %s
                """,
                (
                    guest_name,
                    checkin_date,
                    room_no
                )
            )

        connection.commit()

    except Exception:

        connection.rollback()

        raise


# =========================================================
# 11. SERVICES
# =========================================================

def add_service(
    room_no,
    guest_name,
    service_name,
    amount
):

    connection = get_connection()

    try:

        with connection.cursor() as cursor:

            # ---------------------------------------------
            # Kiểm tra phòng
            # ---------------------------------------------

            cursor.execute(
                """
                SELECT status
                FROM rooms
                WHERE room_no = %s
                FOR UPDATE
                """,
                (room_no,)
            )

            room = cursor.fetchone()

            if not room:

                raise Exception(
                    "Không tìm thấy phòng."
                )

            if room["status"] != "Đang ở":

                raise Exception(
                    "Chỉ được thêm dịch vụ "
                    "cho phòng đang có khách."
                )

            # ---------------------------------------------
            # INSERT SERVICE
            # ---------------------------------------------

            cursor.execute(
                """
                INSERT INTO services (
                    room_no,
                    guest_name,
                    service_name,
                    amount
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    %s
                )
                """,
                (
                    room_no,
                    guest_name,
                    service_name,
                    amount
                )
            )

            # ---------------------------------------------
            # UPDATE TOTAL SERVICE
            # ---------------------------------------------

            cursor.execute(
                """
                UPDATE rooms
                SET
                    services_total =
                    services_total + %s
                WHERE room_no = %s
                """,
                (
                    amount,
                    room_no
                )
            )

        connection.commit()

    except Exception:

        connection.rollback()

        raise


def get_room_services(room_no):

    rows = fetch_all(
        """
        SELECT
            id,
            service_name,
            amount,
            service_date
        FROM services
        WHERE room_no = %s
        ORDER BY service_date DESC, id DESC
        """,
        (room_no,)
    )

    df = pd.DataFrame(rows)

    if not df.empty:

        df["amount"] = pd.to_numeric(
            df["amount"],
            errors="coerce"
        ).fillna(0)

    return df


# =========================================================
# 12. CHECK-OUT
# =========================================================

def checkout_room(room_no):

    connection = get_connection()

    try:

        with connection.cursor() as cursor:

            # ---------------------------------------------
            # LOCK ROOM
            # ---------------------------------------------

            cursor.execute(
                """
                SELECT *
                FROM rooms
                WHERE room_no = %s
                FOR UPDATE
                """,
                (room_no,)
            )

            room = cursor.fetchone()

            if not room:

                raise Exception(
                    "Không tìm thấy phòng."
                )

            if room["status"] != "Đang ở":

                raise Exception(
                    "Phòng không ở trạng thái Đang ở."
                )

            # ---------------------------------------------
            # CALCULATE BILL
            # ---------------------------------------------

            room_price = Decimal(
                str(room["price"])
            )

            service_fee = Decimal(
                str(
                    room["services_total"]
                    or 0
                )
            )

            total_amount = (
                room_price +
                service_fee
            )

            checkout_date = (
                datetime.date.today()
            )

            # ---------------------------------------------
            # SAVE TRANSACTION
            # ---------------------------------------------

            cursor.execute(
                """
                INSERT INTO transactions (
                    room_no,
                    guest_name,
                    room_price,
                    service_fee,
                    total_amount,
                    check_in_date,
                    checkout_date
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
                """,
                (
                    room["room_no"],
                    room["guest_name"],
                    room_price,
                    service_fee,
                    total_amount,
                    room["check_in"],
                    checkout_date
                )
            )

            # ---------------------------------------------
            # UPDATE ROOM
            # ---------------------------------------------

            cursor.execute(
                """
                UPDATE rooms
                SET
                    status = 'Đang dọn dẹp',
                    guest_name = NULL,
                    check_in = NULL,
                    services_total = 0
                WHERE room_no = %s
                """,
                (room_no,)
            )

        connection.commit()

        return total_amount

    except Exception:

        connection.rollback()

        raise


# =========================================================
# 13. TRANSACTION HISTORY
# =========================================================

def get_history_df():

    rows = fetch_all(
        """
        SELECT
            id,
            room_no,
            guest_name,
            room_price,
            service_fee,
            total_amount,
            check_in_date,
            checkout_date,
            created_at
        FROM transactions
        ORDER BY checkout_date DESC, id DESC
        """
    )

    df = pd.DataFrame(rows)

    if not df.empty:

        for column in [
            "room_price",
            "service_fee",
            "total_amount"
        ]:

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce"
            ).fillna(0)

    return df


# =========================================================
# 14. START DATABASE
# =========================================================

try:

    initialize_database()

    seed_database()

except Exception as e:

    st.error(
        "❌ Không thể kết nối tới MySQL Aiven."
    )

    st.code(
        str(e),
        language="text"
    )

    st.markdown(
        """
        ### Kiểm tra các thông tin sau:

        **Host**
        ```
        mysql-1905d98b-su27062005-0289.b.aivencloud.com
        ```

        **Port**
        ```
        24833
        ```

        **User**
        ```
        avnadmin
        ```

        **Database**
        ```
        defaultdb
        ```

        Nếu Aiven yêu cầu CA certificate,
        hãy tải `ca.pem` từ Aiven và đặt cùng
        thư mục với `app.py`.
        """
    )

    st.stop()


# =========================================================
# 15. SIDEBAR
# =========================================================

st.sidebar.title(
    "🏨 HMS Manager"
)

st.sidebar.caption(
    "Hệ thống Quản trị Khách sạn Vận hành"
)

menu = st.sidebar.radio(
    "Danh mục quản lý",
    [
        "Sơ đồ phòng (Live Grid)",
        "Check-in / Đặt phòng",
        "Dịch vụ & Check-out",
        "Báo cáo Doanh thu & KPIs"
    ]
)

st.sidebar.divider()

st.sidebar.success(
    "🟢 MySQL Aiven: Connected"
)

st.sidebar.info(
    """
    💡 **Quy trình phòng**

    Trống
    ↓
    Đang ở
    ↓
    Đang dọn dẹp
    ↓
    Trống
    """
)


# =========================================================
# 16. LIVE ROOM GRID
# =========================================================

if menu == "Sơ đồ phòng (Live Grid)":

    st.title(
        "📌 Sơ đồ trạng thái phòng thời gian thực"
    )

    df_rooms = get_room_df()

    # -----------------------------------------------------
    # KPI
    # -----------------------------------------------------

    total_rooms = len(df_rooms)

    occupied = len(
        df_rooms[
            df_rooms["status"] == "Đang ở"
        ]
    )

    available = len(
        df_rooms[
            df_rooms["status"] == "Trống"
        ]
    )

    dirty = len(
        df_rooms[
            df_rooms["status"] == "Đang dọn dẹp"
        ]
    )

    if total_rooms > 0:

        occ_rate = round(
            occupied / total_rooms * 100,
            1
        )

    else:

        occ_rate = 0

    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric(
        "Tổng số phòng",
        total_rooms
    )

    c2.metric(
        "Đang có khách",
        occupied
    )

    c3.metric(
        "Sẵn sàng đón khách",
        available
    )

    c4.metric(
        "Đang dọn dẹp",
        dirty
    )

    c5.metric(
        "Tỷ lệ lấp đầy",
        f"{occ_rate}%"
    )

    st.divider()

    # -----------------------------------------------------
    # FILTER
    # -----------------------------------------------------

    filter_status = st.selectbox(
        "Lọc theo trạng thái:",
        [
            "Tất cả",
            "Trống",
            "Đang ở",
            "Đang dọn dẹp"
        ]
    )

    if filter_status == "Tất cả":

        filtered_df = df_rooms

    else:

        filtered_df = df_rooms[
            df_rooms["status"] == filter_status
        ]

    # -----------------------------------------------------
    # ROOM GRID
    # -----------------------------------------------------

    cols = st.columns(3)

    status_colors = {
        "Trống": "#28a745",
        "Đang ở": "#dc3545",
        "Đang dọn dẹp": "#ffc107"
    }

    for position, (_, room) in enumerate(
        filtered_df.iterrows()
    ):

        col = cols[position % 3]

        color = status_colors.get(
            room["status"],
            "#6c757d"
        )

        guest_name = (
            room["guest_name"]
            if room["guest_name"]
            else "---"
        )

        with col:

            st.markdown(
                f"""
                <div style="
                    border-left: 6px solid {color};
                    padding: 12px;
                    background-color: #ffffff;
                    border-radius: 8px;
                    margin-bottom: 15px;
                    border: 1px solid #e0e0e0;
                ">

                    <h3 style="
                        margin: 0;
                        color: #333;
                    ">
                        Phòng {room['room_no']}
                    </h3>

                    <p style="
                        margin: 5px 0;
                        color: {color};
                        font-weight: bold;
                    ">
                        {room['status']}
                    </p>

                    <p style="margin: 5px 0;">
                        <b>Loại:</b>
                        {room['room_type']}
                    </p>

                    <p style="margin: 5px 0;">
                        <b>Giá phòng:</b>
                        {room['price']:,.0f} VNĐ/đêm
                    </p>

                    <p style="margin: 5px 0;">
                        <b>Khách hàng:</b>
                        {guest_name}
                    </p>

                    <p style="margin: 5px 0;">
                        <b>Dịch vụ:</b>
                        {room['services_total']:,.0f} VNĐ
                    </p>

                </div>
                """,
                unsafe_allow_html=True
            )

            # ---------------------------------------------
            # HOUSEKEEPING
            # ---------------------------------------------

            if room["status"] == "Đang dọn dẹp":

                if st.button(
                    f"✅ Đã dọn xong #{room['room_no']}",
                    key=f"clean_{room['room_no']}"
                ):

                    try:

                        update_room_status(
                            room["room_no"],
                            "Trống",
                            None,
                            None,
                            0
                        )

                        st.success(
                            f"Phòng {room['room_no']} "
                            "đã sẵn sàng đón khách."
                        )

                        st.rerun()

                    except Exception as e:

                        st.error(
                            f"Lỗi cập nhật phòng: {e}"
                        )


# =========================================================
# 17. CHECK-IN / BOOKING
# =========================================================

elif menu == "Check-in / Đặt phòng":

    st.title(
        "🔑 Nhận phòng & Đặt phòng mới"
    )

    df_rooms = get_room_df()

    available_rooms = df_rooms[
        df_rooms["status"] == "Trống"
    ]

    if available_rooms.empty:

        st.warning(
            "Hiện tại không còn phòng trống sẵn sàng!"
        )

    else:

        with st.form(
            "checkin_form"
        ):

            st.subheader(
                "Thông tin lượt ở mới"
            )

            room_choice = st.selectbox(
                "Chọn phòng trống:",
                available_rooms[
                    "room_no"
                ].tolist(),
                format_func=lambda room_no:
                    (
                        f"Phòng {room_no} - "
                        f"{df_rooms.loc["
                            df_rooms["room_no"] == room_no,
                            "room_type"
                        ].iloc[0]} - "
                        f"{df_rooms.loc["
                            df_rooms["room_no"] == room_no,
                            "price"
                        ].iloc[0]:,.0f} VNĐ"
                    )
            )

            guest_name = st.text_input(
                "Họ và tên khách hàng:"
            )

            checkin_date = st.date_input(
                "Ngày nhận phòng:",
                datetime.date.today()
            )

            submit = st.form_submit_button(
                "🔑 Xác nhận Check-in",
                type="primary"
            )

            if submit:

                if not guest_name.strip():

                    st.error(
                        "Vui lòng nhập tên khách hàng!"
                    )

                else:

                    try:

                        check_in_room(
                            room_choice,
                            guest_name.strip(),
                            checkin_date
                        )

                        st.success(
                            f"Đã check-in thành công "
                            f"cho khách **{guest_name}** "
                            f"vào phòng **{room_choice}**!"
                        )

                        st.rerun()

                    except Exception as e:

                        st.error(
                            f"Lỗi Check-in: {e}"
                        )


# =========================================================
# 18. SERVICES & CHECK-OUT
# =========================================================

elif menu == "Dịch vụ & Check-out":

    st.title(
        "💳 Phát sinh dịch vụ & Thanh toán"
    )

    df_rooms = get_room_df()

    occupied_rooms = df_rooms[
        df_rooms["status"] == "Đang ở"
    ]

    if occupied_rooms.empty:

        st.info(
            "Hiện không có phòng nào đang có khách ở."
        )

    else:

        selected_room = st.selectbox(
            "Chọn phòng xử lý:",
            occupied_rooms[
                "room_no"
            ].tolist()
        )

        room_data = get_room(
            selected_room
        )

        if not room_data:

            st.error(
                "Không tìm thấy phòng."
            )

            st.stop()

        tab1, tab2 = st.tabs(
            [
                "🛎️ Dịch vụ / Mini-bar",
                "💳 Thanh toán & Check-out"
            ]
        )

        # =================================================
        # TAB 1 - SERVICE
        # =================================================

        with tab1:

            st.subheader(
                f"Thêm phụ phí / dịch vụ "
                f"cho Phòng {selected_room}"
            )

            service_item = st.selectbox(
                "Chọn loại dịch vụ:",
                [
                    "Nước uống Mini-bar",
                    "Giặt ủi",
                    "Đồ ăn tại phòng",
                    "Đưa đón sân bay",
                    "Spa",
                    "Khác"
                ]
            )

            service_cost = st.number_input(
                "Số tiền dịch vụ (VNĐ):",
                min_value=10000,
                step=10000,
                value=50000
            )

            if st.button(
                "➕ Thêm vào hóa đơn",
                type="primary"
            ):

                try:

                    add_service(
                        selected_room,
                        room_data["guest_name"],
                        service_item,
                        service_cost
                    )

                    st.success(
                        f"Đã thêm "
                        f"{service_cost:,.0f} VNĐ "
                        f"({service_item}) "
                        f"vào phòng {selected_room}."
                    )

                    st.rerun()

                except Exception as e:

                    st.error(
                        f"Lỗi thêm dịch vụ: {e}"
                    )

            st.divider()

            st.subheader(
                "📋 Danh sách dịch vụ đã sử dụng"
            )

            service_df = get_room_services(
                selected_room
            )

            if service_df.empty:

                st.info(
                    "Phòng chưa phát sinh dịch vụ."
                )

            else:

                service_display = (
                    service_df.rename(
                        columns={
                            "service_name": "Dịch vụ",
                            "amount": "Số tiền",
                            "service_date": "Thời gian"
                        }
                    )
                )

                service_display[
                    "Số tiền"
                ] = service_display[
                    "Số tiền"
                ].map(
                    lambda x:
                        f"{x:,.0f} VNĐ"
                )

                st.dataframe(
                    service_display[
                        [
                            "Dịch vụ",
                            "Số tiền",
                            "Thời gian"
                        ]
                    ],
                    use_container_width=True,
                    hide_index=True
                )

        # =================================================
        # TAB 2 - CHECKOUT
        # =================================================

        with tab2:

            st.subheader(
                f"Hóa đơn thanh toán - "
                f"Phòng {selected_room}"
            )

            room_price = Decimal(
                str(room_data["price"])
            )

            service_fee = Decimal(
                str(
                    room_data[
                        "services_total"
                    ] or 0
                )
            )

            total = (
                room_price +
                service_fee
            )

            st.write(
                f"**Tên khách hàng:** "
                f"{room_data['guest_name']}"
            )

            st.write(
                f"**Ngày check-in:** "
                f"{room_data['check_in']}"
            )

            st.divider()

            col_a, col_b, col_c = st.columns(3)

            col_a.metric(
                "Tiền phòng",
                f"{room_price:,.0f} VNĐ"
            )

            col_b.metric(
                "Phụ phí/Dịch vụ",
                f"{service_fee:,.0f} VNĐ"
            )

            col_c.metric(
                "TỔNG THANH TOÁN",
                f"{total:,.0f} VNĐ"
            )

            st.divider()

            if st.button(
                "💳 Xác nhận Thanh toán & Check-out",
                type="primary",
                use_container_width=True
            ):

                try:

                    checkout_total = checkout_room(
                        selected_room
                    )

                    st.success(
                        f"Phòng {selected_room} "
                        f"đã check-out thành công!"
                    )

                    st.success(
                        f"Tổng thanh toán: "
                        f"{checkout_total:,.0f} VNĐ"
                    )

                    st.info(
                        "Trạng thái phòng đã chuyển "
                        "sang **Đang dọn dẹp**."
                    )

                    st.rerun()

                except Exception as e:

                    st.error(
                        f"Lỗi Check-out: {e}"
                    )


# =========================================================
# 19. REPORTS & KPIs
# =========================================================

elif menu == "Báo cáo Doanh thu & KPIs":

    st.title(
        "📊 Báo cáo Vận hành & Hiệu quả Kinh doanh"
    )

    df_history = get_history_df()

    df_rooms = get_room_df()

    # =====================================================
    # DATE FILTER
    # =====================================================

    st.subheader(
        "🔎 Bộ lọc báo cáo"
    )

    col_filter1, col_filter2 = st.columns(2)

    with col_filter1:

        start_date = st.date_input(
            "Từ ngày:",
            datetime.date.today()
            - datetime.timedelta(days=30)
        )

    with col_filter2:

        end_date = st.date_input(
            "Đến ngày:",
            datetime.date.today()
        )

    # =====================================================
    # FILTER TRANSACTIONS
    # =====================================================

    if not df_history.empty:

        df_history["checkout_date"] = (
            pd.to_datetime(
                df_history["checkout_date"]
            ).dt.date
        )

        filtered_history = df_history[
            (
                df_history["checkout_date"]
                >= start_date
            )
            &
            (
                df_history["checkout_date"]
                <= end_date
            )
        ].copy()

    else:

        filtered_history = df_history

    # =====================================================
    # KPI
    # =====================================================

    if not filtered_history.empty:

        total_revenue = (
            filtered_history[
                "total_amount"
            ].sum()
        )

        transaction_count = (
            len(filtered_history)
        )

        adr = (
            total_revenue /
            transaction_count
        )

    else:

        total_revenue = 0

        transaction_count = 0

        adr = 0

    total_rooms = len(df_rooms)

    occupied_count = len(
        df_rooms[
            df_rooms["status"] == "Đang ở"
        ]
    )

    revpar = (
        total_revenue /
        total_rooms
        if total_rooms > 0
        else 0
    )

    occupancy_rate = (
        occupied_count /
        total_rooms *
        100
        if total_rooms > 0
        else 0
    )

    # =====================================================
    # KPI DISPLAY
    # =====================================================

    m1, m2, m3, m4 = st.columns(4)

    m1.metric(
        "💰 Tổng doanh thu",
        f"{total_revenue:,.0f} VNĐ"
    )

    m2.metric(
        "📈 ADR",
        f"{adr:,.0f} VNĐ"
    )

    m3.metric(
        "🏨 RevPAR",
        f"{revpar:,.0f} VNĐ"
    )

    m4.metric(
        "📊 Công suất hiện tại",
        f"{occupancy_rate:.1f}%"
    )

    st.divider()

    # =====================================================
    # CHARTS
    # =====================================================

    col_chart1, col_chart2 = st.columns(2)

    # -----------------------------------------------------
    # ROOM STATUS
    # -----------------------------------------------------

    with col_chart1:

        st.subheader(
            "🏨 Cơ cấu trạng thái phòng"
        )

        if not df_rooms.empty:

            status_count = (
                df_rooms[
                    "status"
                ]
                .value_counts()
                .reset_index()
            )

            status_count.columns = [
                "status",
                "count"
            ]

            fig_status = px.pie(
                status_count,
                names="status",
                values="count",
                title="Tỷ lệ trạng thái phòng hiện tại",
                color="status",
                color_discrete_map={
                    "Trống": "#28a745",
                    "Đang ở": "#dc3545",
                    "Đang dọn dẹp": "#ffc107"
                }
            )

            st.plotly_chart(
                fig_status,
                use_container_width=True
            )

        else:

            st.info(
                "Chưa có dữ liệu phòng."
            )

    # -----------------------------------------------------
    # REVENUE CHART
    # -----------------------------------------------------

    with col_chart2:

        st.subheader(
            "💰 Doanh thu theo ngày"
        )

        if not filtered_history.empty:

            revenue_daily = (
                filtered_history
                .groupby(
                    "checkout_date",
                    as_index=False
                )[
                    "total_amount"
                ]
                .sum()
            )

            fig_revenue = px.bar(
                revenue_daily,
                x="checkout_date",
                y="total_amount",
                title="Doanh thu theo ngày",
                labels={
                    "checkout_date": "Ngày",
                    "total_amount": "Doanh thu"
                }
            )

            fig_revenue.update_yaxes(
                tickformat=",.0f"
            )

            st.plotly_chart(
                fig_revenue,
                use_container_width=True
            )

        else:

            st.info(
                "Chưa có doanh thu "
                "trong khoảng thời gian đã chọn."
            )

    # =====================================================
    # TRANSACTION HISTORY
    # =====================================================

    st.divider()

    st.subheader(
        "📜 Lịch sử giao dịch"
    )

    if not filtered_history.empty:

        display_history = (
            filtered_history.rename(
                columns={
                    "id": "ID",
                    "room_no": "Phòng",
                    "guest_name": "Tên khách",
                    "room_price": "Tiền phòng",
                    "service_fee": "Dịch vụ",
                    "total_amount": "Tổng tiền",
                    "check_in_date": "Ngày check-in",
                    "checkout_date": "Ngày check-out"
                }
            )
        )

        for column in [
            "Tiền phòng",
            "Dịch vụ",
            "Tổng tiền"
        ]:

            display_history[column] = (
                display_history[column]
                .map(
                    lambda x:
                        f"{x:,.0f} VNĐ"
                )
            )

        st.dataframe(
            display_history[
                [
                    "ID",
                    "Phòng",
                    "Tên khách",
                    "Tiền phòng",
                    "Dịch vụ",
                    "Tổng tiền",
                    "Ngày check-in",
                    "Ngày check-out"
                ]
            ],
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info(
            "Chưa có giao dịch "
            "trong khoảng thời gian này."
        )

    # =====================================================
    # DATABASE INFORMATION
    # =====================================================

    st.divider()

    st.subheader(
        "🗄️ Thông tin Database"
    )

    db1, db2, db3, db4 = st.columns(4)

    db1.metric(
        "Database",
        DB_NAME
    )

    db2.metric(
        "Tổng phòng",
        total_rooms
    )

    db3.metric(
        "Tổng giao dịch",
        len(df_history)
    )

    db4.metric(
        "Tổng dịch vụ",
        len(
            fetch_all(
                "SELECT id FROM services"
            )
        )
    )
````
