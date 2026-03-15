# Future Plans and Ideas

## 1. Fetch Video Metadata via URLs
Create a script to pull the YouTube video URLs from the Google Takeout history data and fetch metadata for each video—specifically the **video length/duration**. This could potentially be done using the YouTube Data API or a tool like `yt-dlp`.

## 2. Accurate Session Gap Calculations
Currently, the codebase determines listening sessions by calculating the time gap between the *start times* of two consecutive videos (e.g., separating sessions if the gap is greater than 30 minutes). 

**The Flaw:**
If you watch a video that is 1 hour long, the gap between the start times is 60 minutes. Even if the next video plays immediately after it finishes, the system will incorrectly break the session because 60 minutes is greater than the defined 30-minute session gap limit.

**Proposed Implementation:**
By utilizing the video lengths fetched in the first step, we can calculate the actual *end time* of each video (`Start Time + Video Duration`). The session logic can then be updated to measure the time gap between the *end time* of the previous video and the *start time* of the next one. This will accurately track long videos (such as full album streams, DJ mixes, or hour-long live shows) as continuous, unbroken sessions.
