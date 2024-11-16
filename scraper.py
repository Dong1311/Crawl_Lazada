import os
import csv
import pickle

from collections import Counter
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from tqdm import tqdm
from config import get_chrome_options, get_chrome_service

from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

# Load và lưu cookie để tránh phải đăng nhập lại
def save_cookies(driver, filename):
    with open(filename, "wb") as file:
        pickle.dump(driver.get_cookies(), file)

def load_cookies(driver, filename):
    with open(filename, "rb") as file:
        cookies = pickle.load(file)
        for cookie in cookies:
            driver.add_cookie(cookie)

def login_shopee(driver):
    # Thay `YOUR_USERNAME` và `YOUR_PASSWORD` bằng thông tin đăng nhập của bạn
    USERNAME = "YOUR_USERNAME"
    PASSWORD = "YOUR_PASSWORD"
    
    driver.get("https://shopee.vn/buyer/login")
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.NAME, "loginKey"))).send_keys(USERNAME)
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.NAME, "password"))).send_keys(PASSWORD)
    WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".shopee-button-solid"))).click()

            
def load_last_processed_index(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            return int(file.read().strip())
    except FileNotFoundError:
        return 0

def save_last_processed_index(index, filename):
    with open(filename, 'w', encoding='utf-8') as file:
        file.write(str(index))

def scrape_reviews(driver, url):
    driver.get(url)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    
    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
    )

    reviews = [] 

    try:
        # Đợi cho phần bình luận xuất hiện trên Shopee
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '.shopee-product-rating'))
        )
    except Exception:
        print(f"Không tìm thấy phần bình luận tại {url}")
        return reviews

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    
    try:
        review_elements = soup.find_all('div', class_='shopee-product-rating')

        if review_elements:
            for item in review_elements:
                review = {}

                # Số sao (rating) của bình luận
                stars_container = item.find('div', class_='shopee-rating-stars__stars')
                if stars_container:
                    star_count = len(stars_container.find_all('div', class_='icon-rating-solid--active'))
                    review['rating'] = star_count
                
                # Nội dung của bình luận
                content_element = item.find('div', class_='shopee-product-rating__content')
                review['content'] = content_element.get_text(strip=True) if content_element else 'N/A'
                
                # Thêm bình luận vào danh sách
                reviews.append(review)
    except Exception as e:
        print(f"Lỗi khi lấy dữ liệu: {e} trên trang {url}")

    return reviews



def write_to_csv(csv_filename, reviews):
    """Appends reviews to the CSV file."""
    with open(csv_filename, 'a', newline='', encoding='utf-8') as csvfile:
        csvwriter = csv.writer(csvfile)
        for review in reviews:
            if review.get('content') != 'N/A':
                cleaned_content = review.get('content', '').replace('\n', ' ').strip()
                csvwriter.writerow([review.get('rating', 'N/A'), cleaned_content])

def run_scraper():
    # options = get_chrome_options()
    # service = get_chrome_service()
    # driver = webdriver.Chrome(options=options, service=service)

    options = webdriver.ChromeOptions()
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    batch_size = 5
    csv_filename = 'reviews.csv'
    last_processed_index_file = 'last_processed_index.txt'

    last_processed_index = load_last_processed_index(last_processed_index_file)

    file_exists = os.path.exists(csv_filename)
    if not file_exists:
        with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
            csvwriter = csv.writer(csvfile)
            csvwriter.writerow(['rating', 'review'])  

    with open('urls.txt', 'r', encoding='utf-8') as file:
        urls = file.readlines()
        remaining_urls = urls[last_processed_index:]

        while remaining_urls:
            batch = remaining_urls[:batch_size]
            remaining_urls = remaining_urls[batch_size:]

            current_index = last_processed_index + len(batch)

            for url in tqdm(batch, desc="Scraping products"):
                url = url.strip()
                reviews = scrape_reviews(driver, url)  
                write_to_csv(csv_filename, reviews)  
            
            save_last_processed_index(current_index, last_processed_index_file)
            last_processed_index = current_index

    driver.quit()

if __name__ == "__main__":
    run_scraper()
