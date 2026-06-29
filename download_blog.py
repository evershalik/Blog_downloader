import os
import re
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md

# ==========================================
# CHANGE THIS TO THE BLOG LINK YOU WANT
# ==========================================
TARGET_URL = "https://example-blog.com/some-post-title/"
# ==========================================

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


def slugify(text):
    """Turns a string into a clean folder/file name."""
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[-\s]+", "-", text).strip("-")


def download_blog_post(url):
    print(f"Fetching: {url}")
    response = requests.get(url, headers=HEADERS)
    if response.status_code != 200:
        print(f"Failed to load page. Status code: {response.status_code}")
        return

    soup = BeautifulSoup(response.text, "html.parser")

    # 1. Try to find the title of the post
    title_tag = (
        soup.find("h1")
        or soup.find("title")
        or soup.find(class_=re.compile("title", re.I))
    )
    title_text = title_tag.get_text().strip() if title_tag else "Untitled Post"
    folder_name = slugify(title_text)

    # Create target directories
    os.makedirs(folder_name, exist_ok=True)
    images_dir = os.path.join(folder_name, "images")
    os.makedirs(images_dir, exist_ok=True)

    # 2. Try to locate the main content body
    # Standard blogs usually place content inside article, main, or specific divs
    content_area = soup.find("article") or soup.find("main")
    if not content_area:
        content_area = soup.find(
            class_=re.compile("content|post-body|entry-content", re.I)
        )

    # Fallback to entire body if specific content area isn't found
    if not content_area:
        content_area = soup.find("body")

    # 3. Find and download all images inside the content area
    img_tags = content_area.find_all("img")
    print(f"Found {len(img_tags)} images. Downloading...")

    for idx, img in enumerate(img_tags):
        # Handle regular src, or lazy-loaded data-src/data-lazy-src attributes
        img_url = (
            img.get("src")
            or img.get("data-src")
            or img.get("data-lazy-src")
            or img.get("srcset")
        )

        if not img_url:
            continue

        # Clean up srcset if it contains multiple URLs
        if "," in img_url:
            img_url = img_url.split(",")[0].strip().split(" ")[0]

        # Convert relative URLs to absolute URLs
        img_url = urljoin(url, img_url)

        # Skip base64 encoded tracker images
        if img_url.startswith("data:image"):
            continue

        # Extract extension and create a clean filename
        parsed_img = urlparse(img_url)
        ext = os.path.splitext(parsed_img.path)[1]
        if not ext or len(ext) > 5:
            ext = ".png"  # Fallback extension

        img_filename = f"image_{idx + 1}{ext}"
        img_filepath = os.path.join(images_dir, img_filename)

        # Download the image file
        try:
            img_response = requests.get(img_url, headers=HEADERS, timeout=10)
            if img_response.status_code == 200:
                with open(img_filepath, "wb") as f:
                    f.write(img_response.content)
                # Update the HTML source to point to the local relative GitHub path
                img["src"] = f"images/{img_filename}"
                # Clear out lazy load attributes so markdownify doesn't get confused
                if img.get("srcset"):
                    del img["srcset"]
                if img.get("data-src"):
                    del img["data-src"]
            else:
                print(f"Could not download image: {img_url}")
        except Exception as e:
            print(f"Error downloading image {img_url}: {e}")

    # 4. Convert the modified HTML into clean Markdown
    markdown_text = md(str(content_area), heading_style="ATX")

    # Add a title header to the markdown file
    final_markdown = f"# {title_text}\n\nOriginal URL: {url}\n\n---\n\n{markdown_text}"

    # Save the markdown file
    md_filepath = os.path.join(folder_name, "README.md")
    with open(md_filepath, "w", encoding="utf-8") as f:
        f.write(final_markdown)

    print(f"\nSuccessfully saved everything inside the folder: '{folder_name}'")


if __name__ == "__main__":
    download_blog_post(TARGET_URL)
