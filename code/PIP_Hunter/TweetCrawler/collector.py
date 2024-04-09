import requests
import json
import time
import settings
import logging
import datetime
import os
import sys
import re
import threading

logging.basicConfig(level=logging.INFO,
                    filename="runtime.log",
                    format="%(asctime)s - %(levelname)s - %(filename)s : %(lineno)s line - %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S")
logging.Formatter.converter = time.localtime
logger = logging.getLogger(__name__)

lock = threading.Lock()

def get_seeds():
    # restore from last crawl
    restore = {}
    logger.info("Restoring...")
    
    ## get the remaining quota
    if os.path.exists('runtime.log'):
        with open('runtime.log', 'r') as f:
            tmp = f.read().splitlines()[-1]
            q = re.findall('quota=[1-9]\d*', tmp)
            if len(q):
                restore['quota'] = int(re.split('quota=', q[0])[1])
            else:
                restore['quota'] = 0
    else:
        restore['quota'] = 0
    ## get the last crawled seed
    if os.path.exists(settings.tweet_filepath): 
        with open(settings.tweet_filepath, 'r') as f:
            last = f.readline()
            second = None
            while last:
                second = last
                last = f.readline()
            second = json.loads(second)
            if 'next_token' in second['meta']:
                restore['next_token'] = second['meta']['next_token']
                restore['next_seed'] = second['meta']['seed_info']
            else:
                restore['next_token'] = None
                restore['next_seed'] = second['meta']['seed_info']
    else:
        restore['next_token'] = None
        restore['next_seed'] = None
    logger.info(f"Restore: quota={restore['quota']}, next_token={restore['next_token']}, next_seed={restore['next_seed']}")

    # get seeds that haven't been crawled
    with open(settings.seed_filepath, 'r') as f:
        data = [json.loads(each) for each in f.read().splitlines()]
        if restore['next_seed'] is None:
            restore['seeds'] = data
        else:
            for idx, line in enumerate(data):
                if line['seed'] == restore['next_seed']['seed'] and line['type'] == restore['next_seed']['type']:
                    if restore['next_token'] is None:
                        restore['seeds'] = data[idx+1:len(data)]
                        restore['searched_seeds'] = data[0:idx]
                    else:
                        restore['seeds'] = data[idx:len(data)]
                        restore['searched_seeds'] = data[0:idx-1]
                    break
    logger.info(f"{len(restore['seeds'])} seeds, {len(restore['searched_seeds'])} searched_seeds. ")
    return restore

