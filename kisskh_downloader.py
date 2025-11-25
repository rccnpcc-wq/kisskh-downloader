import json
import time
import os
import subprocess
from urllib.parse import urlparse, parse_qs

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import WebDriverException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- CONFIGURATION ---
TIMEOUT_SECONDS = 20  
DOWNLOADER_PATH = r"C:\Users\dell\YT_DLP"  # SET THIS PATH TO YOUR YT-DLP/FFMPEG DIRECTORY
REFERER_HEADER = "https://kisskh.co/"

# Known persistent link failure overrides (Series ID: {EP ID: Working_M3U8_Link})
LINK_OVERRIDES = {
    10652: { 
        184427: "https://hls.cdnvideo11.shop/hls07/10652/Ep2.v1865_index.m3u8"
    }
}

# --- GLOBAL CONFIGURATION ---
SERIES_ID = None 
SERIES_NAME = None
TARGET_URL = None
EPISODE_IDS = {}

# Selectors
VIDEO_PLAYER_SELECTOR = "video.video"
SPINNER_OVERLAY_SELECTOR = ".spin.ng-star-inserted" 

# ----------------------------------------------------------------------
# --- 0. User Input Function ---
# ----------------------------------------------------------------------

def get_user_input():
    """Prompts the user for the series details and sets the global configuration."""
    global SERIES_ID, SERIES_NAME, TARGET_URL

    print("--- KissKH Downloader Setup ---")
    
    while True:
        url = input("Enter the full Episode 1 URL of the drama series: ").strip()
        if url.startswith("https://kisskh.co/Drama/"):
            break
        print("Invalid URL. Please enter a valid KissKH drama episode URL.")

    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    
    if 'id' in query_params and query_params['id'][0].isdigit():
        SERIES_ID = int(query_params['id'][0])
    else:
        print("FATAL: Could not extract Series ID from the URL. Please check the URL format.")
        return False
        
    TARGET_URL = url
    
    path_segments = parsed_url.path.split('/')
    try:
        title_segment = next(s for s in path_segments if s and 'Drama' not in s and 'Episode' not in s)
        SERIES_NAME = title_segment.replace('-', ' ')
    except StopIteration:
        SERIES_NAME = "Unknown_Series"
        
    print(f"\nConfiguration Set:")
    print(f"  > Series Name: {SERIES_NAME}")
    print(f"  > Series ID:   {SERIES_ID}")
    print(f"  > Target URL:  {TARGET_URL}")
    print("----------------------------\n")
    return True

# ----------------------------------------------------------------------
# --- Helper Functions ---
# ----------------------------------------------------------------------

def find_episode_list_in_logs(driver, logs):
    """Searches network logs for the series list JSON content."""
    for log_entry in logs:
        message = json.loads(log_entry['message'])
        method = message.get('message', {}).get('method')
        
        if method == 'Network.responseReceived':
            status = message['message']['params']['response']['status']
            if status >= 200 and status < 300:
                request_id = message['message']['params']['requestId']
                try:
                    response_body = driver.execute_cdp_cmd(
                        'Network.getResponseBody', {'requestId': request_id}
                    )
                    body_content = response_body.get('body')
                    
                    if body_content:
                        try:
                            data = json.loads(body_content)
                            if data.get('id') == SERIES_ID and 'episodes' in data:
                                return [{'number': item.get('number'), 'ep_id': item.get('id')} 
                                        for item in data.get('episodes', []) if item.get('number') is not None]
                                
                        except json.JSONDecodeError:
                            continue
                        
                except Exception:
                    continue
    return []

