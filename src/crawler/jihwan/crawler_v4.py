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

########################################################################################################################

def extract_element_text(driver, parent_element, css_selector, url, timeout=10):
    try:
        WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, css_selector))
        )
    except TimeoutException as e:
        logging.error("%s exception for %s at %s", type(e).__name__, css_selector, url)
    return extract_with_error_handling(
        lambda: parent_element.find_element(By.CSS_SELECTOR, css_selector).text.strip(),
        css_selector,
        url,
        default=None
    )

def extract_element(driver, parent_element, css_selector, url, timeout=10):
    try:
        WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, css_selector))
        )
    except TimeoutException as e:
        logging.error("%s exception for %s at %s", type(e).__name__, css_selector, url)
    return extract_with_error_handling(
        lambda: parent_element.find_element(By.CSS_SELECTOR, css_selector),
        css_selector,
        url,
        default=None
    )

def extract_element_text_list(driver, parent_element, css_selector, url, timeout=10):
    try:
        WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, css_selector))
        )
    except TimeoutException as e:
        logging.error("%s exception for %s at %s", type(e).__name__, css_selector, url)
    return extract_with_error_handling(
        lambda: [flag.text.strip() for flag in parent_element.find_elements(By.CSS_SELECTOR, css_selector)],
        css_selector,
        url,
        default=[]
    )

def extract_element_list(driver, parent_element, css_selector, url, timeout=10):
    try:
        WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, css_selector))
        )
    except TimeoutException as e:
        logging.error("%s exception for %s at %s", type(e).__name__, css_selector, url)
    return extract_with_error_handling(
        lambda: [element for element in parent_element.find_elements(By.CSS_SELECTOR, css_selector)],
        css_selector,
        url,
        default=[]
    )

def extract_with_error_handling(extraction_func, css_selector, url, default=None):
    try:
        result = extraction_func()
        logging.info(f"[extract_with_error_handling] The result is {result}")
        return extraction_func()
    except (NoSuchElementException, TimeoutException, StaleElementReferenceException) as e:
        logging.error("%s exception for %s at %s", type(e).__name__, css_selector, url)
    except Exception as e:
        logging.error("Unexpected error for %s at %s: \n%s", css_selector, url, e)
    return default

########################################################################################################################

def extract_product_info(driver, url):
    logging.info("[extract_product_info] Start")
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
        logging.error("Error extracting product info from %s \n%s", url, e)

    product_info = driver.find_element(By.CSS_SELECTOR, "div.right_area > div.prd_info")
    product_social_info = driver.find_element(By.CSS_SELECTOR, "div.left_area > div.prd_social_info")

    brand_name = extract_element_text(driver, product_info, "p.prd_brand", url)
    product_name = extract_element_text(driver, product_info, "p.prd_name", url)
    product_flags = extract_element_text_list(driver, product_info, "p.prd_flag span", url)

    review_cnt_txt = extract_element_text(driver, product_social_info, "p#repReview > em", url)
    review_cnt = int(review_cnt_txt.strip("()").strip("건").replace(",", ""))
    overall_rating = float(extract_element_text(driver, product_social_info, "p#repReview > b", url))


    logging.info("[extract_product_info] Finished with: brand_name=%s, product_name=%s, review_cnt=%d, overall_rating=%f",
                 brand_name, product_name, review_cnt, overall_rating)

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
        logging.info("[extract_ingredients] START")

        element = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "li#buyInfo"))
        )
        element.click()
        logging.info("The ingredient tab has been successfully clicked")

    except (NoSuchElementException, TimeoutException, StaleElementReferenceException) as e:
        logging.error("%s occurred while extracting ingredients for %s \n%s", type(e).__name__, url, e)
    except Exception as e:
        logging.error("Unexpected error while extracting ingredients for %s \n%s", url, e)

        # WebDriverWait(driver, 10).until(
        #     EC.visibility_of_all_elements_located((By.CSS_SELECTOR, "div#artcInfo > dl.detail_info_list"))
        # )

        product_info_list = extract_element_text_list(driver, driver, "div#artcInfo > dl.detail_info_list", url)

        for product_info in product_info_list[1:]:
            dt_text = extract_element_text(driver, product_info, "dt", url)
            if dt_text == "화장품법에 따라 기재해야 하는 모든 성분":
                ingredients = extract_element_text(driver, product_info, "dd", url)
                logging.info("[extract_ingredients] FINISH")
                return ingredients

        logging.warning("No ingredient information found for %s", url)

    error_list["url"].append(url)
    error_list["reason"].append("ingredients error")
    return None