class Collector(threading.Thread):
    def __init__(self, quota, seeds, searched_seeds, next_token=None):
        super(Collector, self).__init__()
        self.bearer_token = settings.bearer_token
        self.search_url = "https://api.twitter.com/2/tweets/search/all"
        self.start_time = settings.start_time
        self.end_time = settings.end_time
        self.tweets_filepath = settings.tweet_filepath
        self.seeds_filepath = settings.seed_filepath
        self.next_token = next_token
        self.quota = quota
        self.seeds = seeds
        self.searched_seeds = searched_seeds

    def bearer_oauth(self, r):
        """
        Method required by bearer token authentication.
        """

        r.headers["Authorization"] = f"Bearer {self.bearer_token}"
        r.headers["User-Agent"] = "v2FullArchiveSearchPython"
        return r

    def connect_to_endpoint(self, params):
        response = requests.request("GET", self.search_url, auth=self.bearer_oauth, params=params)
        # print(f"status code: {response.status_code}"))
        
        while response.status_code == 429: #if rate limit exceeded, wait until recovery
            logger.info(f"{self.getName()}: Waiting due to rate limit...")
            time.sleep(30)
            response = requests.request("GET", self.search_url, auth=self.bearer_oauth, params=params)
        if response.status_code != 200:
            logger.debug(Exception(response.status_code, response.text))
            raise Exception(response.status_code, response.text)
        return response.json()

    def query(self, seed, next_token=None):
        ##generate query string
        if seed['type'] == 'hashtag':
            qry = "#" + re.sub(r'^[ #\n]*|[ #\n]*$', '', seed['seed']) + " -is:retweet -is:reply"
        elif seed['type'] == 'account':
            qry = f"from:{seed['seed']} -is:retweet -is:reply"
        else:
            qry = f"{seed['seed']} -is:retweet -is:reply"
        
        ## query API
        ## Optional params: start_time,end_time,since_id,until_id,max_results,next_token,
        ## expansions,tweet.fields,media.fields,poll.fields,place.fields,user.fields
        query_params = {'query': qry,
                        'start_time': self.start_time,
                        'end_time': self.end_time,
                        'next_token': next_token,
                        'max_results': 500,
                        'tweet.fields': 'author_id,created_at,lang,public_metrics',
                        'expansions': 'attachments.media_keys,author_id',
                        'media.fields': 'media_key,type,url,preview_image_url,variants',
                        'user.fields': 'created_at,description,profile_image_url,url'}
        response = self.connect_to_endpoint(query_params)
        return response

    def run(self):
        request_cnt = 1
        while len(self.seeds):
            lock.acquire()
            seed = self.seeds[0]
            self.seeds.remove(seed)
            lock.release()
            tweet_cnt = 0
            zero_count = 0
            self.start_time = settings.start_time
            self.end_time = settings.end_time
            seed['start_time'] = settings.start_time
            seed['end_time'] = settings.end_time
            
            # crawling policy: for each seed, keep crawling until more than 100 tweets are crawled,
            #         except that the seed is unactive for more than 50 requests(which is 1 year)
            while tweet_cnt < 100 and zero_count <= 50:
                logger.info(f"{self.getName()}: Search by {seed} from {self.start_time} to {self.end_time}, quota={self.quota}")
                seed['start_time'] = self.start_time
                response = self.query(seed, next_token=self.next_token)
                response['meta']['seed_info'] = seed
                with open(self.tweets_filepath, 'a') as f:
                    print(json.dumps(response, sort_keys=True, ensure_ascii=False), file=f)
                tweet_cnt += response['meta']['result_count']
                self.quota += response['meta']['result_count']
                if response['meta']['result_count'] == 0:
                    zero_count += 1
                else:
                    zero_count = 0
                if 'data' in response:
                    print(f"{self.getName()}: {request_cnt}th request, {tweet_cnt} tweets collected. Time: {response['data'][-1]['created_at']}")
                else:
                    print(f"{self.getName()}: {request_cnt}th request, {tweet_cnt} tweets collected.")
                while ('next_token' in response ['meta']):
                    response = self.query(seed, next_token=response['meta']['next_token'])
                    response['meta']['seed_info'] = seed
                    with open(self.tweets_filepath, 'a') as f:
                        print(json.dumps(response, sort_keys=True, ensure_ascii=False), file=f)
                    tweet_cnt += response['meta']['result_count']
                    self.quota += response['meta']['result_count']
                    if response['meta']['result_count'] == 0:
                        zero_count += 1
                    if 'data' in response:
                        print(f"{self.getName()}: {request_cnt}th request, {tweet_cnt} tweets collected. Time: {response['data'][-1]['created_at']}")
                    else:
                        print(f"{self.getName()}: {request_cnt}th request, {tweet_cnt} tweets collected.")
                self.start_time = (datetime.datetime.strptime(self.start_time, "%Y-%m-%dT00:00:00.00Z") + datetime.timedelta(days=-7)).strftime("%Y-%m-%dT00:00:00.00Z")
                self.end_time = (datetime.datetime.strptime(self.end_time, "%Y-%m-%dT23:59:59.59Z") + datetime.timedelta(days=-7)).strftime("%Y-%m-%dT23:59:59.59Z")

            response['meta']['total_count'] = tweet_cnt
            self.searched_seeds.append(seed)
            with open('searched_seeds.json', 'w') as fs:
                fs.write('\n'.join(json.dumps(each, sort_keys=True, ensure_ascii=False) for each in self.searched_seeds))
            logger.info(f"{self.getName()}: {seed} has {tweet_cnt} tweets in total, quota={self.quota}")

if __name__ == "__main__":
    restore = get_seeds()
    thread_count = settings.thread_count
    threads = []
    if restore['next_token'] is not None:
        threads.append(Collector(
            quota=restore['quota'],
            seeds=[restore['seeds'][0]], 
            searched_seeds=restore['searched_seeds'], 
            next_token=restore['next_token']))
        restore['seeds'] = restore['seeds'][1:]
        for i in range(thread_count - 1):
            threads.append(Collector(
                quota=restore['quota'],
                seeds=restore['seeds'], 
                searched_seeds=restore['searched_seeds']))
    else:
        for i in range(thread_count):
            threads.append(Collector(
                quota=restore['quota'],
                seeds=restore['seeds'], 
                searched_seeds=restore['searched_seeds']))
    for thread in threads:
        thread.start()
