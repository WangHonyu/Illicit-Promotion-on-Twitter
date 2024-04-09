import requests
import os
import json
from tqdm import tqdm
import logging
import settings
from multiprocessing import Pool, Manager, Process

logging.basicConfig(level=logging.INFO,
                    filename="download.log",
                    format='%(asctime)s processID %(process)d [%(name)s] %(levelname)s: %(message)s',
                    datefmt="%Y-%m-%d %H:%M:%S")

def get_urls(data_path):
    logging.info("Extracting urls...")
    urls = set()
    downloaded = set()
    if os.path.exists('downloaded.txt'):
        with open('downloaded.txt', 'r') as f:
            downloaded = set([line for line in f.read().splitlines()])
    with open(data_path, 'r') as f:
        line = 0
        data = f.readline()
        while data:
            line += 1
            data = json.loads(data)
            if 'includes' in data:
                if 'media' in data['includes']:
                    for media in data['includes']['media']:
                        if media['type'] == 'video':
                            urls.add(media['variants'][0]['url'].strip('\n'))
                        elif media['type'] == 'photo':
                            urls.add(media['url'].strip('\n'))
                if 'users' in data['includes']:
                    for user in data['includes']['users']:
                        urls.add(user['profile_image_url'].strip('\n'))
            data = f.readline()
    logging.info(f"{line} responses, get {len(urls)} urls")
    return urls, downloaded

def get_media_name(media_url):
    if media_url.startswith('https://pbs.twimg.com/'):
        media_name = media_url.split('/')[-1]
    elif media_url.startswith('https://video.twimg.com'):
        media_name = media_url.split('/')[-1].split('?')[0]
    else:
        logging.info("invalid url " + media_url)
        return "invalid url"
    return media_name

def download_media(media_url, downloaded):
    media_path = settings.media_path
    media_name = get_media_name(media_url)
    if media_name.endswith(".m3u8") or os.path.exists(os.path.join(media_path, media_name)) or media_url in downloaded:
        return

    try:
        response = requests.get(media_url)
        if len(response.content) > 0:
            with open(os.path.join(media_path, media_name), "wb") as f:
                f.write(response.content)
        downloaded.add(media_url)
        if len(downloaded) % 1000 == 0:
            with open('downloaded.txt', 'w') as f:
                f.write('\n'.join(downloaded))
    except Exception as e:
        logging.error(f"Failed to download media {media_url} {e}")

def error_handler(e):
    logging.error(e)

if __name__=="__main__":
    data_path = settings.tweet_filepath
    urls, downloaded = get_urls(data_path)
    
    with Pool(processes=20) as pool:
        for url in urls:
            pool.apply_async(download_media, args=(url, downloaded, ), error_callback=error_handler)
    logging.info('Finished.')
