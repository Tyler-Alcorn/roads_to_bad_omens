import csv
import re
from datetime import datetime, timedelta
from lxml import html
import json
import os

# Paths
BASE_DIR = "/Volumes/Dock/roads_to_bad_omens"
MUSIC_LIBRARY_PATH = os.path.join(BASE_DIR, "Takeout/YouTube and YouTube Music/music (library and uploads)/music library songs.csv")
WATCH_HISTORY_PATH = os.path.join(BASE_DIR, "Takeout/YouTube and YouTube Music/history/watch-history.html")
OUTPUT_REPORT_PATH = os.path.join(BASE_DIR, "music_session_report.txt")
OUTPUT_JSON_PATH = os.path.join(BASE_DIR, "music_session_transitions.json")

SESSION_GAP_MINUTES = 30

def parse_timestamp(ts_str):
    # Remove the narrow non-breaking space (U+202F) if present
    ts_str = ts_str.replace('\u202f', ' ')
    # Format: Feb 24, 2026, 4:00:14 PM PST
    # Note: timezone might stay as PST/PDT etc. simplified parsing for now
    try:
        # Try without timezone first, or handle common ones
        clean_ts = re.sub(r'\s[A-Z]{3,4}$', '', ts_str)
        return datetime.strptime(clean_ts, "%b %d, %r") # %r is locale's appropriate 12-hour clock time
    except:
        try:
             # Feb 24, 2026, 4:00:14 PM
             return datetime.strptime(clean_ts, "%b %d, %Y, %I:%M:%S %p")
        except Exception as e:
            print(f"Failed to parse timestamp: {ts_str} -> {e}")
            return None

def get_video_id(url):
    match = re.search(r'v=([^&]+)', url)
    return match.group(1) if match else None

def main():
    print("Loading music library...")
    video_to_artist = {}
    if os.path.exists(MUSIC_LIBRARY_PATH):
        with open(MUSIC_LIBRARY_PATH, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                v_id = row.get('Video ID')
                artist = row.get('Artist Name 1')
                if v_id and artist:
                    video_to_artist[v_id] = artist
    print(f"Loaded {len(video_to_artist)} songs from library.")

    print("Parsing watch history (this may take a moment)...")
    with open(WATCH_HISTORY_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    tree = html.fromstring(content)
    # The structure is <div class="outer-cell ...">
    cells = tree.xpath('//div[contains(@class, "outer-cell")]')
    
    events = []
    for cell in cells:
        # Find the watch link
        link_node = cell.xpath('.//a[contains(@href, "youtube.com/watch?v=")]')
        if not link_node:
             continue
        
        url = link_node[0].get('href')
        video_id = get_video_id(url)
        title = link_node[0].text
        
        # Find the channel link (usually the second <a> in the same cell)
        channel_node = cell.xpath('.//a[contains(@href, "youtube.com/channel/")]')
        channel = channel_node[0].text if channel_node else "Unknown Channel"
        
        # Find the timestamp (usually text node after the last <br> in the content-cell)
        # Or just look for the text pattern in the content-cell
        content_text = cell.xpath('.//div[contains(@class, "content-cell")]//text()')
        timestamp = None
        for text in reversed(content_text):
            parsed = parse_timestamp(text.strip())
            if parsed:
                timestamp = parsed
                break
        
        if video_id and timestamp:
            events.append({
                'video_id': video_id,
                'title': title,
                'channel': channel,
                'timestamp': timestamp,
                'artist': video_to_artist.get(video_id, channel)
            })

    # Sort events by timestamp ascending
    events.sort(key=lambda x: x['timestamp'])
    print(f"Extracted {len(events)} watch events.")

    # Group into sessions
    sessions = []
    if events:
        current_session = [events[0]]
        for i in range(1, len(events)):
            gap = events[i]['timestamp'] - events[i-1]['timestamp']
            if gap > timedelta(minutes=SESSION_GAP_MINUTES):
                sessions.append(current_session)
                current_session = [events[i]]
            else:
                current_session.append(events[i])
        sessions.append(current_session)

    print(f"Grouped into {len(sessions)} sessions.")

    # Analyze transitions
    transitions = {}
    path_counts = {}

    for session in sessions:
        path = [item['artist'] for item in session]
        # Remove consecutive duplicates to see flow between distinct artists
        collapsed_path = []
        if path:
            collapsed_path.append(path[0])
            for i in range(1, len(path)):
                if path[i] != path[i-1]:
                    collapsed_path.append(path[i])
        
        path_str = " -> ".join(collapsed_path)
        path_counts[path_str] = path_counts.get(path_str, 0) + 1
        
        for i in range(len(collapsed_path) - 1):
            pair = (collapsed_path[i], collapsed_path[i+1])
            transitions[pair] = transitions.get(pair, 0) + 1

    # Sorting results
    top_paths = sorted(path_counts.items(), key=lambda x: x[1], reverse=True)[:20]
    top_transitions = sorted(transitions.items(), key=lambda x: x[1], reverse=True)[:50]

    # Write report
    with open(OUTPUT_REPORT_PATH, 'w', encoding='utf-8') as f:
        f.write("Music History Session Mapping Report\n")
        f.write("====================================\n\n")
        f.write(f"Total Watch Events: {len(events)}\n")
        f.write(f"Total Sessions: {len(sessions)}\n")
        f.write(f"Session Gap Threshold: {SESSION_GAP_MINUTES} minutes\n\n")
        
        f.write("Top 20 Distinct Artist/Channel Paths in Sessions:\n")
        f.write("--------------------------------------------------\n")
        for path, count in top_paths:
            f.write(f"{count}x: {path}\n")
        
        f.write("\nTop 50 Transitions between Artists/Channels:\n")
        f.write("--------------------------------------------\n")
        for (src, dst), count in top_transitions:
            f.write(f"{count}x: {src} -> {dst}\n")

    # Save transitions to JSON for further use
    serializable_transitions = [
        {"from": k[0], "to": k[1], "count": v} for k, v in transitions.items()
    ]
    with open(OUTPUT_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(serializable_transitions, f, indent=4)

    print(f"Report generated: {OUTPUT_REPORT_PATH}")
    print(f"JSON mapping saved: {OUTPUT_JSON_PATH}")

if __name__ == "__main__":
    main()
