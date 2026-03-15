import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_JSON = os.path.join(BASE_DIR, "python", "music_session_transitions.json")
OUTPUT_JSON = os.path.join(BASE_DIR, "python", "graph_data.json")

# Performance thresholds
MIN_COUNT = 3  # Only keep transitions that occurred at least 3 times
MAX_TRANSITIONS = 2000 # Limit total transitions to keep UI snappy

def main():
    if not os.path.exists(INPUT_JSON):
        print(f"Error: {INPUT_JSON} not found.")
        return

    with open(INPUT_JSON, 'r', encoding='utf-8') as f:
        transitions = json.load(f)

    print(f"Loaded {len(transitions)} total transitions.")

    # Filter based on count, remove self-loops, and ignore 'Unknown Channel'
    filtered = [t for t in transitions 
                if t['count'] >= MIN_COUNT 
                and t['from'] != t['to'] 
                and t['from'] != 'Unknown Channel' 
                and t['to'] != 'Unknown Channel']
    
    # Sort by count descending and take top N
    filtered.sort(key=lambda x: x['count'], reverse=True)
    filtered = filtered[:MAX_TRANSITIONS]

    print(f"Filtered to {len(filtered)} transitions (count >= {MIN_COUNT}).")

    # Build nodes and links
    nodes_set = set()
    links = []
    
    for t in filtered:
        nodes_set.add(t['from'])
        nodes_set.add(t['to'])
        links.append({
            "source": t['from'],
            "target": t['to'],
            "value": t['count']
        })

    nodes = [{"id": name} for name in nodes_set]
    
    graph_data = {
        "nodes": nodes,
        "links": links
    }

    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(graph_data, f, indent=4)

    print(f"Graph data saved to {OUTPUT_JSON}")
    print(f"Total nodes: {len(nodes)}, Total links: {len(links)}")

    import re
    html_file = os.path.join(BASE_DIR, "python", "music_graph.html")
    if os.path.exists(html_file):
        with open(html_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Find .graphData(...) line and replace its content
        new_content = re.sub(
            r'\.graphData\(\{.*?"links":\s*\[.*?\]\s*\}\)',
            lambda m: f'.graphData({json.dumps(graph_data)})',
            content,
            flags=re.DOTALL
        )
        
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("Successfully updated music_graph.html")

if __name__ == "__main__":
    main()
