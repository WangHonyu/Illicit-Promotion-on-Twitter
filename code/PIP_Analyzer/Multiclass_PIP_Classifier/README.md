# Multiclass PIP Classifier

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
python predict.py -d datapath -s savepath -c chunk
```

Parameters:
- `data_path` : Path of the data file to be predicted, which should be an output file of [the Binary PIP Classifier](../../PIP_Hunter/Binary_PIP_Classifier/).

- `chunk_length`: How much data will be predicted once.

- `save_path`: Path to save the predicted data.
