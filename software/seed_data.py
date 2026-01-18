import calendar
import random
import sqlite3
from datetime import datetime, timedelta

from config import Config

DATABASE = Config.DATABASE_PATH

# === CẤU HÌNH DỮ LIỆU ĐẸP ===
PROVINCES = [29, 30, 31, 32, 14, 15, 90, 18, 36, 37]
CHARS = "ABCDEFGHKLMNPSTVXYZ"

def generate_vietnam_plate():
    """Sinh biển số xe chuẩn format Việt Nam (VD: 30A-123.45)"""
    province = random.choice(PROVINCES)
    char = random.choice(CHARS)
    
    if random.random() > 0.2:
        num1 = random.randint(100, 999)
        num2 = random.randint(10, 99)
        return f"{province}{char}-{num1}.{num2}"
    else:
        num = random.randint(1000, 9999)
        return f"{province}{char}-{num}"

def generate_hex_card_id():
    """
    Sinh mã thẻ RFID dạng Hex chuẩn (4 byte), ví dụ: '4E 12 AB F9'.
    Đây là định dạng phổ biến của các loại thẻ từ gửi xe.
    """
    # Sinh 4 số ngẫu nhiên từ 0-255 (1 byte)
    bytes_list = [random.randint(0, 255) for _ in range(4)]
    # Format thành chuỗi Hex in hoa, nối bằng dấu cách
    return " ".join(f"{b:02X}" for b in bytes_list)

def add_months(base_date, months):
    month = base_date.month - 1 + months
    year = base_date.year + month // 12
    month = month % 12 + 1
    day = min(base_date.day, calendar.monthrange(year, month)[1])
    return base_date.replace(year=year, month=month, day=day)

def get_settings(cursor):
    """Lấy giá vé hiện tại"""
    settings = {}
    try:
        cursor.execute("SELECT key, value FROM settings")
        for row in cursor.fetchall():
            settings[row[0]] = int(row[1])
    except:
        pass
    return settings

# Danh sách các mã thẻ VIP cố định (để tiện dọn dẹp và theo dõi)
VIP_CARDS = [
    ("E4 1A 9B F1", "Nguyễn Văn Giám Đốc", "30H-888.88"),
    ("C2 5D 88 AA", "Trần Thị Trưởng Phòng", "29A-678.99"),
    ("9F 12 33 4C", "Lê Văn Nhân Viên", "18B-123.45"),
    ("B1 00 5E 7F", "Phạm Thị Thư Ký", "90A-555.55"),
]

def seed_monthly_payments(cursor, monthly_fee, month_count=6):
    """Sinh dữ liệu vé tháng 'đẹp'"""
    print(f"   + Tạo dữ liệu vé tháng cho {month_count} tháng gần nhất...")

    now = datetime.now()
    
    for card_id, holder, plate in VIP_CARDS:
        # Tạo thẻ (còn hạn dài)
        created_at = (now - timedelta(days=200)).strftime("%Y-%m-%d %H:%M:%S")
        expiry_date = add_months(now, 1).strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute("""
            INSERT OR REPLACE INTO cards (card_id, holder_name, license_plate, ticket_type, expiry_date, created_at, status)
            VALUES (?, ?, ?, 'monthly', ?, ?, 'active')
        """, (card_id, holder, plate, expiry_date, created_at))

        # Tạo lịch sử đóng tiền từng tháng
        start_month = now.replace(day=1)
        for i in range(month_count):
            month_iter = start_month.month - i
            year_iter = start_month.year
            while month_iter <= 0:
                month_iter += 12
                year_iter -= 1
            
            month_label = f"{year_iter:04d}-{month_iter:02d}"
            
            paid_day = random.randint(1, 5)
            paid_at = datetime(year_iter, month_iter, paid_day, random.randint(8, 17), random.randint(0, 59))
            
            cursor.execute("""
                INSERT INTO monthly_payments (card_id, month, amount, paid_at)
                VALUES (?, ?, ?, ?)
            """, (card_id, month_label, monthly_fee, paid_at.strftime("%Y-%m-%d %H:%M:%S")))