########################################################################################################################

def extract_reviews(driver, product_info):
    logging.info("[extract_reviews] START")

    review_info_dict = defaultdict(list)

    try:
        element = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "li#reviewInfo"))
        )
        element.click()
        logging.info("The review tab has been successfully clicked")

        WebDriverWait(driver, 10).until(
            EC.visibility_of_all_elements_located((By.CSS_SELECTOR, "div.review_list_wrap"))
        )

    except (NoSuchElementException, TimeoutException, StaleElementReferenceException) as e:
        logging.error("%s occurred while preparing reviews for %s \n%s", type(e).__name__, product_info["url"], e)
        error_list["url"].append(product_info["url"])
        error_list["reason"].append("review count error")
        return review_info_dict
    except Exception as e:
        logging.error("Unexpected %s occurred while preparing reviews for %s \n%s", type(e).__name__, product_info["url"], e)
        error_list["url"].append(product_info["url"])
        error_list["reason"].append("review count error")
        return review_info_dict

    pages = min(100, (product_info["review_cnt"] // 10) + 1)
    for page in tqdm(range(1, pages + 1), desc="Page", position=1, leave=False):
        try:
            if page != 1:
                next_page_element = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, f"div.pageing > a[data-page-no='{page}']"))
                )
                next_page_element.click()
                logging.info("The next review page button has been successfully clicked")
                time.sleep(1.5)
        except (NoSuchElementException, TimeoutException, StaleElementReferenceException) as e:
            logging.error("%s occurred while navigating to page %d for %s \n%s", type(e).__name__, page, product_info["url"], e)
            error_list["url"].append(product_info["url"])
            error_list["reason"].append(f"navigating to page error on {page}")
        except Exception as e:
            logging.error("Unexpected %s occurred while navigating to page %d for %s \n%s", type(e).__name__, page, product_info["url"], e)
            error_list["url"].append(product_info["url"])
            error_list["reason"].append(f"navigating to page error on {page}")

        review_list = extract_element_list(driver, driver, "div.review_list_wrap > ul#gdasList > li", product_info["url"])

        for idx, review in enumerate(review_list):
            try:
                WebDriverWait(driver, 10).until(
                    EC.visibility_of_all_elements_located((By.CSS_SELECTOR, "div#Contents div.review_wrap div.info > div.user > p.info_user"))
                )
                WebDriverWait(driver, 10).until(
                    EC.visibility_of_all_elements_located((By.CSS_SELECTOR, "div#Contents div.review_wrap div.review_cont > div.txt_inner"))
                )
                
            except (NoSuchElementException, TimeoutException, StaleElementReferenceException) as e:
                logging.error("%s occurred while extracting review[%d] on page %d for %s \n%s", type(e).__name__, idx, page, product_info["url"], e)
                error_list["url"].append(product_info["url"])
                error_list["reason"].append(f"extracting review error review[{idx}] on page {page}")
            except Exception as e:
                logging.error("Unexpected %s occurred while extracting review[%d] on page %d for %s \n%s", type(e).__name__, idx, page, product_info["url"], e)
                error_list["url"].append(product_info["url"])
                error_list["reason"].append(f"extracting review error review[{idx}] on page {page}")

            # User Information
            user_info = extract_element(driver, review, "div.info > div.user", product_info["url"])
            
            user_link = extract_element(driver, user_info, "p.info_user > a.id", product_info["url"])
            user_code_match = re.search(r"'([A-Za-z0-9+/=]+)'", user_link.get_attribute("onclick"))
            user_code = user_code_match.group(1) if user_code_match else None
            logging.info("User Code is %s", user_code)
            
            user_id = extract_element_text(driver, user_info, "p.info_user > a.id", product_info["url"])
            logging.info("User ID is %s", user_id)

            user_skin_type = extract_element_text_list(driver, user_info, "p.tag > span", product_info["url"])
            user_skin_type = ",".join(user_skin_type)
            logging.info("User Skin Type is %s", user_skin_type)
            
            user_tag_list = extract_element_text_list(driver, user_info, "div.badge > a.point_flag", product_info["url"])
            user_tag = ",".join(user_tag_list)
            logging.info("User Tag is %s", user_tag)


            # Review Information
            review_info = extract_element(driver, review, "div.review_cont", product_info["url"])
            
            review_rating = extract_element_text(driver, review_info, "div.score_area > span.review_point > span.point", product_info["url"])
            logging.info("Review Rating is %s", review_rating)
            
            review_date = extract_element_text(driver, review_info, "div.score_area > span.date", product_info["url"])
            logging.info("Review Date is %s", review_date)

            purchase_channel = extract_element_text(driver, review_info, "div.score_area > span.ico_offlineStore", product_info["url"]) or "온라인"
            logging.info("The place item puchased is %s", purchase_channel)

            review_poll = {}
            poll_samples = extract_element_list(driver, review_info, "div.poll_sample dl.poll_type1", product_info["url"])
            for poll_sample in poll_samples:
                poll_question = extract_element_text(driver, poll_sample, "dt", product_info["url"])
                poll_answer = extract_element_text(driver, poll_sample, "dd", product_info["url"])
                review_poll[poll_question] = poll_answer
            logging.info("Review poll is %s", review_poll)

            review_text = extract_element_text(driver, review_info, "div.txt_inner", product_info["url"])
            logging.info("User Review is %s", review_text)

            recommend_num = extract_element_text(driver, review_info, "div.recom_area button span.num", product_info["url"])
            logging.info("Times the review recommended is %s", recommend_num)


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

                
        
        

    logging.info("[extract_reviews] FINISH")

    return review_info_dict

