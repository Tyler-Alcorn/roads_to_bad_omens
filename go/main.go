package main

import (
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/url"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"time"

	"github.com/PuerkitoBio/goquery"
)

type WatchEvent struct {
	VideoID   string
	Title     string
	Channel   string
	Artist    string
	Timestamp time.Time
	IsYTMusic bool
}

type GraphNode struct {
	ID string `json:"id"`
}

type GraphLink struct {
	Source string `json:"source"`
	Target string `json:"target"`
	Value  int    `json:"value"`
}

type GraphData struct {
	Nodes []GraphNode `json:"nodes"`
	Links []GraphLink `json:"links"`
}

func parseTimestamp(ts string) (time.Time, error) {
	// Format generally expected from Google Takeout watch-history.html: "Feb 24, 2026, 4:00:14 PM"
	layout := "Jan 2, 2006, 3:04:05 PM"
	// Ensure narrow no-break space is converted
	ts = strings.ReplaceAll(ts, "\u202f", " ")
	ts = strings.ReplaceAll(ts, " ", " ")

	// Remove trailing timezone if present (e.g. PST, PDT)
	re := regexp.MustCompile(`\s+[A-Z]{3,4}$`)
	cleanTs := strings.TrimSpace(re.ReplaceAllString(ts, ""))

	parsed, err := time.Parse(layout, cleanTs)
	if err != nil {
		return time.Time{}, err
	}
	return parsed, nil
}

func getVideoID(href string) string {
	u, err := url.Parse(href)
	if err != nil {
		return ""
	}
	return u.Query().Get("v")
}

func parseHistoryHTML(r io.Reader) ([]WatchEvent, error) {
	doc, err := goquery.NewDocumentFromReader(r)
	if err != nil {
		return nil, err
	}

	var events []WatchEvent

	// Process each outer-cell
	doc.Find("div.outer-cell").Each(func(i int, s *goquery.Selection) {
		linkNode := s.Find("a[href*='youtube.com/watch?v=']").First()
		if linkNode.Length() == 0 {
			return
		}

		href, _ := linkNode.Attr("href")
		videoID := getVideoID(href)
		title := linkNode.Text()

		channelNode := s.Find("a[href*='youtube.com/channel/']").First()
		channel := "Unknown Channel"
		if channelNode.Length() > 0 {
			channel = channelNode.Text()
		}

		var timestamp time.Time
		foundTime := false

		// To find the timestamp, we iterate text nodes inside the content-cell
		s.Find("div.content-cell").Contents().Each(func(j int, sel *goquery.Selection) {
			if goquery.NodeName(sel) == "#text" {
				text := strings.TrimSpace(sel.Text())
				if text != "" {
					parsed, err := parseTimestamp(text)
					if err == nil {
						timestamp = parsed
						foundTime = true
					}
				}
			}
		})

		if videoID != "" && foundTime {
			isYTMusic := strings.Contains(s.Find("div.header-cell").Text(), "YouTube Music")
			events = append(events, WatchEvent{
				VideoID:   videoID,
				Title:     title,
				Channel:   channel,
				Artist:    channel, // default artist to channel if no csv logic available
				Timestamp: timestamp,
				IsYTMusic: isYTMusic,
			})
		}
	})

	// Sort events ascending by timestamp
	sort.Slice(events, func(i, j int) bool {
		return events[i].Timestamp.Before(events[j].Timestamp)
	})

	return events, nil
}

