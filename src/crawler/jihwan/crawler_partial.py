import os
import re
import time
from collections import defaultdict
import logging
import sys

import pandas as pd
from tqdm import tqdm

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException

logging.basicConfig(filename="../../logs/crawler.log", filemode='a', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--window-size=1920x1080")
chrome_options.add_argument('--disable-gpu')
chrome_options.add_argument('--disable-infobars')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-blink-features=AutomationControlled')
service = Service()

error_list = defaultdict(list)
HEADER = ""

########################################################################################################################

def extract_element_text(driver, parent_element, css_selector, url, wait=True, timeout=10):
    try:
        if wait:
            WebDriverWait(driver, timeout).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, css_selector))
            )
        element = parent_element.find_element(By.CSS_SELECTOR, css_selector)
        result = element.text.strip()
        return result
    except Exception as e:
        logging.error("[%s] %s exception for %s at %s", HEADER, type(e).__name__, css_selector, url)
        return None

def extract_element(driver, parent_element, css_selector, url, wait=True, timeout=10):
    try:
        if wait:
            WebDriverWait(driver, timeout).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, css_selector))
            )
        element = parent_element.find_element(By.CSS_SELECTOR, css_selector)
        return element
    except Exception as e:
        logging.error("[%s] %s exception for %s at %s", HEADER, type(e).__name__, css_selector, url)
        return None

def extract_element_text_list(driver, parent_element, css_selector, url, wait=True, timeout=10):
    try:
        if wait:
            WebDriverWait(driver, timeout).until(
                EC.visibility_of_all_elements_located((By.CSS_SELECTOR, css_selector))
            )
        elements = parent_element.find_elements(By.CSS_SELECTOR, css_selector)
        result = [element.text.strip() for element in elements]
        return result
    except Exception as e:
        logging.error("[%s] %s exception for %s at %s", HEADER, type(e).__name__, css_selector, url)
        return []

def extract_element_list(driver, parent_element, css_selector, url, wait=True, timeout=10):
    try:
        if wait:
            WebDriverWait(driver, timeout).until(
                EC.visibility_of_all_elements_located((By.CSS_SELECTOR, css_selector))
            )
        elements = parent_element.find_elements(By.CSS_SELECTOR, css_selector)
        return elements
    except Exception as e:
        logging.error("[%s] %s exception for %s at %s", HEADER, type(e).__name__, css_selector, url)
        return []

########################################################################################################################

def extract_product_info(driver, url):
    logging.info("[%s] [extract_product_info] Start", HEADER)
    brand_name, product_name, product_flags = None, None, []
    review_cnt, overall_rating = None, None

    try:
        WebDriverWait(driver, 10).until(
            EC.visibility_of_all_elements_located((By.CSS_SELECTOR, "div.right_area > div.prd_info > p.prd_flag span"))
        )
        WebDriverWait(driver, 10).until(
            EC.visibility_of_all_elements_located((By.CSS_SELECTOR, "div.left_area > div.prd_social_info > p#repReview"))
        )
    except Exception as e:
        logging.error("[%s] Error extracting product info from %s \n%s", HEADER, url, e)

    product_info = extract_element(driver, driver, "div.right_area > div.prd_info", url, True, 20)
    product_social_info = extract_element(driver, driver, "div.left_area > div.prd_social_info", url, True, 20)

    brand_name = extract_element_text(driver, product_info, "p.prd_brand", url, False)
    product_name = extract_element_text(driver, product_info, "p.prd_name", url, False)
    product_flags = extract_element_text_list(driver, product_info, "p.prd_flag span", url, False)

    review_cnt_txt = extract_element_text(driver, product_social_info, "p#repReview > em", url, False)
    review_cnt = int(review_cnt_txt.strip("()").strip("건").replace(",", ""))
    overall_rating = float(extract_element_text(driver, product_social_info, "p#repReview > b", url, False))

    logging.info("[%s] [extract_product_info] Finished with: brand_name=%s, product_name=%s, review_cnt=%d, overall_rating=%f",
                 HEADER, brand_name, product_name, review_cnt, overall_rating)

    return {
        "brand_name": brand_name,
        "product_name": product_name,
        "product_flag": ",".join(product_flags),
        "url": url,
        "review_cnt": review_cnt,
        "overall_rating": overall_rating
    }

