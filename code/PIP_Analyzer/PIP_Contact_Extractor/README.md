# PIP Contact Extractor
1. Using **Name Entity Recognition(ner)** to determine the contacts in tweet.
2. Contacts inlude: qq, tg, wechat, and others(e.g., twitter account, pop account, Line, telephone, etc)
3. script to get the next-hop(redirect) website

### Required Environment
```
simpletransformers == 0.63.9
paddlenlp == 2.5.0
paddlepaddle == 2.4.1
```

### Training and Testing

Code for training and testing is in [jupyter notebook]().

### Predict
Before running, please fill in the model path in `settings.py`.
```
python extract_contacts.py -d datapath -s savepath -c chunk
```

Parameters:
- `data_path` : Path of the data file to be predicted, which should be an output file of [the Multiclass PIP Classifier](../Multiclass_PIP_Classifier/).

- `chunk_length`: How much data will be predicted once.

- `save_path`: Predicted data save path.
