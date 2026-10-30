from datetime import datetime, timedelta, timezone
import json
import time
from curl_cffi import requests as curl_requests

BASE_DOMAIN = "https://xoiche3.live"
INITIAL_API_URL = f"{BASE_DOMAIN}/api/matches/?ordering=smart&page_size=36&page=1&site=xoiche&has_commentator=true"

# Headers tối giản nhận JSON thuần
HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": f"{BASE_DOMAIN}/",
    "Origin": BASE_DOMAIN,
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
}

# Danh sách thứ tự ưu tiên các tab thể thao
SPORT_ORDER = [
    "Bóng đá",
    "Bóng chuyền",
    "Bóng rổ",
    "Bóng bàn",
    "Cầu lông",
    "Bi a",
    "Sports Games"
]

def fix_url(url):
    if not url:
        return ""
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        if url.startswith("/live/"):
            return "https://live.khoga.space" + url
        return BASE_DOMAIN + url
    return url

def format_match_time(time_str):
    if not time_str:
        return "", None
    try:
        # Xử lý chuỗi thời gian ISO sang datetime object (UTC hoặc chuẩn giờ)
        dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        # Quy đổi sang giờ Việt Nam (UTC+7) nếu cần thiết, hoặc giữ nguyên tùy API trả về
        # Ở đây giả định so sánh trực tiếp múi giờ hệ thống / UTC tương ứng
        formatted_str = dt.strftime("%H:%M %d/%m")
        return formatted_str, dt
    except Exception:
        return "", None

def is_today_or_tomorrow(dt):
    """Kiểm tra trận đấu có nằm trong hôm nay hoặc ngày mai không (theo giờ VN / UTC+7)"""
    if not dt:
        return False
    
    # Lấy giờ hiện tại theo múi giờ VN (UTC+7)
    vn_tz = timezone(timedelta(hours=7))
    now_vn = datetime.now(vn_tz)
    
    # Chuyển dt sang múi giờ VN nếu có info timezone
    if dt.tzinfo is not None:
        dt_vn = dt.astimezone(vn_tz)
    else:
        dt_vn = dt.replace(tzinfo=vn_tz)
        
    start_today = now_vn.replace(hour=0, minute=0, second=0, microsecond=0)
    end_tomorrow = start_today + timedelta(days=2) # Hết ngày mai (tính đến 23:59 ngày mai)
    
    # Cho phép giữ lại các trận đang diễn ra sớm hơn một chút hoặc từ đầu ngày hôm nay đến hết ngày mai
    return start_today <= dt_vn < end_tomorrow

def fetch_all_matches():
    matches = []
    current_url = INITIAL_API_URL

    session = curl_requests.Session(impersonate="chrome120")

    print("Đang khởi tạo phiên truy cập trang chủ xoiche3.live...", flush=True)
    try:
        init_res = session.get(f"{BASE_DOMAIN}/", headers=HEADERS, timeout=15)
        print(f"Trang chủ status: {init_res.status_code}", flush=True)
        time.sleep(1)
    except Exception as e:
        print(f"Không thể kết nối trang chủ: {e}", flush=True)

    while current_url:
        print(f"Đang tải API: {current_url}", flush=True)
        try:
            res = session.get(current_url, headers=HEADERS, timeout=20)

            if res.status_code != 200:
                print(f"Lỗi HTTP {res.status_code}", flush=True)
                break

            try:
                data = res.json()
            except Exception as e:
                print(f"Không thể parse JSON: {e}", flush=True)
                break

            results = data.get("results", [])
            print(f"-> Lấy thành công {len(results)} trận từ trang.", flush=True)
            matches.extend(results)

            next_page = data.get("next")
            if next_page:
                current_url = fix_url(next_page)
            else:
                current_url = None
        except Exception as e:
            print(f"Lỗi khi tải dữ liệu: {e}", flush=True)
            break

    return matches

