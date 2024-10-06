import os
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

logging.basicConfig(filename=f"../../logs/{os.path.basename(__file__)}.log", filemode='a', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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

def scrape_product_reviews(product_url_dict, position=1):
    product_info_dict = defaultdict(list)

    cat_name, product_urls = product_url_dict.popitem()

    for url in tqdm(product_urls, desc=f"[{HEADER}] URL", position=position):
        with webdriver.Chrome(service=service, options=chrome_options) as driver:
            logging.info("====== [%s] New URL Start =======", HEADER)
            logging.info("[%s] URL: %s", HEADER, url)
            try:
                driver.get(url)
            except Exception as e:
                logging.error("[%s] %s saving product data for category %s \n%s", HEADER, type(e).__name__, cat_name, e)

            product_info = extract_product_info(driver, url)
            ingredients = extract_ingredients(driver, url)
            logging.info("[%s] Ingredients are %s", HEADER, ingredients)

            product_info_dict["category"].append(cat_name)
            product_info_dict["product_name"].append(product_info["product_name"])
            product_info_dict["brand_name"].append(product_info["brand_name"])
            product_info_dict["product_flag"].append(product_info["product_flag"])
            product_info_dict["review_cnt"].append(product_info["review_cnt"])
            product_info_dict["overall_rating"].append(product_info["overall_rating"])
            product_info_dict["url"].append(url)
            product_info_dict["ingredients"].append(ingredients)
                
        time.sleep(5)

    try:
        pd.DataFrame(product_info_dict).to_csv(f"../../data/jihwan/products/{cat_name}.csv", index=False)
        logging.info("[%s] Safely saved product data for category %s", HEADER, cat_name)
    except Exception as e:
        logging.error("[%s] Error saving product data for category %s \n%s", HEADER, cat_name, e)

########################################################################################################################

# main function
if __name__ == "__main__":
    product_url_df = pd.read_csv(sys.argv[1])
    position = int(sys.argv[2])
    product_url_dict = product_url_df.to_dict("list")
    HEADER = product_url_df.columns[0]

    logging.info("========== [%s] [Crawling Start] ==========", HEADER)
    scrape_product_reviews(product_url_dict, position)
    logging.info("========== [%s] [Crawling Finish] ==========", HEADER)
