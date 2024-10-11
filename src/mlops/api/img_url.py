from bs4 import BeautifulSoup
import requests
from data_loader import product_name2id


def get_image_urls(items, caches):
    urls = []
    for item in items:
        if item not in caches:
            page = "https://www.oliveyoung.co.kr/store/goods/getGoodsDetail.do?goodsNo={product_id}"
            print(product_name2id[item[0]])
            html = requests.get(page.format(product_id=product_name2id[item[0]]), timeout=100).text
            soup = BeautifulSoup(html, "html.parser")
            try:
                url = soup.find("div", attrs={"class": "prd_img"}).find("img").attrs["src"]
                caches[item] = url
                urls.append(url)
            except Exception:
                urls.append(None)
        else:
            urls.append(caches[item])

    return urls, caches
