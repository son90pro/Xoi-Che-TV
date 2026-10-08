from datetime import datetime
import json
from curl_cffi import requests as curl_requests

BASE_DOMAIN = "https://xoiche2.live"
INITIAL_API_URL = f"{BASE_DOMAIN}/api/matches/?ordering=smart&page_size=36&page=1&site=xoiche&has_stream=true"

HEADERS = {
    "X-Site-Id": "xoiche",
    "X-Site": "xoiche",
    "X-Client-Transport": "obfuscated",
    "Accept": "application/x-obfuscated, application/json, text/plain, */*",
    "Content-Type": "application/json",
    "Referer": "https://xoiche2.live/",
    "Origin": "https://xoiche2.live",
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

    while current_url:
        print(f"Đang tải: {current_url}", flush=True)
        try:
            # Dùng impersonate="chrome120" để giả lập TLS fingerprint Chrome thật
            res = curl_requests.get(
                current_url,
                headers=HEADERS,
                impersonate="chrome120",
                timeout=20,
            )

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
                    "Lỗi: Server vẫn trả về HTML/Cloudflare thay vì JSON.",
                    flush=True,
                )
                print(
                    f"Nội dung phản hồi (300 ký tự): {res.text[:300]}",
                    flush=True,
                )
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
    
