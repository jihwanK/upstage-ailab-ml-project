import os
import re
import time
from collections import defaultdict
import logging

import pandas as pd
from tqdm import tqdm
from tqdm import tqdm

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException


logging.basicConfig(filename="../../logs/crawler.log", filemode='a', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# logging.getLogger(__name__).setLevel(logging.INFO)

chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--window-size=1920x1080")
chrome_options.add_argument('--disable-gpu')
chrome_options.add_argument('--disable-infobars')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-blink-features=AutomationControlled')
service = Service()

error_list = defaultdict(list)

def extract_product_info(driver, url):
    logging.info("[extract_product_info] START")
    try:
        product_info = driver.find_element(By.CSS_SELECTOR, "div.right_area div.prd_info")
        brand_name = product_info.find_element(By.CSS_SELECTOR, "p.prd_brand").text.strip()
        product_name = product_info.find_element(By.CSS_SELECTOR, "p.prd_name").text.strip()
        product_flags = [flag.text.strip() for flag in product_info.find_elements(By.CSS_SELECTOR, "p.prd_flag span")]

        logging.info("[extract_product_info] FINISH")

        return {
            "brand_name": brand_name,
            "product_name": product_name,
            "product_flag": ",".join(product_flags),
            "url": url,
        }

    except (NoSuchElementException, TimeoutException, StaleElementReferenceException) as e:
        print("NoSuchElementException, TimeoutException extracting product info")
        logging.error("Error extracting product info from %s \n%s", url, e)
        error_list["url"].append(url)
        error_list["reason"].append("Product info NoSuchElementException, TimeoutException")
        return {"brand_name": None, "product_name": None, "product_flag": None}
    except Exception as e:
        print("Error extracting product info")
        logging.error("Error extracting product info from %s \n%s", url, e)
        error_list["url"].append(url)
        error_list["reason"].append("Product info Error")
        return {"brand_name": None, "product_name": None, "product_flag": None}


def extract_ingredients(driver, url):
    try:
        logging.info("[extract_ingredients] START")
        element = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "li#buyInfo"))
        )
        element.click()

        WebDriverWait(driver, 10).until(
            EC.visibility_of_all_elements_located((By.CSS_SELECTOR, "div#artcInfo > dl.detail_info_list"))
        )

        product_info_list = driver.find_elements(By.CSS_SELECTOR, "div#artcInfo > dl.detail_info_list")

        for product_info in product_info_list[1:]:
            dt_text = product_info.find_element(By.TAG_NAME, "dt").text.strip()
            if dt_text == "화장품법에 따라 기재해야 하는 모든 성분":
                logging.info("[extract_ingredients] FINISH")
                return product_info.find_element(By.TAG_NAME, "dd").text.strip()

    except (NoSuchElementException, TimeoutException, StaleElementReferenceException) as e:
        print("NoSuchElementException, TimeoutException extracting ingredients")
        logging.error("Specific error (NoSuchElementException or TimeoutException) in extract_ingredients \n%s", e)
        error_list["url"].append(url)
        error_list["reason"].append("ingredients error")
        return None
    except Exception as e:
        print("Error extracting ingredients")
        logging.error("Error extracting ingredients \n%s", e)
        error_list["url"].append(url)
        error_list["reason"].append("ingredients error")
        return None


