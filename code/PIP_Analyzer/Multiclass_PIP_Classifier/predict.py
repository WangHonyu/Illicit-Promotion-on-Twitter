from simpletransformers.classification import MultiModalClassificationModel, MultiModalClassificationArgs,ClassificationModel
import json
import cv2
import os
import re
import pandas as pd
import argparse
import warnings
import emoji
from PIL import ImageFile
from PIL import Image
import numpy as np
import logging
from itertools import chain
import settings

ImageFile.LOAD_TRUNCATED_IMAGES = True

multimodal_path = settings.multimodal_model_path
textmodel_path = settings.text_only_model_path

re_url ='http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
media_train_path = settings.media_path
file_names = os.listdir(media_train_path)
zero_size_file_names = [name for name in file_names if os.path.getsize(os.path.join(media_train_path,name)) == 0]
label_map_dict = {"Crowdturfing": "0", "fake_document": "1", "data_leakage": "2", "money-laundry": "3", "drug": "4", "porn": "5", "weapon": "6", "harassment": "7", "Gambling": "8", "surrogacy": "9", "Others": "10"}
idx2label = dict(zip(label_map_dict.values(), label_map_dict.keys()))
english_pattern = re.compile(r'[a-zA-Z]+')

logger = logging.getLogger(__name__)

def preprocess(data):
    data = re.sub(re_url,'',data)
    data = emoji.demojize(data)
    # data = re.sub(':\S+?:', ' ', data) #remove emoji
    data = re.sub(r'[^\w\s]', '', data)
    # data = english_pattern.sub('', data)

    return data.replace('\n','')
def preprocessing(data,media_download_path):
    tmp_dict = {}
    tmp_dict['id'] = data['id']
    tmp_dict['author_id'] = data['author_id']
    tmp_dict['media_url'] = data['media_url']
    tmp_dict['ori_text'] = data['text']
    tmp_dict['text'] = preprocess(tmp_dict['ori_text'])
    tmp_dict['images'] = []
    try:
        if len(data['media'])>0:
            for tmp in data['media']:
                if tmp.endswith(".mp4"):
                    get_frames(media_download_path,tmp)
                if tmp.endswith(".gif"):
                    try:
                        get_gif_frame(media_download_path, tmp)
                    except:
                        continue
            tmp_dict['images'] = [tmp.replace('.mp4','.jpg').replace('.gif','.jpg') for tmp in data['media'] if media_in_downloaded_path(media_download_path,tmp.replace('.mp4','.jpg')) or media_in_downloaded_path(media_download_path,tmp.replace('.gif','.jpg')) ]
            tmp_dict['images'] = [tmp for tmp in tmp_dict['images'] if os.path.getsize(os.path.join(media_download_path,tmp)) != 0]
        else:
            data['media'] = []
    except:
        data['media'] = []
    if len(tmp_dict['images'])>0:
        tmp_dict['images'] = tmp_dict['images'][0]
        tmp_dict['media_type'] = "media"
    else:
        tmp_dict['images'] = []
        tmp_dict['media_type'] = "text"
    if 'labels' in data:
        tmp_dict['labels'] = data["labels"]
    return tmp_dict

def load_model(multimodal_path, text_model_path):
    ImageFile.LOAD_TRUNCATED_IMAGES = True
    warnings.filterwarnings('ignore')
    multiModal_args = MultiModalClassificationArgs(fp16=False)
    multiModal = MultiModalClassificationModel(
        "bert",
        multimodal_path,
        args=multiModal_args,
        use_cuda = True,
    )
    multiModal.config.use_return_dict = False
    text_model = ClassificationModel("bert", text_model_path)
    return multiModal, text_model

def media_in_downloaded_path(media_path,media):
    if os.path.exists(os.path.join(media_path,media)):
        return True
    else:
        return False

def get_frames(media_download_path,video):
    video_capture = cv2.VideoCapture(os.path.join(media_download_path,video))
    video_name = video.replace('.mp4','')
        # Capture the first frame of the video
    for i in range(1):
        # Read a frame of video
        success, frame = video_capture.read()
        # If the read fails, exit the loop
        if not success:
            break
        # Save frame image to file
        cv2.imwrite(os.path.join(media_download_path,video_name+(str(".jpg"))), frame)
    video_capture.release()  

def get_gif_frame(media_download_path,gif):
    im = Image.open(os.path.join(media_download_path,gif))
    gif_name = gif.replace('.gif','')
    im.seek(0)
    im.save(os.path.join(media_download_path,gif_name+str(".jpg"))) 

def write2jsonfile(data,filename):
    with open(filename, 'a+') as f:
        for line in data:
            f.write(json.dumps(line, ensure_ascii=False))
            f.write("\n")

def read_from_json(file):
    with open(file, 'r') as f:
        data = [json.loads(each) for each in f.readlines() if each.strip() != '']
    return data

def cal_class_cov(train_pred, pred_probs):
    class_preds_dict = {}
    for idx in range(pred_probs.shape[1]):
        class_preds_dict[idx] = []
    for idx,each in enumerate(train_pred):
        class_preds_dict[each].append(pred_probs[idx])
    covariances = []
    mean = []
    for pred in class_preds_dict.values():
        covariances.append(np.cov(np.array(pred).T) )
        mean.append(pred)
    return mean,covariances

def cal_mahalanobis_distance(mean_vector_k, prob, cov_k):
    x_minus_mean = prob - mean_vector_k
    covariance_matrix_inv = np.linalg.inv(cov_k)
    left_multiply = np.dot(x_minus_mean, covariance_matrix_inv)
    mahalanobis_distance_square = np.dot(left_multiply, x_minus_mean)
    mahalanobis_distance = np.sqrt(mahalanobis_distance_square)
    return mahalanobis_distance

def chunk_data(arr, n):
    return [arr[i:i+n] for i in range(0, len(arr), n)]

def parse_args():
    parse = argparse.ArgumentParser(description='Extract contacts')
    parse.add_argument('-d', '--data', type=str, help='Data to be predicted path')
    parse.add_argument('-c', '--chunk', default=10000, type=int, help="the length of each trunk")
    parse.add_argument('-s', '--savefile', type=str, help="The prediction result of save file path")
    args = parse.parse_args()
    return args

multiModal, text_model = load_model(multimodal_path,textmodel_path)
sub_train_args = json.load(open('sub_train_args.json', 'r'))
mean_text = sub_train_args['mean_text']
cov_text = sub_train_args['cov_text']
mean_media = sub_train_args['mean_media']
cov_media = sub_train_args['cov_media']
mean_vec_media = sub_train_args['mean_vec_media']
mean_vec_text = sub_train_args['mean_vec_text']


def subcategory(filepath, save_filename, len_=10000):
    all_data = read_from_json(filepath)
    chunks = chunk_data(all_data,len_)

    for data in chunks:
        preprocessed_data = [preprocessing(each,media_train_path) for each in data]
        text_predictions, text_raw_outputs = text_model.predict([each['text'] for each in preprocessed_data])
        for idx, each_pred in enumerate(text_predictions):
            data[idx]['sub_category'] = idx2label[str(each_pred)]
            
    ret_data = list(chain(*chunks))
    write2jsonfile(ret_data, save_filename)
    return ret_data


if __name__ == "__main__":
    args = parse_args()
    data_path = args.data
    len_ = args.chunk
    save_filename = args.savefile
    
    subcategory(data_path, save_filename, len_)
