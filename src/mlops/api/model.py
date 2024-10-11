from model_loader import model
from data_loader import data, product_ids, product_id2name


def get_seen_items(df, user_code):
    return set(df[df["user_code"] == user_code]["product_id"])


def get_top_n_unseen_recommendations(user_code, n=10):
    seen_items = get_seen_items(data, user_code)
    unseen_items = [item_id for item_id in product_ids if item_id not in seen_items]

    predictions = []
    for product_id in unseen_items:
        pred = model.predict(user_code, product_id2name[product_id]).est
        predictions.append((product_id2name[product_id], pred))

    predictions.sort(key=lambda x: x[1], reverse=True)
    return predictions[:n]


def get_top_n_seen_recommendations(user_code, n=10):
    seen_items = get_seen_items(data, user_code)

    predictions = []
    for product_id in seen_items:
        pred = model.predict(user_code, product_id2name[product_id]).est
        predictions.append((product_id2name[product_id], pred))

    predictions.sort(key=lambda x: x[1], reverse=True)
    return predictions[:n]