########################################################################################################################

def extract_ingredients(driver, url):
    try:
        logging.info("[%s] [extract_ingredients] START", HEADER)

        element = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "li#buyInfo"))
        )
        element.click()
        logging.info("[%s] The ingredient tab has been successfully clicked", HEADER)

    except (NoSuchElementException, TimeoutException, StaleElementReferenceException) as e:
        logging.error("[%s] %s occurred while extracting ingredients for %s \n%s", type(e).__name__, url, e)
    except Exception as e:
        logging.error("[%s] Unexpected error while extracting ingredients for %s \n%s", HEADER, url, e)

    product_info_list = extract_element_list(driver, driver, "div#artcInfo > dl.detail_info_list", url)
    logging.info("[%s] The product information list is like %s", HEADER, product_info_list)

    for product_info in product_info_list[1:]:
        dt_text = extract_element_text(driver, product_info, "dt", url, False)
        if dt_text == "화장품법에 따라 기재해야 하는 모든 성분":
            ingredients = extract_element_text(driver, product_info, "dd", url, False)
            logging.info("[%s] [extract_ingredients] FINISH", HEADER)
            return ingredients

    logging.warning("[%s] No ingredient information found for %s", HEADER, url)

    error_list["url"].append(url)
    error_list["reason"].append("ingredients error")
    return None

########################################################################################################################