def find_m3u8_in_logs(driver, logs, ep_id):
    """Searches network logs for the specific M3U8 stream URL."""
    for log_entry in logs:
        message = json.loads(log_entry['message'])
        params = message.get('message', {}).get('params', {})
        method = message.get('message', {}).get('method')

        # --- Direct URL check ---
        url = params.get('request', {}).get('url') or params.get('response', {}).get('url')
        
        if url and url.endswith('.m3u8'):
            return url
        
        # --- Check the EpConfig JSON Response Body ---
        if method == 'Network.responseReceived':
             if url and f"Epconfig/{ep_id}" in url:
                try:
                    request_id = params['requestId']
                    response_body = driver.execute_cdp_cmd(
                        'Network.getResponseBody', {'requestId': request_id}
                    )
                    body_content = response_body.get('body')
                    if body_content:
                        config = json.loads(body_content)
                        if config.get('HlsUrl') and config.get('HlsUrl').endswith('.m3u8'):
                            return config.get('HlsUrl')
                except Exception:
                    continue
                
    return None

def robust_find_m3u8(driver, ep_id):
    """Continuously checks the logs until M3U8 link is found or timeout is reached."""
    start_time = time.time()
    while time.time() - start_time < TIMEOUT_SECONDS:
        try:
            current_logs = driver.get_log('performance') 
            link = find_m3u8_in_logs(driver, current_logs, ep_id)
            if link:
                return link
        except Exception:
            pass
        time.sleep(0.5) 
    return None

def apply_link_overrides(final_links):
    """Checks for known persistent failures and applies manual fixes."""
    if SERIES_ID in LINK_OVERRIDES:
        overrides = LINK_OVERRIDES[SERIES_ID]
        
        for ep_num, ep_id in EPISODE_IDS.items(): 
            if ep_id in overrides:
                current_link = final_links.get(ep_num)
                if current_link and not current_link.endswith('.m3u8'):
                    final_links[ep_num] = overrides[ep_id]
                    print(f"-> Manual OVERRIDE applied for Episode {ep_num} (EP ID: {ep_id}). Link secured.")
    return final_links

def run_bulk_download(final_links, download_folder):
    """Executes yt-dlp for all M3U8 links found."""
    print("\n--- Starting BULK DOWNLOAD Execution ---")
    
    # Change CWD to where download tools (yt-dlp, ffmpeg) are located
    original_cwd = os.getcwd()
    os.chdir(DOWNLOADER_PATH)
    
    # Create the output folder if it doesn't exist
    output_dir = os.path.join(original_cwd, download_folder)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    try:
        sorted_links = sorted(final_links.items())

        for i, (ep_num, stream_link) in enumerate(sorted_links, 1):
            
            if not stream_link.endswith('.m3u8'):
                print(f"\n--- Skipping Episode {ep_num} (Link not M3U8) ---")
                continue

            output_filename = f"{SERIES_NAME} - S01E{int(ep_num):02d}.mp4"
            output_path = os.path.join(output_dir, output_filename)
            
            command = [
                'yt-dlp',
                '--referer', REFERER_HEADER,
                stream_link,
                '--concurrent-fragments', '10',  # <-- NEW: Maximize Speed (10 connections)
                '--paths', DOWNLOADER_PATH,       # <-- NEW: Provide path for ffmpeg/ffprobe
                '-o', output_path
            ]

            print(f"\n--- Downloading Episode {ep_num} (File: {output_filename}) ---")
            
            # Execute the command
            subprocess.run(command, capture_output=False, text=True, bufsize=1, universal_newlines=True)

    except Exception as e:
        print(f"\nAn error occurred during the download process: {e}")
    finally:
        # Restore the original working directory
        os.chdir(original_cwd)
        print("Download process finished.")

# ----------------------------------------------------------------------
# --- 1. Master Function to Get ALL Episode IDs and Stream Links ---
# ----------------------------------------------------------------------

