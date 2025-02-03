from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
from selenium.webdriver.chrome.options import Options
import csv
from time import sleep
import random
import json

def setup_driver():
    options = Options()
    # Remove headless mode for debugging
    # options.add_argument('--headless=new')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-notifications')
    
    # Add more realistic user agent
    user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    options.add_argument(f'user-agent={user_agent}')
    
    driver = uc.Chrome(options=options)
    # Additional stealth settings
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

def save_debug_info(html_content, page_number):
    """Save the HTML content for debugging"""
    with open(f'debug_page_{page_number}.html', 'w', encoding='utf-8') as f:
        f.write(html_content)

def extract_profiles(driver, page_source, page_number):
    soup = BeautifulSoup(page_source, 'html.parser')
    
    # Save debug info
    save_debug_info(page_source, page_number)
    
    # Print all unique class names found for debugging
    all_classes = set()
    for tag in soup.find_all(class_=True):
        all_classes.update(tag.get('class', []))
    
    print("\nDebug: Found these classes:")
    print(json.dumps(list(all_classes), indent=2))
    
    # Try multiple different selectors for search results
    search_results = []
    
    # Common container patterns
    selectors = [
        'div.search-results-container li',
        'li.reusable-search__result-container',
        'li.search-result',
        'div[data-test-search-result]',
        '.search-results__list-item'
    ]
    
    for selector in selectors:
        try:
            results = soup.select(selector)
            if results:
                print(f"\nFound {len(results)} results using selector: {selector}")
                search_results = results
                break
        except Exception as e:
            print(f"Error with selector {selector}: {str(e)}")
    
    if not search_results:
        print("\nNo results found with any selector!")
        # Save the current page source for manual inspection
        with open(f'failed_page_{page_number}.html', 'w', encoding='utf-8') as f:
            f.write(page_source)
        return []

    profiles = []
    for result in search_results:
        try:
            profile = {}
            
            # Debug print the HTML of each result
            print("\nDebug: Processing result HTML:")
            print(result.prettify()[:500])  # Print first 500 chars for brevity
            
            # Try multiple selectors for each field
            name_selectors = [
                'span[aria-hidden="true"]',
                'span.name',
                'span.actor-name',
                'a.app-aware-link > span',
                '.entity-result__title-text > a'
            ]
            
            for selector in name_selectors:
                name_element = result.select_one(selector)
                if name_element:
                    profile['Name'] = name_element.get_text(strip=True)
                    print(f"Found name using selector: {selector}")
                    break
            
            # Similar approach for other fields...
            link_selectors = [
                'a.data-test-app-aware-link',
                'a[class="KprJpWqBczopqatsFUTNnABBalZLkNjhjOnIg"]'
            ]
            
            for selector in link_selectors:
                link_element = result.select_one(selector)
                if link_element and link_element.get('href'):
                    profile['Profile Link'] = link_element['href'].split('?')[0]
                    print(f"Found link using selector: {selector}")
                    break

            jobtitle_selector=[
                'div[class="zWtZUbHsGMETHzjxfLLmbKVDzBrFaEtmhEY t-14 t-black t-normal"]'
            ]
            
            for selector in jobtitle_selector:
                jobtitle_element = result.select_one(selector)
                if jobtitle_element:
                    profile['Job Title'] = jobtitle_element.get_text(strip=True)
                    print(f"Found job title using selector: {selector}")
                    break
            
            location_selector=[
                'div[class="ecukOCgrnCAeLUvTkwaZsGUzlVMoRIMyzptQ t-14 t-normal"]'
            ]

            for selector in location_selector:
                location_element = result.select_one(selector)
                if location_element:
                    profile['Location'] = location_element.get_text(strip=True)
                    print(f"Found location using selector: {selector}")
                    break
                
            # If we found any valid data, add the profile
            if profile.get('Name') and profile.get('Name') != "LinkedIn Member":
                profiles.append(profile)
            else:
                print("Debug: Failed to extract valid profile data")
            
        except Exception as e:
            print(f"Error extracting individual profile: {str(e)}")
            continue
    
    return profiles

def login_to_linkedin(driver, username, password):
    try:
        driver.get("https://www.linkedin.com/login")
        print("Waiting for login page...")
        
        # Wait for login page and screenshot it
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "username")))
        driver.save_screenshot("login_page.png")
        
        sleep(random.uniform(2, 4))
        
        # Find and fill username
        username_field = driver.find_element(By.ID, "username")
        for char in username:
            username_field.send_keys(char)
            sleep(random.uniform(0.1, 0.3))
        
        sleep(random.uniform(1, 2))
        
        # Find and fill password
        password_field = driver.find_element(By.ID, "password")
        for char in password:
            password_field.send_keys(char)
            sleep(random.uniform(0.1, 0.3))
        
        sleep(random.uniform(1, 2))
        
        # Click login
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        
        # Wait for feed to load and screenshot it
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[class*='feed-identity-module']"))
        )
        driver.save_screenshot("after_login.png")
        
        print("Login successful")
        return True
        
    except Exception as e:
        print(f"Login failed: {str(e)}")
        driver.save_screenshot("login_error.png")
        return False

def scrape_linkedin_profiles(linkedin_url, username, password, num_pages=1):
    driver = setup_driver()
    
    try:
        if not login_to_linkedin(driver, username, password):
            return
        
        sleep(random.uniform(3, 5))
        
        with open('linkedin_profiles.csv', 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['Name', 'Profile Link', 'Job Title', 'Location']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for page_number in range(1, num_pages + 1):
                page_url = f"{linkedin_url}&page={page_number}"
                print(f"\nAccessing page {page_number}: {page_url}")
                
                try:
                    driver.get(page_url)
                    sleep(random.uniform(3, 5))
                    
                    # Scroll slowly down the page
                    total_height = int(driver.execute_script("return document.body.scrollHeight"))
                    for i in range(1, total_height, 100):
                        driver.execute_script(f"window.scrollTo(0, {i});")
                        sleep(0.1)
                    
                    # Take screenshot of the page
                    driver.save_screenshot(f"page_{page_number}.png")
                    
                    # Extract profiles with debug info
                    profiles = extract_profiles(driver, driver.page_source, page_number)
                    print(f"Found {len(profiles)} valid profiles on page {page_number}")
                    
                    for profile in profiles:
                        writer.writerow(profile)
                        print(f"Saved profile: {profile['Name']}")
                    
                except Exception as e:
                    print(f"Error processing page {page_number}: {str(e)}")
                    driver.save_screenshot(f"error_page_{page_number}.png")
                    continue
                
                sleep(random.uniform(4, 6))
    
    finally:
        driver.quit()

# Example usage
if __name__ == "__main__":
    linkedin_url = "https://www.linkedin.com/search/results/people/?keywords=data%20scientist&origin=SWITCH_SEARCH_VERTICAL&sid=Gq3"
    username = "dhureengul@gmail.com"
    password = "Dhureen20"
    scrape_linkedin_profiles(linkedin_url, username, password)