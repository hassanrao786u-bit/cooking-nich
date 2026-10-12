import streamlit as st
import requests
from datetime import datetime, timedelta, timezone

API_KEY = st.secrets["API_KEY"]

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEO_URL = "https://www.googleapis.com/youtube/v3/videos"
CHANNEL_URL = "https://www.googleapis.com/youtube/v3/channels"

st.title("YouTube Viral Topics Tool")

days = st.number_input("Enter Days to Search (1-30):", min_value=1, max_value=30, value=5)
max_subs = st.number_input("Max subscribers:", min_value=100, value=3000, step=500)

keywords = [
    "Dinner Recipes", "Easy Dinner Recipes", "Quick Dinner Recipes",
    "High Protein Breakfast", "Breakfast Ideas", "Air Fryer Recipes",
    "Easy Dessert Recipes", "One Pot Meals", "Potato Recipes", "Cooking Hacks",
]
selected = st.multiselect("Keywords", keywords, default=keywords[:5])


def call_api(url, params):
    r = requests.get(url, params=params, timeout=15)
    data = r.json()
    if "error" in data:
        raise RuntimeError(data["error"].get("message", "API error"))
    return data


if st.button("Fetch Data"):
    try:
        start_date = (datetime.now(timezone.utc) - timedelta(days=int(days))).strftime("%Y-%m-%dT%H:%M:%SZ")
        results = []

        for kw in selected:
            data = call_api(SEARCH_URL, {
                "part": "snippet", "q": kw, "type": "video",
                "order": "viewCount", "publishedAfter": start_date,
                "maxResults": 5, "key": API_KEY,
            })
            videos = data.get("items", [])
            if not videos:
                st.warning(f"No videos for: {kw}")
                continue

            video_ids = [v["id"]["videoId"] for v in videos if "videoId" in v.get("id", {})]
            channel_ids = list({v["snippet"]["channelId"] for v in videos})

            vstats = call_api(VIDEO_URL, {"part": "statistics", "id": ",".join(video_ids), "key": API_KEY})
            cstats = call_api(CHANNEL_URL, {"part": "statistics", "id": ",".join(channel_ids), "key": API_KEY})

            views_by_id = {i["id"]: int(i["statistics"].get("viewCount", 0)) for i in vstats.get("items", [])}
            subs_by_id = {
                c["id"]: int(c["statistics"].get("subscriberCount", 0))
                for c in cstats.get("items", [])
                if not c["statistics"].get("hiddenSubscriberCount", False)
            }

            for v in videos:
                vid = v.get("id", {}).get("videoId")
                ch = v["snippet"]["channelId"]
                if vid not in views_by_id or ch not in subs_by_id:
                    continue
                if subs_by_id[ch] < max_subs:
                    results.append({
                        "Title": v["snippet"].get("title", "N/A"),
                        "URL": f"https://www.youtube.com/watch?v={vid}",
                        "Views": views_by_id[vid],
                        "Subscribers": subs_by_id[ch],
                        "Keyword": kw,
                    })

        if results:
            results.sort(key=lambda x: x["Views"], reverse=True)
            st.success(f"Found {len(results)} results")
            st.dataframe(results, column_config={"URL": st.column_config.LinkColumn()})
        else:
            st.warning("No results found.")

    except Exception as e:
        st.error(f"Error: {e}")
