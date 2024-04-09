from paddlenlp import Taskflow
import emojiswitch
import re
import argparse
import json
import logging
import pandas as pd
import numpy as np
from simpletransformers.ner import NERModel, NERArgs
import sys
import settings
import filter_contact
import requests
logger = logging.getLogger(__name__)
transformers_logger = logging.getLogger("transformers")
transformers_logger.setLevel(logging.WARNING)
NER_model_path = settings.NER_model_path
seg = Taskflow("word_segmentation", mode="fast")

url_pattern = re.compile(r"(https?|ftp|file)://[-A-Za-z0-9+&@#/%?=~_|!:,.;]+[-A-Za-z0-9+&@#/%=~_|]")

def write2jsonfile(data,filename):
    with open(filename, 'a+') as f:
        for line in data:
            f.write(json.dumps(line, ensure_ascii=False))
            f.write("\n")

def read_from_json(file):
    with open(file, 'r') as f:
        data = [json.loads(each) for each in f.readlines() if each.strip() != '']
    return data

labels = ['O', 'B-qq', 'B-wechat', 'I-wechat', 'B-tg', 'I-tg', 'B-others','I-others', 'I-qq']
model = NERModel(
    "roberta",
    NER_model_path,    
    labels=labels
)
def extract_hashtag(text):
    re_hashtag = '(?<=\#)[\s\S]*?(?=\#|\s)'
    if text.endswith(" ") is False:
        text+= " "
    return [item for item in re.findall(re_hashtag, text) if item != '']

def remove_hashtags(text, hashtags):
    hashtags = ["#"+each for each in hashtags]
    for each in hashtags:
        text = text.replace(each,"")
    text = re.sub(' +',' ',text)
    return text.strip().replace("\n"," ")

def seg_sents(sent):
    hashtags = extract_hashtag(sent)
    sent = remove_hashtags(sent, hashtags)
    new_sent = re.sub(url_pattern, "url", sent)
    new_sent = new_sent.replace("飞机url", "飞机 url").replace("联系","联系 ").replace("电报","电报 ").replace("👉"," ")
    # new_sent = emojiswitch.demojize(new_sent, delimiters=(' ',' '))
    if new_sent == "":
        return [""]
    else:
        sent = seg(new_sent)
    new_sentence = " ".join([w.strip() for w in sent if w.strip() != '']).split(" ")
    new_sentence = [w.strip() for w in new_sentence if w.strip() != '']
    return new_sentence

def extract_urls(sent):
    matches = url_pattern.finditer(sent)
    urls_extracted = [match.group() for match in matches]

    return urls_extracted
def get_redirect_url(tco_url):
    # Send a request to get the redirect URL
    try:
        response = requests.get(tco_url, allow_redirects=False)
    except:
        return "error"

    # Get redirect URL
    if response.status_code == 301:
        redirect_url = response.headers["location"]
        return redirect_url
    elif response.status_code == 200:
        return tco_url
#         print(f"Redirected URL: {redirect_url}")
    else:
        return "error"
def get_contacts_from_url(urls):
    contacts = {'tg':[],'Whatsapp':[],'LINE':[]}
    # print(urls)
    left_urls = []
    for url in urls:
        if url.startswith('https://t.me/'):
            tg = url.split('/')[-1]
            contacts['tg'].append(tg)
        elif re.match(r'^https?://(line\.me/ti/g/|line\.me/ti/p|line\.me/R/ti/g|shop\.line\.me|page\.line\.me/)', url.lower()):
            line = url.split('/')[-1]
            contacts['LINE'].append(line)
        elif url.lower().startswith('https://lin.ee/') or url.lower().startswith('http://lin.ee/'):
            redirect_url = get_redirect_url(url)
            if redirect_url!='error':
                line = redirect_url.split('/')[-1]
                contacts['LINE'].append(line)
            else:
                left_urls.append(url)
        elif url.lower().startswith('https://wa.me/') or url.lower().startswith('http://wa.me/'):
            whatsapp = url.split('/')[-1].replace("+","")
            contacts['Whatsapp'].append(whatsapp)
        else:
            left_urls.append(url)
    return contacts,left_urls

def extract_contacts(each_pred):
    result = {"qq":[],"tg":[], "wechat":[],"others":[]}
    temp = ""
    last_tag = "O"
    for i in range(len(each_pred)):
        for key, value in each_pred[i].items():
            if value.startswith("B-"):
                tag = value.split("-")[-1]
                temp = key
                result[tag].append(temp)
                last_tag = "B-"+tag
            elif value.startswith("I-"):
                if last_tag == "O":
                    tag = value.split("-")[-1]
                    last_tag = "I-"+tag
                    temp += key
                    if len(result[tag]) == 0:
                        result[tag].append(temp)
                    else:
                        result[tag][-1] = temp
                else:
                    temp += key
                    result[tag][-1] = temp
                    last_tag = tag
            elif value == "O":
                last_tag = "O"
                temp = key     
    result['tg'] = [each for each in result['tg'] if not each.startswith('url')]   
    result['others'] = [each for each in result['others'] if not each.startswith('url')]
    # if "url" in result['tg']: 
    #     urls = [x for x in each_pred if x.get("url")]
    #     indexes = [i for i, x in enumerate(urls) if x.get("url") == "B-tg"]
    #     result['tg'] = [item for item in result['tg'] if item !='url']
    #     for idx in indexes:
    #         result['tg'].append('url_%s'%idx)
    return result