def get_stream_links_via_monitoring():
    """
    Loads the page, discovers all episode IDs, and then iterates through 
    each episode URL to find and capture the stream link using timed retry.
    """
    global EPISODE_IDS
    print(f"-> Starting Chrome Driver for Stream Link Monitoring.")
    
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.set_capability("goog:loggingPrefs", {'performance': 'ALL'})
    
    driver = None
    final_links = {}

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        wait = WebDriverWait(driver, 20)
        
        # --- PHASE 1: Discover Episode IDs ---
        driver.get(TARGET_URL)
        print("-> Waiting for page to load and security check to pass...")
        time.sleep(5) 
        
        # Click video player on the first episode to get the list JSON and a good session
        try:
            print("-> Attempting to click the video player to trigger network events...")
            wait.until(EC.invisibility_of_element_located((By.CSS_SELECTOR, SPINNER_OVERLAY_SELECTOR)))
            video_player = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, VIDEO_PLAYER_SELECTOR)))
            driver.execute_script("arguments[0].click();", video_player)
            time.sleep(5) 
        except Exception:
            print(f"Warning: Failed to click video player on Ep 1. Proceeding with monitoring.")
            time.sleep(10)
        
        print("-> Searching network logs for Episode List JSON...")
        logs = driver.get_log('performance')
        
        episode_list = find_episode_list_in_logs(driver, logs)
        if not episode_list:
             print("-> FATAL: Could not confirm EPISODE LIST JSON. Cannot proceed.")
             return {}
        
        EPISODE_IDS = {item['number']: item['ep_id'] for item in episode_list}
        print(f"-> SUCCESS! Discovered {len(EPISODE_IDS)} episodes.")
        
        # --- PHASE 2: Fetch stream link for each episode ID with Robust Wait ---
        print(f"\n-> Starting network monitor search for stream links.")

        sorted_episodes = sorted(EPISODE_IDS.items())

        for ep_num, ep_id in sorted_episodes:
            
            episode_url = f"https://kisskh.co/Drama/{SERIES_NAME.replace(' ', '-')}/Episode-{ep_num}?id={SERIES_ID}&ep={ep_id}&page=0&pageSize=100"
            driver.get(episode_url)
            print(f"Episode {ep_num} (EP ID: {ep_id}): Navigating...", end=" ")
            
            time.sleep(2) 
            
            # Attempt to click the video player 
            try:
                wait.until(EC.invisibility_of_element_located((By.CSS_SELECTOR, SPINNER_OVERLAY_SELECTOR)))
                video_player = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, VIDEO_PLAYER_SELECTOR)))
                driver.execute_script("arguments[0].click();", video_player)
            except Exception:
                pass 
            
            # Robustly check logs in a loop for the M3U8 link
            stream_link = robust_find_m3u8(driver, ep_id)

            if stream_link:
                final_links[ep_num] = stream_link
                print("-> SUCCESS! Stream Link Found.")
            else:
                final_links[ep_num] = episode_url 
                print("-> FAILED to find stream link in logs. (Saving HTML page URL as fallback)")
            
            time.sleep(0.5) 
            
        return final_links

    except WebDriverException as e:
        print(f"\nFATAL ERROR: WebDriver failed: {e}")
        return {}
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        return {}
    finally:
        if driver:
            driver.quit()
            print("\n-> Chrome Driver closed.")

# ----------------------------------------------------------------------
# --- Main Execution ---
# ----------------------------------------------------------------------

if __name__ == "__main__":
    
    if not get_user_input():
        print("Script terminated due to invalid input.")
    else:
        # 1. Run the link finding process
        final_links = get_stream_links_via_monitoring()
        
        # 2. Apply known overrides
        final_links = apply_link_overrides(final_links)
        
        # --- Final Output ---
        if not final_links:
            print("\nFATAL: Failed to retrieve any valid links.")
        else:
            download_folder = SERIES_NAME.replace(" ", "_").replace(":", "_")
            if not os.path.exists(download_folder):
                os.makedirs(download_folder)

            LINKS_FILE = os.path.join(download_folder, "final_links.txt")
            
            print("\n--- Final Link List ---")
            print(f"Links saved to '{LINKS_FILE}'")
            
            # Save final list to file
            with open(LINKS_FILE, 'w') as f:
                for ep_num in sorted(final_links.keys()):
                    link = final_links[ep_num]
                    link_type = "STREAM (M3U8)" if link.endswith('.m3u8') else "HTML PAGE (FALLBACK)"
                    
                    full_line = f"Episode {ep_num} ({link_type}): {link}"
                    print(full_line)
                    f.write(link + '\n')
            
            # 3. Execute the download
            print("\nStarting bulk download...")
            run_bulk_download(final_links, download_folder)