def create_beautiful_data():
    print(f"=== BẮT ĐẦU TẠO DỮ LIỆU MẪU (HEX CARD ID VERSION) ===")
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # 1. Dọn dẹp dữ liệu cũ
    print("1. Dọn dẹp dữ liệu seed cũ...")
    # Xóa giao dịch giả
    cursor.execute("DELETE FROM transactions WHERE security_user = 'dieptb'")
    
    # Xóa thẻ VIP và lịch sử thanh toán của chúng (dựa trên danh sách VIP_CARDS)
    vip_ids = tuple(item[0] for item in VIP_CARDS)
    cursor.execute(f"DELETE FROM cards WHERE card_id IN {vip_ids}")
    cursor.execute(f"DELETE FROM monthly_payments WHERE card_id IN {vip_ids}")

    # Xóa dọn sạch các dữ liệu cũ định dạng khác nếu còn sót
    cursor.execute("DELETE FROM cards WHERE card_id LIKE 'MONTH_VIP_%' OR card_id LIKE 'FAKE_%'")
    cursor.execute("DELETE FROM monthly_payments WHERE card_id LIKE 'MONTH_VIP_%'")
    
    conn.commit()

    # 2. Lấy cấu hình giá
    settings = get_settings(cursor)
    hourly_fee = settings.get('fee_per_hour', 5000)
    monthly_fee = settings.get('monthly_fee', 1500000)
    print(f"   -> Giá vé: {hourly_fee:,}đ/h | Vé tháng: {monthly_fee:,}đ/tháng")

    # 3. Sinh giao dịch vãng lai
    print("2. Đang sinh hàng trăm giao dịch xe ra vào...")
    total_records = 0
    days_back = 5 

    for i in range(days_back, -1, -1):
        current_date = datetime.now() - timedelta(days=i)
        is_weekend = current_date.weekday() >= 5
        daily_cars = random.randint(15, 30) if not is_weekend else random.randint(30, 50)

        for _ in range(daily_cars):
            # Logic giờ giấc
            rand_val = random.random()
            if rand_val < 0.3:
                hour_in = random.randint(7, 9)
            elif rand_val < 0.6:
                hour_in = random.randint(13, 15)
            else:
                hour_in = random.randint(7, 21)

            minute_in = random.randint(0, 59)
            entry_time = current_date.replace(hour=hour_in, minute=minute_in, second=random.randint(0, 59))

            # Logic thời gian gửi
            if random.random() < 0.7:
                duration_minutes = random.randint(30, 120)
            else:
                duration_minutes = random.randint(240, 540)

            exit_time = entry_time + timedelta(minutes=duration_minutes)
            if exit_time > datetime.now():
                continue

            fee = max(1, -(-duration_minutes // 60)) * hourly_fee
            plate = generate_vietnam_plate()
            
            # SỬ DỤNG MÃ THẺ HEX MỚI (Mỗi lượt xe vãng lai dùng 1 thẻ khác nhau)
            card_id = generate_hex_card_id()

            cursor.execute("""
                INSERT INTO transactions 
                (card_id, license_plate, entry_time, exit_time, fee, entry_snapshot, exit_snapshot, security_user)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                card_id,
                plate,
                entry_time.strftime("%Y-%m-%d %H:%M:%S"),
                exit_time.strftime("%Y-%m-%d %H:%M:%S"),
                fee,
                "placeholder.jpg",
                "placeholder.jpg",
                "dieptb"
            ))
            total_records += 1

    # 4. Sinh dữ liệu vé tháng
    seed_monthly_payments(cursor, monthly_fee)

    conn.commit()
    conn.close()
    print(f"=== HOÀN TẤT! Đã thêm {total_records} giao dịch. ===")

if __name__ == '__main__':
    create_beautiful_data()