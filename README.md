# Music Session Transition Graph

An interactive force-directed graph visualization of music listening transitions, mapping how artists and channels flow into one another based on watch history.

## 🚀 Features
- **Interactive Force-Directed Graph**: Nodes (artists) and edges (transitions) are rendered using a dynamic physics simulation.
- **Weighted Edge Thickness**: The thickness of each connection represents the frequency of that transition.
- **Embedded Data**: The filtered transition data is embedded directly into the HTML file, allowing it to work offline.

## 🛠️ Usage
1. Open `music_graph.html` in your web browser.
2. **Zoom/Pan**: Use your mouse wheel and click-drag.
3. **Pin Nodes**: Drag a node to fix its position for custom layout inspection.

## ⚙️ Data Preparation
The data is processed using `prepare_graph_data.py`, which takes raw transitioning data (`music_session_transitions.json`), filters out low-frequency and self-looping transitions, and embeds the sanitized data (`graph_data.json`) directly into the HTML file.
