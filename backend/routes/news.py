from fastapi import APIRouter
import httpx, random

router = APIRouter()

HACKERNEWS_TOPSTORIES_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
HACKERNEWS_ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{id}.json"

@router.get("/news/tech")
async def get_tech_news(limit: int = 5, randomize : bool = True):
    """
    Fetch top HackerNews stories (default = 5).
    If `randomize=True`, picks random stories from the top 50 instead of always same top `limit`.
    """
    async with httpx.AsyncClient() as client:
        # get top story IDs
        resp = await client.get(HACKERNEWS_TOPSTORIES_URL)
        ids = resp.json()

        if not ids:
            return {"news": []}

        # take from top 50 to avoid super old stories
        top_ids = ids[:50]

        # pick either first N or random N
        if randomize:
            chosen_ids = random.sample(top_ids, min(limit, len(top_ids)))
        else:
            chosen_ids = top_ids[:limit]

        news_list = []
        for story_id in chosen_ids:
            item_resp = await client.get(HACKERNEWS_ITEM_URL.format(id=story_id))
            item = item_resp.json()
            if item and "title" in item:
                news_list.append({
                    "title": item["title"],
                    "url": item.get("url", f"https://news.ycombinator.com/item?id={story_id}")
                })

        return {"news": news_list}
