import json
import time
from datetime import datetime
from curl_cffi import requests as curl_requests

BASE_DOMAIN = "https://xoiche2.live"
INITIAL_API_URL = f"{BASE_DOMAIN}/api/matches/?ordering=smart&page_size=36&page=1&site=xoiche&has_stream=true"

# Header chuẩn giả lập duyệt web tự nhiên
HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://xoiche2.live/",
    "Origin": "https://xoiche2.live",
    "X-Site-Id": "xoiche",
    "X-Site": "xoiche",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
}


def fix_url(url):
    if not url:
        return ""
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        return BASE_DOMAIN + url
    return url


def format_match_time(time_str):
    if not time_str:
        return ""
    try:
        dt = datetime.fromisoformat(time_str)
        return dt.strftime("%H:%M %d/%m")
    except Exception:
        return ""


def fetch_all_matches():
    matches = []
    current_url = INITIAL_API_URL

    # Khởi tạo Session giả lập trình duyệt Chrome
    session = curl_requests.Session(impersonate="chrome120")

    # BƯỚC 1: Truy cập trang chủ trước để lấy Cookie Session từ Cloudflare
    print("Đang khởi tạo phiên truy cập trang chủ xoiche2.live...", flush=True)
    try:
        init_res = session.get(
            f"{BASE_DOMAIN}/", headers=HEADERS, timeout=15
        )
        print(
            f"-> Trang chủ trả về HTTP {init_res.status_code}, đã nhận Session"
            " Cookie.",
            flush=True,
        )
        time.sleep(2)  # Chờ 2 giây tạo độ trễ như người dùng thật
    except Exception as e:
        print(f"Lỗi khi khởi tạo Session: {e}", flush=True)

    # BƯỚC 2: Gọi API lấy toàn bộ danh sách trận đấu
    while current_url:
        print(f"Đang tải API: {current_url}", flush=True)
        try:
            res = session.get(current_url, headers=HEADERS, timeout=20)

            if res.status_code != 200:
                print(
                    f"Lỗi API HTTP {res.status_code}. Phản hồi:"
                    f" {res.text[:200]}",
                    flush=True,
                )
                break

            try:
                data = res.json()
            except json.JSONDecodeError:
                print(
                    "Lỗi Decode JSON! Đoạn dữ liệu nhận được:",
                    flush=True,
                )
                print(f"Text (200 ký tự): {res.text[:200]}", flush=True)
                break

            results = data.get("results", [])
            print(f"-> Lấy được {len(results)} trận ở trang này.", flush=True)
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
    m3u_lines = ["#EXTM3U"]

    for match in matches:
        sport_info = match.get("sport") or {}
        sport_name = (
            match.get("sport_name")
            or sport_info.get("name")
            or "Thể Thao Khác"
        )
        sport_icon = (
            sport_info.get("icon") or ("⚽" if "Bóng đá" in sport_name else "🏐")
        )

        time_formatted = format_match_time(match.get("start_time"))
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
            stream_url = stream_item.get("stream_url") or stream_item.get(
                "backup_stream_url"
            )
            if not stream_url:
                continue

            stream_url = fix_url(stream_url)

            comm_info = stream_item.get("commentator") or {}
            comm_name = (
                comm_info.get("name")
                or stream_item.get("commentator_name")
                or "Nhà Đài"
            )

            quality_label = "[FHD]"
            title_display = f"{time_formatted} {sport_icon} {home_team} vs {away_team} ({comm_name}) {quality_label}"

            extinf = f'#EXTINF:-1 tvg-logo="{logo_url}" group-title="{sport_name}",{title_display}'
            m3u_lines.append(extinf)
            m3u_lines.append(stream_url)

    return "\n".join(m3u_lines)


def main():
    print("Đang lấy danh sách trận đấu từ xoiche2.live...", flush=True)
    matches = fetch_all_matches()
    print(f"Tổng cộng đã tìm thấy {len(matches)} trận đấu.", flush=True)

    if not matches:
        print("Cảnh báo: Không lấy được trận đấu nào!", flush=True)

    playlist_content = build_m3u_playlist(matches)

    output_filename = "xoiche.m3u"
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(playlist_content)

    print(f"Đã tạo file {output_filename} thành công!", flush=True)


if __name__ == "__main__":
    main()
    
