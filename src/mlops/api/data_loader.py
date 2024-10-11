import pandas as pd
import json

data = pd.read_csv("../../../data/final/purchase_history_rating.csv")
product_ids = data["product_id"].unique()

product_id2name = json.load(open("../../../data/final/product_id2name.json", "r", encoding="utf-8"))
product_name2id = json.load(open("../../../data/final/product_name2id.json", "r", encoding="utf-8"))
