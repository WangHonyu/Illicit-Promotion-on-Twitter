from datetime import datetime
import re
import requests

pattern = r'[#{\}+:;\[\]\\!"\(\)\-=~,.\^｜]'

def get_redirect_url(tco_url):
    # 发送请求获取重定向 URL
    try:
        response = requests.get(tco_url, allow_redirects=False)
    except:
        return "error"

    # 获取重定向 URL
    if response.status_code == 301:
        redirect_url = response.headers["location"]
        return redirect_url
    elif response.status_code == 200:
        return tco_url
#         print(f"Redirected URL: {redirect_url}")
    else:
        return "error"
def is_all_uppercase(input_str):
    if not input_str:
        return False
    
    if not input_str.isalpha():
        return False
    
    return input_str.isupper()

def filter_qq(qq_list):
    return [each for each in qq_list if filter_qq_string(each)]

def is_repeating_number(num_str):
    return all(char == num_str[0] for char in num_str)

def filter_wechat(wechat_list):
    return [each for each in wechat_list if is_wechat_id(each)]
def filter_tg(tg_list):
    return [each for each in tg_list if each.startswith('url') is False and len(each)>=5 and not re.search(pattern, each) and contain_zh(each) is False and len(each)<11]
def filter_others(other_list):
    return [each for each in other_list if each.startswith('url') is False and len(each)>5 and not re.search(pattern, each) and contain_zh(each) is False and len(each)<11]

def filter_qq_string(input_string):

    if is_date(input_string) or is_repeating_number(input_string) or len(input_string.lower().replace('q',''))<7:
        return False
    # 检查字符串是否只包含数字，并且大于7位，且开头不为0
    if input_string.isdigit() and len(input_string.lower().replace('q','')) < 12 and input_string[0] != "0":
        return True
    
    # 检查字符串是否仅包含q/Q和数字，且至少包含一个q/Q
    if re.match("^[qQ\d]*$", input_string) and ("q" in input_string or "Q" in input_string):
        return True
    return False
def is_date(date_string):
    try:
        date = datetime.strptime(date_string, '%Y%m%d')
        return True
    except ValueError:
        return False
def detect_language(text):
    chinese_only = re.sub("[^\u4e00-\u9fa5]+", "", remove_hashtags(text))
    if len(chinese_only) >0:
        return True
    if "wechat" in text.lower() or 'vx' in text.lower():
        return True
    return False
def contain_zh(text):
    if re.search("[\u4e00-\u9fff]", text) is not None:
        return True
    return False
def is_wechat_id(input_str):
    # 判断长度是否在6-15个字符之间
    if len(input_str) < 6 or len(input_str) > 15 or contain_zh(input_str):
        return False
    
    if len(input_str) ==11 and input_str.isdigit():
        return True
    # 判断是否只包含数字、字母和下划线
    if not input_str.isalnum() and "_" not in input_str:
        return False
    
    # 判断是否以字母开头
    if not input_str[0].isalpha():
        return False
    
    # 判断是否包含大写字母但不是 VX
    if is_all_uppercase(input_str):
        return False 
    # upper_letters = [c for c in input_str if c.isupper()]
    # if len(upper_letters) > 0 and not all(c in ["V", "X"] for c in upper_letters):
    #     return False
    
    return True

def remove_hashtags(text):
    clean_tweet_text = re.sub(r'#\w+|#[\u4e00-\u9fff]+', '', text)
    return clean_tweet_text

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