def extract_reviews(driver, product_info_dict):
    logging.info("[extract_reviews] START")

    review_info_dict = defaultdict(list)
    review_cnt = 0

    try:
        element = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "li#reviewInfo"))
        )
        element.click()

        WebDriverWait(driver, 10).until(
            EC.visibility_of_all_elements_located((By.CSS_SELECTOR, "div.review_list_wrap"))
        )

        review_cnt_elem = driver.find_element(By.CSS_SELECTOR, "ul.prd_detail_tab > li#reviewInfo > a > span")
        review_cnt = int(review_cnt_elem.text.strip("()").replace(",", ""))
        pages = (review_cnt // 10) + 1
        pages = min(100, pages)
        overall_rating = float(driver.find_element(By.CSS_SELECTOR, "div.product_rating_area div.star_area > p.num > strong").text)


    except (NoSuchElementException, TimeoutException, StaleElementReferenceException) as e:
        print("NoSuchElementException or TimeoutException extracting review count or preparing reviews")
        logging.error("Specific error (NoSuchElementException or TimeoutException) in extract_reviews \n%s", e)
        error_list["url"].append(product_info_dict["url"])
        error_list["reason"].append("review count error")
        return review_info_dict, review_cnt
    except Exception as e:
        print("Error extracting review count or preparing reviews")
        logging.error("Error extracting review count or preparing reviews \n%s", e)
        error_list["url"].append(product_info_dict["url"])
        error_list["reason"].append("review count error")
        return review_info_dict, review_cnt

    for page in tqdm(range(1, pages + 1), desc="Page", position=2, leave=False):
        try:
            if page != 1:
                next_page_element = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, f"div.pageing > a[data-page-no='{page}']"))
                )
                next_page_element.click()
                time.sleep(1.5)

            review_list = driver.find_elements(By.CSS_SELECTOR, "div.review_list_wrap > ul#gdasList > li")

            for idx, review in enumerate(review_list):
                try:
                    WebDriverWait(driver, 10).until(
                        EC.visibility_of_all_elements_located((By.CSS_SELECTOR, "div#Contents div.review_wrap div.info > div.user > p.info_user"))
                    )
                    WebDriverWait(driver, 10).until(
                        EC.visibility_of_all_elements_located((By.CSS_SELECTOR, "div#Contents div.review_wrap div.review_cont > div.txt_inner"))
                    )
                    user_info = review.find_element(By.CSS_SELECTOR, "div.info")
                    user_link = user_info.find_element(By.TAG_NAME, "a")
                    user_code_match = re.search(r"'([A-Za-z0-9+/=]+)'", user_link.get_attribute("onclick"))
                    user_code = user_code_match.group(1) if user_code_match else None
                    user_id = user_info.find_element(By.CSS_SELECTOR, "p.info_user > a.id").text.strip()
                    try:
                        user_skin_type = [element.text.strip() for element in user_info.find_elements(By.CSS_SELECTOR, "p.tag > span")]
                    except (NoSuchElementException, TimeoutException, StaleElementReferenceException) as e:
                        logging.error("user_skin is missing")
                        print("user_skin is missing")
                        error_list["url"].append(product_info_dict["url"])
                        error_list["reason"].append("user skin error")
                        user_skin_type = []
                    try:
                        user_tag_list = [ele.text.strip() for ele in user_info.find_elements(By.CSS_SELECTOR, "div.badge > a.point_flag")]
                        user_tag = ",".join(user_tag_list)
                    except (NoSuchElementException, TimeoutException, StaleElementReferenceException) as e:
                        logging.error("user_tag is missing")
                        print("user_tag is missing")
                        error_list["url"].append(product_info_dict["url"])
                        error_list["reason"].append("user tag error")
                        user_tag = None

                    review_info = review.find_element(By.CSS_SELECTOR, "div.review_cont")
                    review_rating = review_info.find_element(By.CSS_SELECTOR, "div.score_area > span.review_point > span.point").text.strip()
                    review_date = review_info.find_element(By.CSS_SELECTOR, "div.score_area > span.date").text.strip()
                    try:
                        purchase_channel = review_info.find_element(By.CSS_SELECTOR, "div.score_area > span.ico_offlineStore").text.strip()
                    except (NoSuchElementException, TimeoutException, StaleElementReferenceException) as e:
                        # logging.error("purchase_channel is missing")
                        # print("purchase_channel is missing")
                        purchase_channel = "온라인"
                    item_option_elements = review_info.find_elements(By.CSS_SELECTOR, "p.item_option")
                    item_option = item_option_elements[0].text.strip() if item_option_elements else None

                    review_poll = {}
                    poll_samples = review_info.find_elements(By.CSS_SELECTOR, "div.poll_sample dl.poll_type1")
                    for poll_sample in poll_samples:
                        poll_question = poll_sample.find_element(By.TAG_NAME, "dt").text.strip()
                        poll_answer = poll_sample.find_element(By.TAG_NAME, "dd").text.strip()
                        review_poll[poll_question] = poll_answer

                    review_text = review_info.find_element(By.CSS_SELECTOR, "div.txt_inner").text.strip()
                    recommend_num = review_info.find_element(By.CSS_SELECTOR, "div.recom_area button span.num").text.strip()

                    review_info_dict["user_id"].append(user_id)
                    review_info_dict["user_code"].append(user_code)
                    review_info_dict["user_skintype"].append(",".join(user_skin_type))
                    review_info_dict["user_tag"].append(user_tag)
                    review_info_dict["brand_name"].append(product_info_dict["brand_name"])
                    review_info_dict["product_name"].append(product_info_dict["product_name"])
                    review_info_dict["review_rating"].append(review_rating)
                    review_info_dict["review_date"].append(review_date)
                    review_info_dict["purchase_channel"].append(purchase_channel)
                    review_info_dict["item_option"].append(item_option)
                    for key, value in review_poll.items():
                        review_info_dict[key].append(value)
                    review_info_dict["review"].append(review_text)
                    review_info_dict["recommend_num"].append(recommend_num)


                except (NoSuchElementException, TimeoutException, StaleElementReferenceException) as e:
                    print(f"NoSuchElementException, TimeoutException extracting review[{idx}] on page {page}")
                    logging.error("Specific error in review[%d] on page %d for %s \n%s", idx, page, product_info_dict["url"], e)
                    error_list["url"].append(product_info_dict["url"])
                    error_list["reason"].append(f"extracting review error review[{idx}] on page {page}")
                except Exception as e:
                    print(f"Error extracting review[{idx}] on page {page}")
                    logging.error("Error extracting review[%d] on page %d \n%s", idx, page, e)
                    error_list["url"].append(product_info_dict["url"])
                    error_list["reason"].append(f"extracting review error review[{idx}] on page {page}")


        except (NoSuchElementException, TimeoutException, StaleElementReferenceException) as e:
            print(f"NoSuchElementException, TimeoutException navigating to page {page}")
            logging.error("Specific error navigating to page %d for %s \n%s", page, product_info_dict["url"], e)
            error_list["url"].append(product_info_dict["url"])
            error_list["reason"].append(f"navigating to page error on {page}")
        except Exception as e:
            print(f"Error navigating to page {page}")
            logging.error("Error navigating to page %d \n%s", page, e)
            error_list["url"].append(product_info_dict["url"])
            error_list["reason"].append(f"navigating to page error on {page}")

        # print(f"crawling the {page}/{pages} finished")
    logging.info("[extract_reviews] FINISH")

    return review_info_dict, review_cnt, overall_rating