func handleGenerate(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	err := r.ParseMultipartForm(100 << 20) // 100 MB max memory limit
	if err != nil {
		http.Error(w, "Error parsing form", http.StatusBadRequest)
		return
	}

	file, _, err := r.FormFile("historyFile")
	if err != nil {
		http.Error(w, "Error retrieving file", http.StatusBadRequest)
		return
	}
	defer file.Close()

	// Parse settings
	collapseTopic := r.FormValue("collapseTopic") == "on" || r.FormValue("collapseTopic") == "true"
	videoType := r.FormValue("videoType") // "all", "yt", or "ytmusic"
	if videoType == "" {
		videoType = "all"
	}
	
	minConnections := 3
	if val, err := strconv.Atoi(r.FormValue("minConnections")); err == nil {
		minConnections = val
	}

	sessionGapMinutes := 30
	if val, err := strconv.Atoi(r.FormValue("sessionGap")); err == nil {
		sessionGapMinutes = val
	}

	events, err := parseHistoryHTML(file)
	if err != nil {
		http.Error(w, "Error parsing HTML", http.StatusInternalServerError)
		return
	}

	// Group events into sessions based on time intervals
	var sessions [][]WatchEvent
	if len(events) > 0 {
		var validEvents []WatchEvent
		for _, e := range events {
			// filter by video type
			if videoType == "ytmusic" && !e.IsYTMusic {
				continue
			}
			if videoType == "yt" && e.IsYTMusic {
				continue
			}
			validEvents = append(validEvents, e)
		}

		if len(validEvents) > 0 {
			currentSession := []WatchEvent{validEvents[0]}
			for i := 1; i < len(validEvents); i++ {
				gap := validEvents[i].Timestamp.Sub(validEvents[i-1].Timestamp)
				if gap.Minutes() > float64(sessionGapMinutes) {
					sessions = append(sessions, currentSession)
					currentSession = []WatchEvent{validEvents[i]}
				} else {
					currentSession = append(currentSession, validEvents[i])
				}
			}
			sessions = append(sessions, currentSession)
		}
	}

	transitionCounts := make(map[string]int)

	// Build transitions
	for _, session := range sessions {
		var path []string
		for _, event := range session {
			artist := event.Artist

			// Collapse generic "... - Topic" formats usually used by YouTube Music
			if collapseTopic {
				artist = strings.ReplaceAll(artist, " - Topic", "")
				artist = strings.TrimSpace(artist)
			}
			path = append(path, artist)
		}

		// Remove consecutive identical items in the path
		var collapsedPath []string
		if len(path) > 0 {
			collapsedPath = append(collapsedPath, path[0])
			for i := 1; i < len(path); i++ {
				if path[i] != path[i-1] {
					collapsedPath = append(collapsedPath, path[i])
				}
			}
		}

		// Map exact A->B step transitions
		for i := 0; i < len(collapsedPath)-1; i++ {
			src := collapsedPath[i]
			dst := collapsedPath[i+1]
			
			if src == "Unknown Channel" || dst == "Unknown Channel" {
				continue
			}
			if src == dst {
				// double check we have no self-loops just in case
				continue
			}
			
			key := src + "||" + dst
			transitionCounts[key]++
		}
	}

	var filteredLinks []GraphLink
	for key, count := range transitionCounts {
		if count >= minConnections {
			parts := strings.Split(key, "||")
			src := parts[0]
			dst := parts[1]

			filteredLinks = append(filteredLinks, GraphLink{
				Source: src,
				Target: dst,
				Value:  count,
			})
		}
	}

	// Sort high level transitions
	sort.Slice(filteredLinks, func(i, j int) bool {
		return filteredLinks[i].Value > filteredLinks[j].Value
	})
	
	// Truncate to save UI rendering (Max 2000 links)
	if len(filteredLinks) > 2000 {
		filteredLinks = filteredLinks[:2000]
	}

	// Rebuild nodes array reliably matched with our active links
	finalNodesSet := make(map[string]bool)
	for _, link := range filteredLinks {
		finalNodesSet[link.Source] = true
		finalNodesSet[link.Target] = true
	}

	var nodes []GraphNode
	for node := range finalNodesSet {
		nodes = append(nodes, GraphNode{ID: node})
	}

	data := GraphData{
		Nodes: nodes,
		Links: filteredLinks,
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(data)
}

func main() {
	// API endpoint
	http.HandleFunc("/api/generate", handleGenerate)
	
	// Serve static files
	http.Handle("/", http.FileServer(http.Dir(".")))

	fmt.Println("Server listening on :8080")
	log.Fatal(http.ListenAndServe(":8080", nil))
}