def chunk_data(arr, n):
    return [arr[i:i+n] for i in range(0, len(arr), n)]

def write2json(data,save_path):
    with open(save_path, 'a+') as f:
        for line in data:
            f.write(json.dumps(line, ensure_ascii=False))
            f.write("\n")

def read_from_json(data_path, save_path):
    data = []
    with open(data_path, 'r') as f:
        for line in f.readlines():
            if line.strip() == '':
                continue
            if '}{' in line:
                line = line.replace('}{','},{')
                line = json.loads('['+line+']')
                data.extend(line)
            else:
                data.append(json.loads(line))
    negative = [each for each in data if int(each['labels']) == 0]
    with open(save_path, 'w')as f:
        f.write('\n'.join([json.dumps(each, ensure_ascii=False) for each in negative]))
        f.write('\n')
    data = [each for each in data if each['labels']]
    return data

def gen_contact_data_for_predictions(data, preprocessed_data,predictions):
    for idx,each_pred in enumerate(predictions):
        # data[idx]['preprocessed_text_ner'] = preprocessed_data[idx]
        contacts_info = extract_contacts(each_pred)
        tmp_dict = {}
        tmp_dict['qq'] = []
        tmp_dict['wechat'] = []
        if 'lang' in data[idx]['raw_data']:
            lang1 = data[idx]['raw_data']['lang']
        elif 'language' in data[idx]:
            if 'by_text' in data[idx]['language']:
                lang1 = data[idx]['language']['by_text']
            else:
                lang1 = data[idx]['language']
        else:
            lang1 = ''
        if filter_contact.detect_language(data[idx]['text']) and lang1 not in ['ja','ko']:
            tmp_dict['qq'] =  [each.lower().replace('q','') for each in filter_contact.filter_qq(contacts_info['qq'])]
            tmp_dict['wechat'] =  filter_contact.filter_wechat(contacts_info['wechat'])
        tmp_dict['tg'] =  filter_contact.filter_tg(contacts_info['tg'])
        contacts_info['others'] = filter_contact.filter_others(contacts_info['others'])
        tmp_dict['others'] =  [each for each in contacts_info['others'] if not each.startswith('@')]
        tmp_dict['twitter'] = [each for each in contacts_info['others'] if each.startswith('@')]
        tmp_dict['Whatsapp'] = []
        tmp_dict['LINE'] = []
        if 'entities' in data[idx]['raw_data'].keys():
            urls = [item['expanded_url'] for item in data[idx]['raw_data']['entities']['urls'] if item['expanded_url'].startswith('https://twitter.com') is False]
            tmp_dict['websites'] = urls
        else:
            tmp_dict['websites'] = []
        tmp_contacts, tmp_dict['websites'] = get_contacts_from_url(tmp_dict['websites'])
        if len(tmp_contacts['tg']) >0:
             tmp_dict['tg'] = tmp_contacts['tg']
        if len(tmp_contacts['Whatsapp'])>0:
            tmp_dict['Whatsapp'] = tmp_contacts['Whatsapp']
        if len(tmp_contacts['LINE'])>0:
            tmp_dict['LINE'] = tmp_contacts['LINE']
        # tmp_dict['urls'] = extract_urls(data[idx]['ori_text'])
        data[idx]['contacts'] = tmp_dict
    return data

def parse_args():
    parse = argparse.ArgumentParser(description='Extract contacts')
    parse.add_argument('-d', '--data', type=str, help='Data to be predicted path')
    parse.add_argument('-c', '--chunk', default=10000, type=int, help="the length of each trunk")
    parse.add_argument('-s', '--savefile', type=str, help="The prediction result of save file path")
    args = parse.parse_args()
    return args


def extract(data_path, save_filename, len_=10000):
    logger.info(f"extract({data_path}, {save_filename}, {len_})")
    
    all_data = read_from_json(data_path)
    chunks = chunk_data(all_data, len_)
    predicted_data = []
    for data in chunks:
        try:
            preprocessed = [" ".join(seg_sents(each['ori_text'])) for each in data]
        except:
            preprocessed = [" ".join(seg_sents(each['text'])) for each in data]
        predictions, raw_outputs = model.predict(preprocessed)
        extracted_data = gen_contact_data_for_predictions(data, preprocessed, predictions)
        predicted_data.extend(extracted_data)
        
    write2json(extracted_data,save_filename)
    return predicted_data

if __name__ == "__main__":
    args = parse_args()

    data_path = args.data
    len_ = args.chunk
    save_filename = args.savefile
    extract(data_path, save_filename, len_)

 