def scrape_product_reviews(product_url_dict):
    reviewer_list = set()

    for cat_name in tqdm(product_url_dict, desc="Category", position=0):
        product_info_dict = defaultdict(list)
        product_num = 0

        for url in tqdm(product_url_dict[cat_name], desc="URL", position=1, leave=False):
            try:
                with webdriver.Chrome(service=service, options=chrome_options) as driver:
                    driver.get(url)
                    # print(f"Scraping URL: {url}")

                    product_info = extract_product_info(driver, url)
                    ingredients = extract_ingredients(driver, url)
                    reviews, review_cnt, overall_rating = extract_reviews(driver, product_info)
                    reviews, review_cnt, overall_rating = extract_reviews(driver, product_info)

                    product_info_dict["category"].append(cat_name)
                    product_info_dict["product_name"].append(product_info["product_name"])
                    product_info_dict["brand_name"].append(product_info["brand_name"])
                    product_info_dict["product_flag"].append(product_info["product_flag"])
                    product_info_dict["url"].append(url)
                    product_info_dict["ingredients"].append(ingredients)

                    reviews, review_cnt, overall_rating = extract_reviews(driver, product_info)
                    product_info_dict["review_cnt"].append(review_cnt)
                    product_info_dict["overall_rating"].append(overall_rating)

                    reviewer_list.update(reviews["user_code"])

                    time.sleep(2)

                    try:
                        pd.DataFrame(reviews).to_csv(f"../../data/reviews/{cat_name}_{product_info['product_name']}_reviews.csv", index=False)
                        pd.DataFrame(product_info_dict).to_csv(f"../../data/products/{cat_name}_{product_info['product_name']}.csv", index=False)
                    except Exception as e:
                        print(f"Error saving data for category {cat_name}_{product_info['product_name']}")
                        logging.error("Error saving data for category %s_%s \n%s", cat_name,product_info['product_name'], e)
                    finally:
                        product_num += 1

            except Exception as e:
                print(f"Error processing URL {url} in category {cat_name}")
                logging.error("Error processing URL %s in category %s \n%s", url, cat_name, e)

        try:
            pd.DataFrame(product_info_dict).to_csv(f"../../data/products/{cat_name}.csv", index=False)
        except Exception as e:
            print(f"Error saving data for category {cat_name}")
            logging.error("Error saving data for category %s \n%s", cat_name, e)

    try:
        pd.DataFrame(list(reviewer_list), columns=["user_code"]).to_csv("../../data/reviewers.csv", index=False)
    except Exception as e:
        print("Error saving reviewer data")
        logging.error("Error saving reviewer data \n%s", e)


# main function
if __name__ == "__main__":
    product_url_dict = pd.read_csv("../../data/product_url.csv").to_dict("list")
    try:
        # scrape_product_reviews({"선케어": product_url_dict["선케어"]})
        # del product_url_dict["선케어"]
        scrape_product_reviews(product_url_dict)
    finally:
        pd.DataFrame(error_list).to_csv("../../data/error/error_list.csv", index=False)
    
