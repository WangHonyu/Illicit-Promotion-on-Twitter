#extract new seeds
import os, json, sys
import regex as re
from tqdm import tqdm
from multiprocessing import Pool, Manager
import argparse

def read_from_json(file):
    with open(file, 'r') as f:
        data = [json.loads(each) for each in f.readlines() if each.strip() != '']
    return data

def write2json(data, file):
    with open(file, 'w') as f:
        f.write('\n'.join([json.dumps(each, ensure_ascii=False) for each in data])+'\n')

def parse_args():
    parse = argparse.ArgumentParser(description='Searching Keyword Generator')
    parse.add_argument('-d','--data', type=str, help='The tweet file path')
    parse.add_argument('-s', '--savefile', type=str, help="The prediction result of save file path")
    parse.add_argument('-b', '--blacklist', type=str, help="Seed blacklist")
    args = parse.parse_args()
    return args

def get_blacklist(black_list_path):
    black_list_str = set()  
    black_list = read_from_json(black_list_path)
    for each in black_list:
        black_list_str.add(f"{each['seed']}_{each['type']}")
    return black_list_str

def save_seeds(seeds_str, savefile):
    seed_list = []
    for each in seeds_str:
        seed_list.append({'seed': ''.join(each.split('_')[:-1]), 'type': each.split('_')[-1]})
    write2json(seed_list, savefile)

#extract from predicted tweets
def extract_from_tweets(file, black_list_path, savefile):
    black_list_str = get_blacklist(black_list_path)
    seeds_str = set()
    tweets = read_from_json(file)
    tweets = [each for each in tweets if each['labels']]
    for tweet in tweets:
        if 'raw_data' in tweet and 'entities' in tweet['raw_data'] and 'hashtags' in tweet['raw_data']['entities']:
            for each in tweet['raw_data']['entities']['hashtags']:
                if f"{each['text']}_hashtag" not in black_list_str:
                    seeds_str.add(f"{each['text']}_hashtag")
        else:
            pattern = r"#[\p{L}_-]+"
            hashtags = re.findall(pattern, tweet['text'])
            for tag in hashtags:
                if f"{tag.strip('#')}_hashtag" not in black_list_str:
                    seeds_str.add(f"{tag.strip('#').strip()}_hashtag")
    save_seeds(seeds_str, savefile)

#extract from predicted users
def extract_from_users(file, black_list_path, savefile):
    black_list_str = get_blacklist(black_list_path)
    seeds_str = set()
    users = read_from_json(file)
    users = [each for each in users if each['labels']]
    for user in users:
        if f"{user['raw_data']['screen_name']}_account" not in black_list_str:
            seeds_str.add(f"{user['raw_data']['screen_name']}_account")
    save_seeds(seeds_str, savefile)

if __name__ == '__main__':
    args = parse_args()
    file = args.data
    savefile = args.savefile
    black_list_path = args.blacklist
    
    extract_from_tweets(file, black_list_path, savefile)
