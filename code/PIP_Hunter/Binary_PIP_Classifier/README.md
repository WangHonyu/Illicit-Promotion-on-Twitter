## The Binary PIP Classifier

### Data Preprocessing
The tweets should be in a json file with one data each line containing at least the following 6 domains:
```
{'id': '', 'author_id': '', 'text': '', 'media': [], 'media_type': [], 'media_url': [] }
# for example
{"id": "1599582871190376448", "author_id": 955389445766660096, "text": "Darren Margaret Clara Ford Ida Thoreau Harriet Reed Penelope Brown #\u94f6\u884c\u5361 #\u7f51\u8d5a\u9879\u76ee https://t.co/HJuQrhX8c4", "media": ["Fi6rPzsUYAMKper.jpg"], "media_type": ["photo"], "media_url": ["http://pbs.twimg.com/media/Fi6rPzsUYAMKper.jpg"]}
```

### Training and Testing

Code for training and testing is in [jupyter notebook](model_training.ipynb).

### Predict
Before running, please fill in the model path in `settings.py`.
```
python predict.py -m media_path -d data_path -s savepath -c chunk
```

Parameters:
- `media_path`: The media downloaded path directory.

- `data_path` : The data path to be predicted in above directory. 

- `chunk_length`: How much data will be predicted once, defaulted to 50000.

- `save_path`: Predicted data save path.