from fastapi import FastAPI
from model import get_top_n_unseen_recommendations, get_top_n_seen_recommendations
from img_url import get_image_urls

app = FastAPI()
app.state.caches = {}

@app.get("/")
def index():
    return {'Hello':'World!'}

@app.get("/api/v1/recommend/{user_code}")
def recommend_items(user_code):
    seen_recommendations = get_top_n_seen_recommendations(user_code)
    unseen_recommendations = get_top_n_unseen_recommendations(user_code)

    seen_img, app.state.caches = get_image_urls(seen_recommendations, app.state.caches)
    unseen_img, app.state.caches = get_image_urls(unseen_recommendations, app.state.caches)

    return {
        "seen": seen_recommendations,
        "unseen": unseen_recommendations,
        "seen_img": seen_img,
        "unseen_img": unseen_img,
    }