########################################################################################################################

def scrape_product_reviews(product_url_dict):
    reviewer_list = set()
    product_info_dict = defaultdict(list)
    product_num = 0

    cat_name, product_urls = product_url_dict.popitem()

    for url in tqdm(product_urls, desc="URL", position=0):
        # try:
        with webdriver.Chrome(service=service, options=chrome_options) as driver:
            driver.get(url)

            product_info = extract_product_info(driver, url)
            ingredients = extract_ingredients(driver, url)
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

            time.sleep(2)

            try:
                os.makedirs(f"../../data/reviews/{cat_name}", exist_ok=True)
                pd.DataFrame(reviews).to_csv(f"../../data/reviews/{cat_name}/{cat_name}_{product_num}_reviews.csv", index=False)
                logging.info("Safely saved reviews for %s", product_info["product_name"])
            except Exception as e:
                logging.error("Error saving reviews for %s_%s \n%s", cat_name, product_info["product_name"], e)
            finally:
                product_num += 1

        # except Exception as e:
        #     logging.error("Unexpected %s occurred while processing URL %s in category %s \n%s", 
        #                   type(e).__name__, url, cat_name, e)

    try:
        pd.DataFrame(product_info_dict).to_csv(f"../../data/products/{cat_name}.csv", index=False)
        logging.info("Safely saved product data for category %s", cat_name)
    except Exception as e:
        logging.error("Error saving product data for category %s \n%s", cat_name, e)

    try:
        pd.DataFrame(list(reviewer_list), columns=["user_code"]).to_csv(f"../../data/{cat_name}_reviewers.csv", index=False)
        logging.info("Safely saved reviewer data for category %s", cat_name)
    except Exception as e:
        logging.error("Error saving reviewer data for category %s \n%s", cat_name, e)

########################################################################################################################

# main function
if __name__ == "__main__":
    product_url_dict = pd.read_csv(sys.argv[1]).to_dict("list")
    try:
        scrape_product_reviews(product_url_dict)
    finally:
        pd.DataFrame(error_list).to_csv("../../data/error/error_list.csv", index=False)
