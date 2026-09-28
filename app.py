import sqlite3
from contextlib import closing
from datetime import date, datetime
import pandas as pd
import streamlit as st
# =========================================================
# CẤU HÌNH
# =========================================================
st.set_page_config(
page_title="Quản lý khách sạn",
page_icon=" ",
layout="wide",
initial_sidebar_state="expanded",
)
DB_FILE = "hotel.db"
ROOM_STATUSES = ["Trống", "Đã đặt", "Đang ở", "Bảo trì"]
BOOKING_STATUSES = ["Đã đặt", "Đang ở", "Đã trả phòng", "Đã hủy"]
# =========================================================
# DATABASE
# =========================================================
def get_connection():
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
conn.row_factory = sqlite3.Row
conn.execute("PRAGMA foreign_keys = ON")return conn
def init_database():
with closing(get_connection()) as conn:
conn.executescript(
"""
CREATE TABLE IF NOT EXISTS rooms (
id INTEGER PRIMARY KEY AUTOINCREMENT,
room_number TEXT UNIQUE NOT NULL,
room_type TEXT NOT NULL,
price REAL NOT NULL DEFAULT 0,
floor INTEGER DEFAULT 1,
status TEXT NOT NULL DEFAULT 'Trống',
note TEXT,
created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS customers (
id INTEGER PRIMARY KEY AUTOINCREMENT,
full_name TEXT NOT NULL,
phone TEXT,
email TEXT,
identity_card TEXT,
address TEXT,
note TEXT,
created_at TEXT DEFAULT CURRENT_TIMESTAMP
);CREATE TABLE IF NOT EXISTS bookings (
id INTEGER PRIMARY KEY AUTOINCREMENT,
room_id INTEGER NOT NULL,
customer_id INTEGER NOT NULL,
check_in TEXT NOT NULL,
check_out TEXT NOT NULL,
adults INTEGER DEFAULT 1,
children INTEGER DEFAULT 0,
total_amount REAL DEFAULT 0,
paid_amount REAL DEFAULT 0,
status TEXT DEFAULT 'Đã đặt',
note TEXT,
created_at TEXT DEFAULT CURRENT_TIMESTAMP,
FOREIGN KEY(room_id) REFERENCES rooms(id),
FOREIGN KEY(customer_id) REFERENCES customers(id)
);
"""
)
count = conn.execute("SELECT COUNT(*) FROM rooms").fetchone()[0]
if count == 0:
sample_rooms = [
("101", "Phòng đơn", 400000, 1),
("102", "Phòng đơn", 400000, 1),
("103", "Phòng đôi", 600000, 1),
("104", "Phòng đôi", 600000, 1),
("201", "Phòng VIP", 1000000, 2),
("202", "Phòng VIP", 1000000, 2),
("203", "Phòng gia đình", 1200000, 2),("204", "Phòng gia đình", 1200000, 2),
("301", "Phòng đơn", 450000, 3),
("302", "Phòng đôi", 650000, 3),
]
conn.executemany(
"""
INSERT INTO rooms (room_number, room_type, price, floor)
VALUES (?, ?, ?, ?)
""",
sample_rooms,
)
conn.commit()
def query_db(query, params=(), fetchall=True):
with closing(get_connection()) as conn:
cur = conn.execute(query, params)
return cur.fetchall() if fetchall else cur.fetchone()
def execute_db(query, params=()):
with closing(get_connection()) as conn:
cur = conn.execute(query, params)
conn.commit()
return cur.lastrowid
def format_money(value):
return f"{float(value or 0):,.0f} ₫".replace(",", ".")def calculate_nights(check_in, check_out):
return (check_out - check_in).days
def room_status_counts():
rows = query_db(
"SELECT status, COUNT(*) AS total FROM rooms GROUP BY status"
)
result = {status: 0 for status in ROOM_STATUSES}
for row in rows:
result[row["status"]] = row["total"]
return result
def booking_overlaps(room_id, check_in, check_out, exclude_booking_id=None):
sql = """
SELECT COUNT(*) AS n
FROM bookings
WHERE room_id = ?
AND status IN ('Đã đặt', 'Đang ở')
AND check_in < ?
AND check_out > ?
"""
params = [room_id, check_out.isoformat(), check_in.isoformat()]
if exclude_booking_id is not None:
sql += " AND id <> ?"
params.append(exclude_booking_id)return query_db(sql, tuple(params), fetchall=False)["n"] > 0
def sync_room_status(room_id):
active = query_db(
"""
SELECT status FROM bookings
WHERE room_id = ? AND status IN ('Đã đặt', 'Đang ở')
ORDER BY CASE status WHEN 'Đang ở' THEN 0 ELSE 1 END
LIMIT 1
""",
(room_id,),
fetchall=False,
)
room = query_db("SELECT status FROM rooms WHERE id = ?", (room_id,),
False)
if room is None:
return
# Không tự động xóa trạng thái bảo trì.
if room["status"] == "Bảo trì":
return
new_status = active["status"] if active else "Trống"
execute_db("UPDATE rooms SET status = ? WHERE id = ?", (new_status,
room_id))
init_database()
# =========================================================# SIDEBAR
# =========================================================
st.sidebar.title(" HOTEL MANAGER")
st.sidebar.caption("Hệ thống quản lý khách sạn")
menu = st.sidebar.radio(
"MENU",
[
" Dashboard",
" Quản lý phòng",
" Khách hàng",
" Đặt phòng",
" Nhận / Trả phòng",
" Doanh thu",
" Lịch sử đặt phòng",
],
)
st.sidebar.divider()
st.sidebar.info("Dữ liệu được lưu trong file `hotel.db` ở thư mục chạy ứng dụng.")
st.sidebar.caption(f"© {datetime.now().year} Hotel Manager")
# =========================================================
# DASHBOARD
# =========================================================
if menu == " Dashboard":
st.title(" Dashboard")
st.caption("Tổng quan hoạt động khách sạn")counts = room_status_counts()
total_rooms = sum(counts.values())
today = date.today().isoformat()
today_bookings = query_db(
"""
SELECT COUNT(*) AS total FROM bookings
WHERE date(check_in) = ? AND status IN ('Đã đặt', 'Đang ở')
""",
(today,),
False,
)["total"]
revenue = query_db(
"SELECT COALESCE(SUM(paid_amount), 0) AS total FROM bookings
WHERE status = 'Đã trả phòng'",
fetchall=False,
)["total"]
outstanding = query_db(
"""
SELECT COALESCE(SUM(total_amount - paid_amount), 0) AS total
FROM bookings WHERE status IN ('Đã đặt', 'Đang ở')
""",
fetchall=False,
)["total"]
c1, c2, c3, c4 = st.columns(4)
c1.metric(" Tổng phòng", total_rooms)
c2.metric(" Phòng trống", counts["Trống"])
c3.metric(" Đang ở", counts["Đang ở"])c4.metric(" Đã thu từ booking hoàn tất", format_money(revenue))
c1, c2, c3, c4 = st.columns(4)
c1.metric(" Nhận phòng hôm nay", today_bookings)
c2.metric(" Đã đặt", counts["Đã đặt"])
c3.metric(" Bảo trì", counts["Bảo trì"])
c4.metric(" Còn phải thu", format_money(outstanding))
st.divider()
st.subheader(" Các booking sắp tới")
upcoming = query_db(
"""
SELECT b.id, r.room_number, c.full_name, c.phone,
b.check_in, b.check_out, b.total_amount, b.paid_amount, b.status
FROM bookings b
JOIN rooms r ON b.room_id = r.id
JOIN customers c ON b.customer_id = c.id
WHERE b.check_in >= ? AND b.status IN ('Đã đặt', 'Đang ở')
ORDER BY b.check_in ASC LIMIT 10
""",
(today,),
)
if upcoming:
data = [
{
"Mã": r["id"],
"Phòng": r["room_number"],
"Khách": r["full_name"],"Điện thoại": r["phone"] or "",
"Nhận phòng": r["check_in"],
"Trả phòng": r["check_out"],
"Tổng tiền": format_money(r["total_amount"]),
"Đã trả": format_money(r["paid_amount"]),
"Trạng thái": r["status"],
}
for r in upcoming
]
st.dataframe(pd.DataFrame(data), use_container_width=True,
hide_index=True)
else:
st.info("Chưa có booking sắp tới.")
# =========================================================
# QUẢN LÝ PHÒNG
# =========================================================
elif menu == " Quản lý phòng":
st.title(" Quản lý phòng")
tab1, tab2 = st.tabs(["Danh sách phòng", "Thêm phòng"])
with tab1:
rooms = query_db("SELECT * FROM rooms ORDER BY floor, room_number")
if not rooms:
st.info("Chưa có phòng.")
for room in rooms:
icon = {"Trống": " ", "Đã đặt": " ", "Đang ở": " ", "Bảo trì":
" "}.get(room["status"], " ")with st.expander(
f"{icon} Phòng {room['room_number']} — {room['room_type']} —
{format_money(room['price'])}/đêm"
):
c1, c2, c3 = st.columns(3)
c1.write(f"**Tầng:** {room['floor']}")
c1.write(f"**Loại:** {room['room_type']}")
c2.write(f"**Giá:** {format_money(room['price'])}")
c2.write(f"**Trạng thái:** {room['status']}")
c3.write(f"**Ghi chú:** {room['note'] or '-'}")
if room["status"] not in ("Đã đặt", "Đang ở"):
with st.form(f"room_status_form_{room['id']}"):
new_status = st.selectbox(
"Trạng thái",
["Trống", "Bảo trì"],
index=0 if room["status"] == "Trống" else 1,
)
save_status = st.form_submit_button(" Cập nhật trạng thái")
if save_status:
execute_db("UPDATE rooms SET status = ? WHERE id = ?",
(new_status, room["id"]))
st.success("Đã cập nhật trạng thái phòng.")
st.rerun()
if rooms:
st.divider()
st.subheader("Bảng phòng")
st.dataframe(
pd.DataFrame([
{
"Phòng": r["room_number"],
"Loại": r["room_type"],
"Tầng": r["floor"],
"Giá/đêm": format_money(r["price"]),
"Trạng thái": r["status"],
"Ghi chú": r["note"] or "",
}
for r in rooms
]
),
use_container_width=True,
hide_index=True,
)
with tab2:
with st.form("add_room_form", clear_on_submit=True):
c1, c2 = st.columns(2)
room_number = c1.text_input("Số phòng *", placeholder="Ví dụ: 305")
room_type = c2.selectbox(
"Loại phòng",
["Phòng đơn", "Phòng đôi", "Phòng VIP", "Phòng gia đình", "Suite"],
)
floor = c1.number_input("Tầng", min_value=1, max_value=100, value=1)
price = c2.number_input("Giá phòng / đêm", min_value=0, value=500000,
step=50000)
note = st.text_area("Ghi chú")
submit = st.form_submit_button(" Thêm phòng",
use_container_width=True)if submit:
if not room_number.strip():
st.error("Vui lòng nhập số phòng.")
else:
try:
execute_db(
"""
INSERT INTO rooms (room_number, room_type, price, floor, status,
note)
VALUES (?, ?, ?, ?, 'Trống', ?)
""",
(room_number.strip(), room_type, price, floor, note.strip()),
)
st.success(f"Đã thêm phòng {room_number.strip()}.")
st.rerun()
except sqlite3.IntegrityError:
st.error("Số phòng đã tồn tại.")
# =========================================================
# KHÁCH HÀNG
# =========================================================
elif menu == " Khách hàng":
st.title(" Quản lý khách hàng")
tab1, tab2 = st.tabs(["Danh sách khách hàng", "Thêm khách hàng"])
with tab1:
search = st.text_input(" Tìm kiếm", placeholder="Tên, số điện thoại hoặc
CCCD...")if search.strip():
pattern = f"%{search.strip()}%"
customers = query_db(
"""
SELECT * FROM customers
WHERE full_name LIKE ? OR phone LIKE ? OR identity_card LIKE ?
ORDER BY id DESC
""",
(pattern, pattern, pattern),
)
else:
customers = query_db("SELECT * FROM customers ORDER BY id DESC")
st.write(f"**Tìm thấy {len(customers)} khách hàng**")
for customer in customers:
with st.expander(f" {customer['full_name']} — {customer['phone'] or 'Chưa
có SĐT'}"):
c1, c2 = st.columns(2)
c1.write(f"**Họ tên:** {customer['full_name']}")
c1.write(f"**Điện thoại:** {customer['phone'] or '-'}")
c1.write(f"**Email:** {customer['email'] or '-'}")
c2.write(f"**CCCD/CMND:** {customer['identity_card'] or '-'}")
c2.write(f"**Địa chỉ:** {customer['address'] or '-'}")
c2.write(f"**Ghi chú:** {customer['note'] or '-'}")
with tab2:
with st.form("customer_form", clear_on_submit=True):
full_name = st.text_input("Họ và tên *")
c1, c2 = st.columns(2)phone = c1.text_input("Số điện thoại")
identity_card = c1.text_input("CCCD / CMND")
email = c2.text_input("Email")
address = c2.text_input("Địa chỉ")
note = st.text_area("Ghi chú")
submit = st.form_submit_button(" Thêm khách hàng",
use_container_width=True)
if submit:
if not full_name.strip():
st.error("Vui lòng nhập họ tên.")
else:
execute_db(
"""
INSERT INTO customers (full_name, phone, email, identity_card,
address, note)
VALUES (?, ?, ?, ?, ?, ?)
""",
(full_name.strip(), phone.strip(), email.strip(), identity_card.strip(),
address.strip(), note.strip()),
)
st.success(f"Đã thêm khách hàng {full_name.strip()}.")
st.rerun()
# =========================================================
# ĐẶT PHÒNG
# =========================================================
elif menu == " Đặt phòng":
st.title(" Đặt phòng")rooms = query_db("SELECT * FROM rooms WHERE status <> 'Bảo trì' ORDER
BY room_number")
customers = query_db("SELECT * FROM customers ORDER BY full_name")
if not rooms:
st.warning("Chưa có phòng khả dụng. Hãy thêm phòng hoặc bỏ trạng thái bảo
trì.")
elif not customers:
st.warning("Chưa có khách hàng. Hãy thêm khách hàng trước khi đặt phòng.")
else:
room_options = {f"{r['room_number']} — {r['room_type']}
({format_money(r['price'])}/đêm)": r for r in rooms}
customer_options = {f"{c['full_name']} — {c['phone'] or 'Không có SĐT'}
(#{c['id']})": c for c in customers}
with st.form("booking_form"):
selected_room_label = st.selectbox("Chọn phòng", list(room_options))
selected_customer_label = st.selectbox("Chọn khách hàng",
list(customer_options))
c1, c2 = st.columns(2)
check_in = c1.date_input("Ngày nhận phòng", value=date.today())
check_out = c2.date_input("Ngày trả phòng",
value=date.today().replace(day=min(date.today().day + 1, 28)))
c1, c2 = st.columns(2)
adults = c1.number_input("Số người lớn", min_value=1, value=1, step=1)
children = c2.number_input("Số trẻ em", min_value=0, value=0, step=1)
note = st.text_area("Ghi chú")
submit = st.form_submit_button(" Xác nhận đặt phòng",
use_container_width=True)
if submit:selected_room = room_options[selected_room_label]
if check_out <= check_in:
st.error("Ngày trả phòng phải sau ngày nhận phòng.")
elif selected_room["status"] == "Bảo trì":
st.error("Phòng đang bảo trì, vui lòng chọn phòng khác.")
elif booking_overlaps(selected_room["id"], check_in, check_out):
st.error("Phòng đã có booking trùng khoảng ngày này. Vui lòng chọn
phòng khác hoặc ngày khác.")
else:
total_amount = selected_room["price"] * calculate_nights(check_in,
check_out)
customer_id = customer_options[selected_customer_label]["id"]
execute_db(
"""
INSERT INTO bookings
(room_id, customer_id, check_in, check_out, adults, children,
total_amount, paid_amount, status, note)
VALUES (?, ?, ?, ?, ?, ?, ?, 0, 'Đã đặt', ?)
""",
(
selected_room["id"],
customer_id,
check_in.isoformat(),
check_out.isoformat(),
adults,
children,
total_amount,
note.strip(),
),
)sync_room_status(selected_room["id"])
st.success(" Đặt phòng thành công!")
st.info(f"Tổng tiền: {format_money(total_amount)}")
st.rerun()
# =========================================================
# NHẬN / TRẢ PHÒNG
# =========================================================
elif menu == " Nhận / Trả phòng":
st.title(" Nhận phòng / Trả phòng")
tab1, tab2 = st.tabs(["Nhận phòng", "Trả phòng"])
with tab1:
bookings = query_db(
"""
SELECT b.*, r.room_number, r.room_type, c.full_name, c.phone
FROM bookings b
JOIN rooms r ON b.room_id = r.id
JOIN customers c ON b.customer_id = c.id
WHERE b.status = 'Đã đặt'
ORDER BY b.check_in ASC
"""
)
if not bookings:
st.info("Không có booking chờ nhận phòng.")
for booking in bookings:
with st.expander(f" Booking #{booking['id']} — Phòng
{booking['room_number']} — {booking['full_name']}"):c1, c2, c3 = st.columns(3)
c1.write(f"**Khách:** {booking['full_name']}")
c1.write(f"**SĐT:** {booking['phone'] or '-'}")
c2.write(f"**Phòng:** {booking['room_number']}")
c2.write(f"**Nhận:** {booking['check_in']}")
c2.write(f"**Trả:** {booking['check_out']}")
c3.write(f"**Tổng:** {format_money(booking['total_amount'])}")
c3.write(f"**Đã trả:** {format_money(booking['paid_amount'])}")
c3.write(f"**Còn lại:** {format_money(booking['total_amount'] -
booking['paid_amount'])}")
if st.button(" Xác nhận nhận phòng", key=f"checkin_{booking['id']}"):
execute_db("UPDATE bookings SET status = 'Đang ở' WHERE id = ?",
(booking["id"],))
execute_db("UPDATE rooms SET status = 'Đang ở' WHERE id = ?",
(booking["room_id"],))
st.success(f"Đã nhận phòng {booking['room_number']}.")
st.rerun()
with tab2:
active_bookings = query_db(
"""
SELECT b.*, r.room_number, r.room_type, c.full_name, c.phone
FROM bookings b
JOIN rooms r ON b.room_id = r.id
JOIN customers c ON b.customer_id = c.id
WHERE b.status = 'Đang ở'
ORDER BY b.check_out ASC
"""
)
if not active_bookings:st.info("Không có khách đang ở.")
for booking in active_bookings:
with st.expander(f" Phòng {booking['room_number']} —
{booking['full_name']}"):
total = booking["total_amount"]
paid = booking["paid_amount"]
remaining = max(total - paid, 0)
c1, c2, c3 = st.columns(3)
c1.write(f"**Khách:** {booking['full_name']}")
c1.write(f"**SĐT:** {booking['phone'] or '-'}")
c2.write(f"**Ngày nhận:** {booking['check_in']}")
c2.write(f"**Ngày trả dự kiến:** {booking['check_out']}")
c3.write(f"**Tổng tiền:** {format_money(total)}")
c3.write(f"**Đã thanh toán:** {format_money(paid)}")
c3.write(f"**Còn lại:** {format_money(remaining)}")
payment = st.number_input(
"Thanh toán thêm",
min_value=0.0,
max_value=float(remaining),
value=float(remaining),
step=50000.0,
key=f"payment_{booking['id']}",
)
if st.button(" Thanh toán & trả phòng", key=f"checkout_{booking['id']}"):
new_paid = paid + payment
execute_db(
"UPDATE bookings SET paid_amount = ?, status = 'Đã trả phòng'
WHERE id = ?",
(new_paid, booking["id"]),)
execute_db("UPDATE rooms SET status = 'Trống' WHERE id = ?",
(booking["room_id"],))
st.success(f"Đã trả phòng {booking['room_number']}.")
st.rerun()
# =========================================================
# DOANH THU
# =========================================================
elif menu == " Doanh thu":
st.title(" Doanh thu")
c1, c2 = st.columns(2)
from_date = c1.date_input("Từ ngày", value=date.today().replace(day=1))
to_date = c2.date_input("Đến ngày", value=date.today())
if from_date > to_date:
st.error("Khoảng ngày không hợp lệ.")
else:
params = (from_date.isoformat(), to_date.isoformat())
summary = query_db(
"""
SELECT COUNT(*) AS bookings,
COALESCE(SUM(total_amount), 0) AS total,
COALESCE(SUM(paid_amount), 0) AS paid,
COALESCE(SUM(total_amount - paid_amount), 0) AS remaining
FROM bookings
WHERE date(created_at) BETWEEN ? AND ? AND status = 'Đã trả phòng'
""",params,
False,
)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Booking", summary["bookings"])
c2.metric("Doanh thu", format_money(summary["total"]))
c3.metric("Đã thu", format_money(summary["paid"]))
c4.metric("Còn thiếu", format_money(summary["remaining"]))
st.divider()
st.subheader("Chi tiết doanh thu")
rows = query_db(
"""
SELECT b.id, r.room_number, c.full_name, b.check_in, b.check_out,
b.total_amount, b.paid_amount, b.created_at
FROM bookings b
JOIN rooms r ON b.room_id = r.id
JOIN customers c ON b.customer_id = c.id
WHERE date(b.created_at) BETWEEN ? AND ? AND b.status = 'Đã trả
phòng'
ORDER BY b.created_at DESC
""",
params,
)
if rows:
st.dataframe(
pd.DataFrame(
[
{"Booking": r["id"],
"Phòng": r["room_number"],
"Khách": r["full_name"],
"Nhận phòng": r["check_in"],
"Trả phòng": r["check_out"],
"Tổng tiền": format_money(r["total_amount"]),
"Đã thu": format_money(r["paid_amount"]),
"Ngày tạo": r["created_at"],
}
for r in rows
]
),
use_container_width=True,
hide_index=True,
)
else:
st.info("Không có doanh thu trong khoảng ngày đã chọn.")
# =========================================================
# LỊCH SỬ ĐẶT PHÒNG
# =========================================================
elif menu == " Lịch sử đặt phòng":
st.title(" Lịch sử đặt phòng")
search = st.text_input("Tìm theo tên khách hoặc số phòng")
status_filter = st.selectbox("Lọc trạng thái", ["Tất cả"] + BOOKING_STATUSES)
sql = """
SELECT b.*, r.room_number, r.room_type, c.full_name, c.phoneFROM bookings b
JOIN rooms r ON b.room_id = r.id
JOIN customers c ON b.customer_id = c.id
WHERE 1 = 1
"""
params = []
if search.strip():
pattern = f"%{search.strip()}%"
sql += " AND (c.full_name LIKE ? OR r.room_number LIKE ?)"
params.extend([pattern, pattern])
if status_filter != "Tất cả":
sql += " AND b.status = ?"
params.append(status_filter)
sql += " ORDER BY b.created_at DESC, b.id DESC"
bookings = query_db(sql, tuple(params))
if bookings:
st.dataframe(
pd.DataFrame(
[
{
"Mã booking": b["id"],
"Phòng": b["room_number"],
"Khách hàng": b["full_name"],
"Điện thoại": b["phone"] or "",
"Nhận phòng": b["check_in"],
"Trả phòng": b["check_out"],
"Người lớn": b["adults"],
"Trẻ em": b["children"],"Tổng tiền": format_money(b["total_amount"]),
"Đã thanh toán": format_money(b["paid_amount"]),
"Trạng thái": b["status"],
"Ghi chú": b["note"] or "",
}
for b in bookings
]
),
use_container_width=True,
hide_index=True,
)
st.divider()
st.subheader("Chi tiết booking")
booking_ids = [b["id"] for b in bookings]
selected_id = st.selectbox("Chọn mã booking", booking_ids)
selected = next(b for b in bookings if b["id"] == selected_id)
c1, c2, c3 = st.columns(3)
c1.write(f"**Khách hàng:** {selected['full_name']}")
c1.write(f"**Điện thoại:** {selected['phone'] or '-'}")
c2.write(f"**Phòng:** {selected['room_number']}")
c2.write(f"**Loại:** {selected['room_type']}")
c3.write(f"**Trạng thái:** {selected['status']}")
c3.write(f"**Ngày tạo:** {selected['created_at']}")
st.write(f"**Ghi chú:** {selected['note'] or '-'}")
else:
st.info("Không tìm thấy booking phù hợp.")