def extract_reviews(driver, product_info):
    logging.info("[%s] [extract_reviews] START", HEADER)

    review_info_dict = defaultdict(list)

    try:
        element = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "li#reviewInfo"))
        )
        element.click()
        logging.info("[%s] The review tab has been successfully clicked", HEADER)

        WebDriverWait(driver, 10).until(
            EC.visibility_of_all_elements_located((By.CSS_SELECTOR, "div.review_list_wrap"))
        )

    except (NoSuchElementException, TimeoutException, StaleElementReferenceException) as e:
        logging.error("[%s] %s occurred while preparing reviews for %s \n%s", HEADER, type(e).__name__, product_info["url"], e)
        error_list["url"].append(product_info["url"])
        error_list["reason"].append("review count error")
        return review_info_dict
    except Exception as e:
        logging.error("[%s] Unexpected %s occurred while preparing reviews for %s \n%s", HEADER, type(e).__name__, product_info["url"], e)
        error_list["url"].append(product_info["url"])
        error_list["reason"].append("review count error")
        return review_info_dict

    pages = min(10, (product_info["review_cnt"] // 10) + 1)
    for page in range(1, pages + 1):
        try:
            if page != 1:
                next_page_element = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, f"div.pageing > a[data-page-no='{page}']"))
                )
                next_page_element.click()
                logging.info("[%s] The next review page button has been successfully clicked", HEADER)
                time.sleep(2)
        except (NoSuchElementException, TimeoutException, StaleElementReferenceException) as e:
            logging.error("[%s] %s occurred while navigating to page %d for %s \n%s", HEADER, type(e).__name__, page, product_info["url"], e)
            error_list["url"].append(product_info["url"])
            error_list["reason"].append(f"navigating to page error on {page}")
        except Exception as e:
            logging.error("[%s] Unexpected %s occurred while navigating to page %d for %s \n%s", HEADER, type(e).__name__, page, product_info["url"], e)
            error_list["url"].append(product_info["url"])
            error_list["reason"].append(f"navigating to page error on {page}")

        review_list = extract_element_list(driver, driver, "ul#gdasList > li", product_info["url"])
        for idx, review in enumerate(review_list):
            logging.info("===== [%s] New review start ======", HEADER)
            try:
                WebDriverWait(driver, 10).until(
                    EC.visibility_of_all_elements_located((By.CSS_SELECTOR, "div#Contents div.review_wrap div.info > div.user > p.info_user"))
                )
                WebDriverWait(driver, 10).until(
                    EC.visibility_of_all_elements_located((By.CSS_SELECTOR, "div#Contents div.review_wrap div.review_cont > div.txt_inner"))
                )

            except (NoSuchElementException, TimeoutException, StaleElementReferenceException) as e:
                logging.error("[%s] %s occurred while extracting review[%d] on page %d for %s \n%s", HEADER, type(e).__name__, idx, page, product_info["url"], e)
                error_list["url"].append(product_info["url"])
                error_list["reason"].append(f"extracting review error review[{idx}] on page {page}")
            except Exception as e:
                logging.error("[%s] Unexpected %s occurred while extracting review[%d] on page %d for %s \n%s", HEADER, type(e).__name__, idx, page, product_info["url"], e)
                error_list["url"].append(product_info["url"])
                error_list["reason"].append(f"extracting review error review[{idx}] on page {page}")


            # User Information
            user_info = extract_element(driver, review, "div.info > div.user", product_info["url"])

            user_link = extract_element(driver, user_info, "p.info_user > a.id", product_info["url"], False)
            if user_link:
                user_code_match = re.search(r"'([A-Za-z0-9+/=]+)'", user_link.get_attribute("onclick"))
                user_code = user_code_match.group(1) if user_code_match else None
            logging.info("[%s]User Code is %s", HEADER, user_code)
            
            user_id = extract_element_text(driver, user_info, "p.info_user > a.id", product_info["url"], False)
            logging.info("[%s]User ID is %s", HEADER, user_id)

            user_skin_type = extract_element_text_list(driver, user_info, "p.tag > span", product_info["url"], False)
            user_skin_type = ",".join(user_skin_type)
            logging.info("[%s]User Skin Type is %s", HEADER, user_skin_type)
            
            user_tag_list = extract_element_text_list(driver, user_info, "div.badge > div > a.point_flag", product_info["url"], False)
            user_tag = ",".join(user_tag_list)
            logging.info("[%s]User Tag is %s", HEADER, user_tag)


            # Review Information
            review_info = extract_element(driver, review, "div.review_cont", product_info["url"])
            
            review_rating = extract_element_text(driver, review_info, "div.score_area > span.review_point > span.point", product_info["url"], False)
            logging.info("[%s] Review Rating is %s", HEADER, review_rating)
            
            review_date = extract_element_text(driver, review_info, "div.score_area > span.date", product_info["url"], False)
            logging.info("[%s] Review Date is %s", HEADER, review_date)

            purchase_channel = extract_element_text(driver, review_info, "div.score_area > span.ico_offlineStore", product_info["url"], False) or "온라인"
            logging.info("[%s] The place item puchased is %s", HEADER, purchase_channel)

            review_poll = {}
            poll_samples = extract_element_list(driver, review_info, "div.poll_sample dl.poll_type1", product_info["url"], False)
            logging.info("[%s] Review poll is %s", HEADER, poll_samples)
            for poll_sample in poll_samples:
                poll_question = extract_element_text(driver, poll_sample, "dt > span", product_info["url"], False)
                poll_answer = extract_element_text(driver, poll_sample, "dd > span", product_info["url"], False)
                review_poll[poll_question] = poll_answer
            logging.info("[%s] Review poll is %s", HEADER, review_poll)

            review_text = extract_element_text(driver, review_info, "div.txt_inner", product_info["url"], False)
            logging.info("[%s] User Review is %s", HEADER, review_text)

            recommend_num = extract_element_text(driver, review_info, "div.recom_area button span.num", product_info["url"], False)
            logging.info("[%s] Times the review recommended is %s", HEADER, recommend_num)


            # Insert information
            review_info_dict["user_id"].append(user_id)
            review_info_dict["user_code"].append(user_code)
            review_info_dict["user_skintype"].append(user_skin_type)
            review_info_dict["user_tag"].append(user_tag)
            review_info_dict["brand_name"].append(product_info["brand_name"])
            review_info_dict["product_name"].append(product_info["product_name"])
            review_info_dict["review_rating"].append(review_rating)
            review_info_dict["review_date"].append(review_date)
            review_info_dict["purchase_channel"].append(purchase_channel)
            for key, value in review_poll.items():
                review_info_dict[key].append(value)
            review_info_dict["review"].append(review_text)
            review_info_dict["recommend_num"].append(recommend_num)
            
            time.sleep(2)

    logging.info("[%s] [extract_reviews] FINISH", HEADER)

    return review_info_dict

