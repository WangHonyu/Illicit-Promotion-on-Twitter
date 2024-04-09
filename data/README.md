## Data release v2

Directory structure:
```
.
├── README.md
├── category_PIPs
│   ├── Crowdturfing.json
│   ├── Gambling.json
│   ├── data_leakage.json
│   ├── drug.json
│   ├── fake_document.json
│   ├── harassment.json
│   ├── money-laundry.json
│   ├── porn.json
│   ├── surrogacy.json
│   └── weapon.json
├── groundtruth_non_pips.json
└── groundtruth_pips.json
```

20K PIPs are sampled for each category, and then deduplicated by removing PIPs that have the same text and different from each other only in url. After that each PIP is checked and labeled manually. Drug, data-leakage, gambling, crowdturfing and surrogacy is ready. Weapon, harassment, porn, money-laundry and fake-document is still under labeling.