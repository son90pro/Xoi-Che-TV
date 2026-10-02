from datetime import datetime
import json
import re
import requests

BASE_DOMAIN = "https://xoiche.live"
INITIAL_API_URL = f"{BASE_DOMAIN}/api/matches/?ordering=smart&page_size=36&page=1&site=xoiche&has_stream=true"

HEADERS = {
    "X-Site-Id": "xoiche",
    "X-Site": "xoiche",
    "X-Client-Transport": "obfuscated",
    "Accept": "application/x-obfuscated, application/json, text/plain, */*",
    "Content-Type": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
        " like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
}


def fix_url(url):
    """Chuẩn hóa đường dẫn URL (xử lý link tương đối /media/...)"""
    if not url:
        return ""
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        return BASE_DOMAIN + url
    return url


def format_match_time(time_str):
    """Chuyển định dạng ISO sang HH:MM DD/MM"""
    if not time_str:
        return ""
    try:
        # Xử lý ISO format từ API (ví dụ: 2026-10-02T13:00:00+07:00)
        dt = datetime.fromisoformat(time_str)
        return dt.strftime("%H:%M %d/%m")
    except Exception:
        return ""


def fetch_all_matches():
    """Lấy toàn bộ trận đấu qua tất cả các trang API"""
    matches = []
    current_url = INITIAL_API_URL

    while current_url:
        try:
            response = requests.get(current_url, headers=HEADERS, timeout=15)
            if response.status_code != 200:
                print(f"Lỗi API HTTP {response.status_code}")
                break

            data = response.json()
            results = data.get("results", [])
            matches.extend(results)

            # Lấy URL trang tiếp theo nếu có
            next_page = data.get("next")
            if next_page:
                current_url = fix_url(next_page)
            else:
                current_url = None
        except Exception as e:
            print(f"Lỗi khi tải dữ liệu: {e}")
            break

    return matches


def build_m3u_playlist(matches):
    """Tạo nội dung M3U chuẩn định dạng như hình mẫu"""
    m3u_lines = ["#EXTM3U"]

    for match in matches:
        # Lấy thông tin môn thể thao
        sport_info = match.get("sport") or {}
        sport_name = (
            match.get("sport_name")
            or sport_info.get("name")
            or "Thể Thao Khác"
        )
        sport_icon = (
            sport_info.get("icon") or "⚽" if "Bóng đá" in sport_name else "🏐"
        )

        # Lấy thông tin thời gian & đội bóng
        time_formatted = format_match_time(match.get("start_time"))
        home_team = match.get("home_team_name") or "Đội nhà"
        away_team = match.get("away_team_name") or "Đội khách"

        # Lấy logo đội nhà (ưu tiên flag/logo)
        logo_url = fix_url(
            match.get("home_team_logo")
            or (match.get("home_team") or {}).get("logo")
        )

        # Lấy tất cả luồng stream / BLV
        commentator_streams = match.get("commentator_streams") or []

        # Nếu không có luồng BLV riêng, kiểm tra luồng mặc định của trận
        if not commentator_streams:
            primary = match.get("primary_stream_url")
            backup = match.get("backup_stream_url")
            if primary or backup:
                commentator_streams = [{
                    "stream_url": primary or backup,
                    "commentator": {"name": "Nhà Đài"},
                }]

        for idx, stream_item in enumerate(commentator_streams, 1):
            stream_url = stream_item.get("stream_url") or stream_item.get(
                "backup_stream_url"
            )
            if not stream_url:
                continue

            # Chuẩn hóa URL stream nếu là đường dẫn tương đối
            stream_url = fix_url(stream_url)

            # Lấy tên BLV
            comm_info = stream_item.get("commentator") or {}
            comm_name = (
                comm_info.get("name")
                or stream_item.get("commentator_name")
                or "Nhà Đài"
            )

            # Chất lượng luồng (Mặc định FHD như mẫu)
            quality_label = "[FHD]"

            # Format tên hiển thị chuẩn như trong hình mẫu:
            # 13:00 02/10 ⚽ China W vs South Korea W (Gà Rừng BLV) [FHD]
            title_display = f"{time_formatted} {sport_icon} {home_team} vs {away_team} ({comm_name}) {quality_label}"

            # Ghép thẻ M3U
            extinf = f'#EXTINF:-1 tvg-logo="{logo_url}" group-title="{sport_name}",{title_display}'
            m3u_lines.append(extinf)
            m3u_lines.append(stream_url)

    return "\n".join(m3u_lines)


def main():
    print("Đang lấy danh sách trận đấu từ xoiche.live...")
    matches = fetch_all_matches()
    print(f"Đã tìm thấy {len(matches)} trận đấu.")

    playlist_content = build_m3u_playlist(matches)

    # Xuất ra file playlist.m3u
    output_filename = "xoiche.m3u"
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(playlist_content)

    print(f"Đã tạo file {output_filename} thành công!")


if __name__ == "__main__":
    main()
  