def build_m3u_playlist(matches):
    # Gom nhóm theo tên môn thể thao
    categorized_matches = {sport: [] for sport in SPORT_ORDER}
    seen_ids = set()

    for match in matches:
        match_id = match.get("id")
        if match_id in seen_ids:
            continue
        
        time_str = match.get("start_time")
        time_formatted, dt_obj = format_match_time(time_str)
        
        # Lọc chỉ lấy trận hôm nay và ngày mai
        if not is_today_or_tomorrow(dt_obj):
            continue
            
        seen_ids.add(match_id)

        sport_info = match.get("sport") or {}
        raw_sport_name = match.get("sport_name") or sport_info.get("name") or "Bóng đá"
        
        # Chuẩn hóa tên môn thể thao khớp với các tab định sẵn
        sport_name = "Bóng đá"
        lower_name = raw_sport_name.lower()
        if "chuyền" in lower_name:
            sport_name = "Bóng chuyền"
        elif "rổ" in lower_name:
            sport_name = "Bóng rổ"
        elif "bàn" in lower_name:
            sport_name = "Bóng bàn"
        elif "cầu lông" in lower_name:
            sport_name = "Cầu lông"
        elif "bi a" in lower_name or "bida" in lower_name or "pool" in lower_name:
            sport_name = "Bi a"
        elif "game" in lower_name or "esports" in lower_name:
            sport_name = "Sports Games"

        if sport_name not in categorized_matches:
            categorized_matches[sport_name] = []

        sport_icon = sport_info.get("icon") or ("⚽" if sport_name == "Bóng đá" else "📺")
        home_team = match.get("home_team_name") or "Đội nhà"
        away_team = match.get("away_team_name") or "Đội khách"

        logo_url = fix_url(
            match.get("home_team_logo")
            or (match.get("home_team") or {}).get("logo")
        )

        commentator_streams = match.get("commentator_streams") or []
        if not commentator_streams:
            primary = match.get("primary_stream_url")
            backup = match.get("backup_stream_url")
            if primary or backup:
                commentator_streams = [{
                    "stream_url": primary or backup,
                    "commentator": {"name": "Nhà Đài"},
                }]

        for stream_item in commentator_streams:
            stream_url = stream_item.get("stream_url") or stream_item.get("backup_stream_url")
            if not stream_url:
                continue

            stream_url = fix_url(stream_url)
            comm_info = stream_item.get("commentator") or {}
            comm_name = comm_info.get("name") or stream_item.get("commentator_name") or "Nhà Đài"

            quality_label = "[FHD]"
            title_display = f"{time_formatted} {sport_icon} {home_team} vs {away_team} ({comm_name}) {quality_label}"

            extinf = f'#EXTINF:-1 tvg-logo="{logo_url}" group-title="{sport_name}",{title_display}'
            
            # Lưu trữ theo cấu trúc để sắp xếp thứ tự tab
            categorized_matches[sport_name].append((extinf, stream_url))

    # Xây dựng nội dung file M3U theo đúng thứ tự ưu tiên các tab
    m3u_lines = ["#EXTM3U"]
    for sport in SPORT_ORDER:
        items = categorized_matches.get(sport, [])
        for extinf, stream_url in items:
            m3u_lines.append(extinf)
            m3u_lines.append(stream_url)

    return "\n".join(m3u_lines)

def main():
    print("Đang lọc và lấy danh sách trận đấu hôm nay và ngày mai...", flush=True)
    matches = fetch_all_matches()
    print(f"Tổng số trận sau khi lọc lịch hôm nay & ngày mai: {len(matches)} trận.", flush=True)

    playlist_content = build_m3u_playlist(matches)
    with open("xoiche.m3u", "w", encoding="utf-8") as f:
        f.write(playlist_content)

    print("Đã cập nhật file xoiche.m3u thành công với các tab phân loại chuẩn xác!", flush=True)

if __name__ == "__main__":
    main()
    
