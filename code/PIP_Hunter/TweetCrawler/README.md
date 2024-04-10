## The Tweet Crawler

TwitterAPI reference: https://developer.twitter.com/en/docs/twitter-api 

### settings.py

Function: Specify the Twitter API token, file path to save responses, and the time range of crawling.



### collector.py

Function: Crawl tweets related to the given seeds within the time range from `settings.start_time` to `settings.end_time`. The seed file should contain one dict-type seed each line with at least two required domains: 
```python
#for eaxample
{"seed": "出肉" "type": "hashtag"}
{"seed": "SimonSurrey1" "type": "account"}
```

Tweets crawled down are saved in `settings.tweet_filepath` in the structure of:

```python
{
    "data": [...] # tweets
    "includes": [...] # medias and user profiles
    "meta": {...} # statistical information
}
```

Due to the Twitter API rate limit, the running process may be relatively long. Re-running after an interruption can automatically resume from the last stopped progress.

Usage: `python3 collector.py`



### download.py

Function: Download all medias (images and videos) contained in the crawled tweets to `settings.media_path`. To prevent memory overflow, the parameter `-m` can set the maximum file size (unit: bytes) that can be downloaded at one time. The default value is 50G. Downloading will stop automatically if it exceeds this size.

Usage: `python3 download.py [-m 'max_size_in_bytes']`


