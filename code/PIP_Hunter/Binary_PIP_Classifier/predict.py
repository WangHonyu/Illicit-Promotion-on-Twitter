from simpletransformers.classification import MultiModalClassificationModel, MultiModalClassificationArgs,ClassificationModel
import json
import cv2
import os
import re
import pandas as pd
import argparse
import warnings
from PIL import ImageFile
from PIL import Image
import logging
import torch
from tqdm import tqdm
from itertools import chain
import settings

torch.cuda.set_device(0)
logger = logging.getLogger(__name__)
transformer_logger = logging.getLogger("transformers")
transformer_logger.setLevel(logging.WARNING)

ImageFile.LOAD_TRUNCATED_IMAGES = True
warnings.filterwarnings('ignore')
multiModal_args = MultiModalClassificationArgs(fp16=True)
multiModal = MultiModalClassificationModel(
    "bert",
    settings.multimodal_model_path,
    args=multiModal_args,
    use_cuda = True,
)
multiModal.config.use_return_dict = False
text_model = ClassificationModel("bert", settings.text_only_model_path,use_cuda=True)
re_url ='http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'


def read_data(path):
    data = []
    with open(path, 'r') as f:
        for line in f.readlines():
            data.append(json.loads(line))
        f.close()
    return data
def read_from_json(filename):
    data = []
    with open(filename, 'r') as f:
        for line in f.readlines():
            data.append(json.loads(line))
    return data
def write2json(data,filename,path):
    with open(os.path.join(path,filename), 'w') as f:
        for line in data:
            f.write(json.dumps(line, ensure_ascii=False))
            f.write("\n")
    f.close()
def write2jsonfile(data,filename):
    with open(filename, 'a+') as f:
        for line in data:
            f.write(json.dumps(line, ensure_ascii=False))
            f.write("\n")
    f.close()
def media_in_downloaded_path(media_path,media):
    if os.path.exists(os.path.join(media_path,media)):
        return True
    else:
        return False
def preprocessing(data,media_download_path):
    tmp_dict = {}
    tmp_dict['id'] = data['id']
    tmp_dict['author_id'] = data['author_id']
    tmp_dict['media_url'] = data['media_url']
    # try:
    #     tmp_dict['raw_data'] = data['raw_data']
    # except:
    #     pass
    tmp_dict['ori_text'] = data['text']
    tmp_dict['text'] = re.sub(re_url,'',tmp_dict['ori_text'])
    tmp_dict['images'] = []
    if 'media' in data and len(data['media'])>0:
        for tmp in data['media']:
            if not os.path.exists(os.path.join(media_download_path, tmp)):
                continue
            if tmp.endswith(".mp4"):
                get_frames(media_download_path,tmp)
            if tmp.endswith(".gif"):
                get_gif_frame(media_download_path, tmp)
        tmp_dict['images'] = [tmp.replace('.mp4','.jpg').replace('.gif','.jpg') for tmp in data['media'] if media_in_downloaded_path(media_download_path,tmp.replace('.mp4','.jpg')) or media_in_downloaded_path(media_download_path,tmp.replace('.gif','.jpg')) ]
        tmp_dict['images'] = [tmp for tmp in tmp_dict['images'] if os.path.exists(os.path.join(media_download_path, tmp)) and os.path.getsize(os.path.join(media_download_path,tmp)) != 0]
        for each_image in tmp_dict['images']:
            try:
               Image.open(os.path.join(media_download_path,each_image)) 
            except:
               tmp_dict['images'].remove(each_image)
        tmp_dict['images'] = [tmp for tmp in tmp_dict['images'] if os.path.exists(os.path.join(media_download_path, tmp)) and os.path.getsize(os.path.join(media_download_path,tmp)) != 0 and tmp.endswith('.m3u8') is False]
    else:
        data['media'] = []
    if len(tmp_dict['images'])>0 and tmp_dict["images"]!=[""]:
        tmp_dict['images'] = tmp_dict['images'][0]
        tmp_dict['media_type'] = "media"
    else:
        tmp_dict['images'] = []
        tmp_dict['media_type'] = "text"
    tmp_dict['labels'] = ""
    return tmp_dict
def get_frames(media_download_path,video):
    video_capture = cv2.VideoCapture(os.path.join(media_download_path,video))
    video_name = video.replace('.mp4','')
        # 截取视频中的第一帧
    for i in range(1):
        # 读取一帧视频
        success, frame = video_capture.read()

        # 如果读取失败，则退出循环
        if not success:
            break
        # 将帧图像保存到文件
        cv2.imwrite(os.path.join(media_download_path,video_name+(str(".jpg"))), frame)
    video_capture.release()  
def get_gif_frame(media_download_path,gif):
    im = Image.open(os.path.join(media_download_path,gif))
    gif_name = gif.replace('.gif','')
    im.seek(0)
    try:
        im.save(os.path.join(media_download_path,gif_name+str(".jpg")))
    except:
        Image.open(os.path.join(media_download_path,gif)).convert('RGB').save(os.path.join(media_download_path,gif_name+str(".jpg")))
def parse_args():
    parse = argparse.ArgumentParser(description='Model predictions') 
    parse.add_argument('-m','--media', type=str, help='The media downloaded path directory') 
    parse.add_argument('-d','--data', type=str, help='The tweet file path')
    parse.add_argument('-c', '--chunk', default=50000, type=int, help="the length of each trunk")
    parse.add_argument('-s', '--savefile', type=str, help="The prediction result of save file path")
    parse.add_argument('-si', '--startindex', default=0, type=int, help="the chunk start index")
    parse.add_argument('-bl', '--batchlen', default=5, type=int, help="the length of each batch")
    args = parse.parse_args()
    return args

def chunks(arr, n):
    return [arr[i:i+n] for i in range(0, len(arr), n)]

def binaryClassification(filename, media_download_path, save_filename, len_=50000):
    all_data = read_from_json(filename)
    chunk = chunks(all_data,len_)
    for data in chunk:
        preprocessed_data = [preprocessing(each,media_download_path) for each in data]
        text_data = [(idx,each) for idx,each in enumerate(preprocessed_data) if each['media_type'] == "text"]
        media_data = [(idx,each) for idx,each in enumerate(preprocessed_data) if each['media_type'] == "media"]
        if len(text_data)>0:
            text_predictions = text_model.predict([each[1]['text'] for each in text_data])[0]
        if len(media_data)>0:
            media_pred_df = pd.DataFrame([each[1] for each in media_data])
            media_data_predictions = multiModal.predict(media_pred_df, image_path=media_download_path)[0]
        for idx, each in enumerate(text_data):
            data[each[0]]['labels'] = text_predictions[idx]
            if data[each[0]]['text'].startswith('http'):
                data[each[0]]['labels'] = 0
        for idx, each in enumerate(media_data):
            data[each[0]]['labels'] = int(media_data_predictions[idx])
    
    ret_data = list(chain(*chunk))
    write2jsonfile(ret_data, save_filename)
    return ret_data


if __name__ == "__main__":

    args = parse_args()
    data_path = args.data
    media_download_path= args.media
    len_ = args.chunk
    save_filename = args.savefile
    startindex = args.startindex
    batch_len = args.batchlen
    
    binaryClassification(data_path, media_download_path, save_filename, len_=len_) 