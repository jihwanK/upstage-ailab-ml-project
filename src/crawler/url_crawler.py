import time

import requests
from bs4 import BeautifulSoup
import pandas as pd
import logging
from tqdm import tqdm

logging.basicConfig(filename="../../logs/url_crawler.log", filemode='a', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

cat_nums = [
    10000010011, 10000010002, 10000010012, 10000010006, 10000010008,
    10000010007, 10000010005, 10000010004, 10000010003, 10000020001,
    10000020002, 10000020003, 10000020005, 10000020004, 10000030007,
    10000030005, 10000030006, 10000010001, 10000010009, 10000010010,
]

cat_names = [
    "선케어", "메이크업", "네일", "미용소품", "더모코스메틱", "맨즈케어", "향수-디퓨저", "헤어케어",
    "바디케어", "건강식품", "푸드", "구강용품", "헬스-건강용품", "여성-위생용품", "컴포트웨어",
    "리빙-펫", "취미-팬시", "스킨케어", "마스크팩", "클렌징"
]

product_url_dict = {}
for i, cat_num in enumerate(tqdm(cat_nums)):
    url_list = []
    page = f"https://www.oliveyoung.co.kr/store/main/getBestList.do?dispCatNo=900000100100001&fltDispCatNo={cat_num}"
    logging.info("[START] Crawl %s URLs", cat_names[i])

    html = requests.get(page.format(cat_num), timeout=100).text
    soup = BeautifulSoup(html, "html.parser")

    products = soup.find_all("div", attrs={"class": "prd_info"})
    for product in products:
        url_list.append(product.find("a").attrs["href"])
    product_url_dict[cat_names[i]] = url_list
    pd.DataFrame(url_list, columns=[cat_names[i]]).to_csv(f"../../data/url/url_{i}.csv", index=False)
    time.sleep(2)

    logging.info("[FINISH] Crawl %s URLs", cat_names[i])

pd.DataFrame(product_url_dict).to_csv("../../data/all_products_url.csv", index=False)