########################################################################################################################

def scrape_product_reviews(product_url_dict, position=1, product_num=0):
    reviewer_list = set()
    product_info_dict = defaultdict(list)

    cat_name, product_urls = product_url_dict.popitem()

    for url in tqdm(product_urls, desc=f"[{HEADER}] URL", position=position):
        # ua = UserAgent()
        # user_angent = ua.random
        # chrome_options.add_argument(f'user-agent={user_angent}')
        # logging.info([%s] "Create a new user-agent ==> %s", user_angent)
        with webdriver.Chrome(service=service, options=chrome_options) as driver:
            logging.info("====== [%s] New URL Start =======", HEADER)
            logging.info("[%s] URL: %s", HEADER, url)
            driver.get(url)

            product_info = extract_product_info(driver, url)
            ingredients = extract_ingredients(driver, url)
            logging.info("[%s] Ingredients are %s", HEADER, ingredients)
            reviews = extract_reviews(driver, product_info)

            product_info_dict["category"].append(cat_name)
            product_info_dict["product_name"].append(product_info["product_name"])
            product_info_dict["brand_name"].append(product_info["brand_name"])
            product_info_dict["product_flag"].append(product_info["product_flag"])
            product_info_dict["review_cnt"].append(product_info["review_cnt"])
            product_info_dict["overall_rating"].append(product_info["overall_rating"])
            product_info_dict["url"].append(url)
            product_info_dict["ingredients"].append(ingredients)

            reviewer_list.update(reviews["user_code"])

            try:
                os.makedirs(f"../../data/reviews/{cat_name}", exist_ok=True)
                pd.DataFrame(reviews).to_csv(f"../../data/reviews/{cat_name}/{cat_name}_{product_num}_reviews.csv", index=False)
                logging.info("[%s] Safely saved reviews for %s", HEADER, product_info["product_name"])
            except Exception as e:
                logging.error("[%s] Error saving reviews for %s_%s \n%s", HEADER, cat_name, product_info["product_name"], e)
            finally:
                product_num += 1
                
        time.sleep(5)

    try:
        pd.DataFrame(product_info_dict).to_csv(f"../../data/products/{cat_name}.csv", index=False)
        logging.info("[%s] Safely saved product data for category %s", HEADER, cat_name)
    except Exception as e:
        logging.error("[%s] Error saving product data for category %s \n%s", HEADER, cat_name, e)

    try:
        pd.DataFrame(list(reviewer_list), columns=["user_code"]).to_csv(f"../../data/{cat_name}_reviewers.csv", index=False)
        logging.info("[%s] Safely saved reviewer data for category %s", HEADER, cat_name)
    except Exception as e:
        logging.error("[%s] Error saving reviewer data for category %s \n%s", HEADER, cat_name, e)

########################################################################################################################

# main function
if __name__ == "__main__":
    row = int(sys.argv[2]) or 0
    product_url_df = pd.read_csv(sys.argv[1]).iloc[row:, :]
    # product_url_df = pd.read_csv("../../data/url/url_0.csv")
    position = 0
    product_url_dict = product_url_df.to_dict("list")
    HEADER = product_url_df.columns[0]
    try:
        logging.info("========== [%s] [Crawling Start] ==========", HEADER)
        scrape_product_reviews(product_url_dict, position, row)
        logging.info("========== [%s] [Crawling Finish] ==========", HEADER)
    finally:
        pd.DataFrame(error_list).to_csv("../../data/error/error_list.csv", index=False)
