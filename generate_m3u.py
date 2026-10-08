from datetime import datetime
import json
import time
from curl_cffi import requests as curl_requests

# Danh sách domain quét tự động
DOMAINS = ["https://xoiche.live", "https://xoiche2.live"]

# Header tối giản y hệt lệnh fetch() trên trình duyệt (đã xóa sạch X-Site & X-Client-Transport)
HEADERS = {
    "Accept": "*/*",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
}


def fix_url(url, domain):
    if not url:
        return ""
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        if url.startswith("/live/"):
            return "https://live.khoga.space" + url
        return domain + url
    return url


def format_match_time(time_str):
    if not time_str:
        return ""
    try:
        dt = datetime.fromisoformat(time_str)
        return dt.strftime("%H:%M %d/%m")
    except Exception:
        return ""


def fetch_matches_from_domain(domain):
    matches = []
    api_url = f"{domain}/api/matches/?ordering=smart&page_size=36&page=1&site=xoiche&has_stream=true"

    headers = HEADERS.copy()
    headers["Referer"] = f"{domain}/"
    headers["Origin"] = domain

    # Giả lập trình duyệt Chrome để qua mặt Cloudflare
    session = curl_requests.Session(impersonate="chrome120")

    print(f"\n--- Đang thử domain: {domain} ---", flush=True)
    try:
        init_res = session.get(f"{domain}/", headers=headers, timeout=15)
        print(f"Trang chủ status: {init_res.status_code}", flush=True)
        time.sleep(1)
    except Exception as e:
        print(f"Không thể kết nối {domain}: {e}", flush=True)
        return []

    current_url = api_url
    while current_url:
        print(f"Đang tải API: {current_url}", flush=True)
        try:
            res = session.get(current_url, headers=headers, timeout=20)

            if res.status_code != 200:
                print(f"Lỗi HTTP {res.status_code}", flush=True)
                break

            try:
                data = res.json()
            except Exception as e:
                print(f"Lỗi parse JSON: {e}", flush=True)
                print(
                    f"Nội dung nhận được (100 ký tự đầu): {res.text[:100]}",
                    flush=True,
                )
                break

            results = data.get("results", [])
            print(f"-> Lấy thành công {len(results)} trận.", flush=True)
            matches.extend(results)

            next_page = data.get("next")
            if next_page:
                current_url = fix_url(next_page, domain)
            else:
                current_url = None
        except Exception as e:
            print(f"Lỗi request: {e}", flush=True)
            break

    return matches


def build_m3u_playlist(matches):
    m3u_lines = ["#EXTM3U"]
    seen_ids = set()

    for match in matches:
        match_id = match.get("id")
        if match_id in seen_ids:
            continue
        seen_ids.add(match_id)

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
            or (match.get("home_team") or {}).get("logo"),
            "https://xoiche2.live",
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

            stream_url = fix_url(stream_url, "https://xoiche2.live")

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
    all_matches = []
    for domain in DOMAINS:
        matches = fetch_matches_from_domain(domain)
        if matches:
            all_matches.extend(matches)
            break

    print(f"\nTổng cộng đã tìm thấy {len(all_matches)} trận đấu.", flush=True)

    playlist_content = build_m3u_playlist(all_matches)
    with open("xoiche.m3u", "w", encoding="utf-8") as f:
        f.write(playlist_content)

    print("Đã tạo file xoiche.m3u thành công!", flush=True)


if __name__ == "__main__":
    main()
    
