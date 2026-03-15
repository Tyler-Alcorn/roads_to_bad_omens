# Music Session Transition Graph

An interactive force-directed graph visualization of music listening transitions, mapping how artists and channels flow into one another based on your watched history. 

## ✨ Features
- **Interactive Force-Directed Graph**: Nodes (artists) and edges (transitions) are rendered dynamically with physics constraints.
- **Web Interface**: A blazingly fast `Go` backend that parses history directly in your browser.
- **Customizable Filtration**: Filter out non-music videos, collapse generic "- Topic" channels, and adjust connection thresholds and session gaps.
- **Local offline processing**: Everything runs locally. No data leaves your machine.

## 🚀 Getting Your Data (Google Takeout)
To generate your own personal music flow graph, you'll need your viewing history from Google.
1. Visit [Google Takeout](https://takeout.google.com/).
2. Click **"Deselect All"** at the top.
3. Scroll down and check the box for **"YouTube and YouTube Music"**.
4. Click **"All YouTube data included"** and deselect everything except **"history"**. 
5. Under **"Multiple formats"**, ensure the History format is set to `HTML`.
6. Click **Next step** and then **Create export**.
7. Once downloaded, extract the `.zip` file. You'll use the `Takeout/YouTube and YouTube Music/history/watch-history.html` file in the web interface!

## 🛠️ Usage (Web App)
The easiest way to explore your data is through the native Go application:
1. Ensure you have [Go](https://go.dev/) installed.
2. Navigate to the `go` directory in terminal:
```bash
cd go
go run main.go
```
3. Open your browser to `http://localhost:8080`.
4. Upload the `watch-history.html` file you extracted in the previous steps and click **Generate Graph**!

### Python Processing (CLI)
Alternatively, if you prefer to use the command line without the web GUI, you can process your data and generate a graph entirely in Python.

1. Navigate into the `python/` directory:
```bash
cd python
```
2. Open `analyze_music_sessions.py` and adjust the `# Configuration Options` at the top of the file to your liking (e.g., `VIDEO_TYPE`, `MIN_CONNECTIONS`, `COLLAPSE_TOPIC`).
3. Run the analysis script:
```bash
python3 analyze_music_sessions.py
```
This single command will parse your history, filter it, bundle the transition data into JSON, and automatically embed it directly into the `music_graph.html` UI file. 
4. Simply open `python/music_graph.html` in your web browser to view your generated graph!
