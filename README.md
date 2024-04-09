# Illicit-Promotion-on-Twitter

This is the repository that contains source code for the project [Illicit Promotion on Twitter](https://wanghonyu.github.io/). In this work, we present an extensive study of the promotion of illicit goods and services on Twitter, a popular online social network(OSN).

In this repository, the source code of the project is released for usage and reproduction. As shown below, the source code for PIP hunting and analyzing tools, as well as source code and respective ground truth datasets for model training and testing are released. Particularly, 3 machine learning models are included, [the Binary PIP Classifier](./code/PIP_Hunter/Binary_PIP_Classifier/), [the Multiclass PIP Classifier](./code/PIP_Analyzer/Multiclass_PIP_Classifier/), and [the Contact Extractor](./code/PIP_Analyzer/PIP_Contact_Extractor/). 

Methodology overview:
![](./code/methodology_overview.png)

Directory structure:
```
.
├── README.md
└── code
    ├── PIP_Analyzer
    │   ├── Multiclass_PIP_Classifier/
    │   ├── PIP_Cluster_Analyzer/
    │   └── PIP_Contact_Extractor/
    ├── PIP_Hunter
    │   ├── Binary_PIP_Classifier/
    │   ├── Searching_Keyword_Generator/
    │   └── TweetCrawler/
    └── methodology_overview.png
```

