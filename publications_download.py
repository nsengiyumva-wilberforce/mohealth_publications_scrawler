import requests
from bs4 import BeautifulSoup
import os
import re

# Base URL
base_url = "https://library.health.go.ug"

# Function to sanitize filename
def sanitize_filename(filename):
    # Remove invalid characters for filenames
    return re.sub(r'[\/:*?"<>|]', '_', filename).strip()

# Directory to save downloads
download_dir = "downloaded_pdfs"
os.makedirs(download_dir, exist_ok=True)

# Loop through pages 0 to 2 (first page no ?page, then ?page=1, ?page=2)
for page in range(3):
    if page == 0:
        page_url = f"{base_url}/publications"
    else:
        page_url = f"{base_url}/publications?page={page}"
    
    print(f"Fetching page: {page_url}")
    
    # Fetch the page content, disabling SSL verification due to expired certificate
    response = requests.get(page_url, verify=False)
    if response.status_code != 200:
        print(f"Failed to fetch {page_url}")
        continue
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find all document rows
    rows = soup.find_all('div', class_='row my-4 border-bottom g-0 pt-2 pb-4 mx-3 mx-md-0')
    
    for row in rows:
        # Extract title
        title_elem = row.find('div', class_='results_title my-2 text-dark')
        if title_elem and title_elem.a:
            title = title_elem.a.text.strip()
        else:
            title = "unknown"
        
        # Extract download link
        download_elem = row.find('a', class_='btn download-btn')
        if download_elem and 'href' in download_elem.attrs:
            download_href = download_elem['href']
            download_url = base_url + download_href
            
            # Sanitize and create filename
            filename = sanitize_filename(title) + ".pdf"
            file_path = os.path.join(download_dir, filename)
            
            if os.path.exists(file_path):
                print(f"File already exists: {filename}")
                continue
            
            print(f"Downloading: {title} from {download_url}")
            
            # Download the PDF, disabling SSL verification
            pdf_response = requests.get(download_url, stream=True, verify=False)
            if pdf_response.status_code == 200:
                with open(file_path, 'wb') as f:
                    for chunk in pdf_response.iter_content(chunk_size=8192):
                        f.write(chunk)
                print(f"Saved: {filename}")
            else:
                print(f"Failed to download {download_url}")
        else:
            print(f"No download link found for {title}")

print("Download complete!")