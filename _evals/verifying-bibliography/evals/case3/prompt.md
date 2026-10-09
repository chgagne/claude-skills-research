---
name: bib-case3
tags: [bibliography, stage1]
runs: 3
max_turns: 60
timeout_seconds: 1500
allowed_tools: [Read, Write, Edit, Bash, Glob, Grep, WebFetch, WebSearch, Skill]
---

A co-author sent the BibTeX file below for a machine-learning paper. Check it before
submission. Save it as `refs.bib` in the working directory if a tool needs a file.

Flag every entry with a substantive error:

- `title`: the title does not match the real work the entry points to
- `authors`: an author is added, missing or wrong
- `doi`: the DOI resolves to a different work
- `metadata`: wrong venue, volume, issue, pages or year
- `preprint`: an arXiv preprint is cited although a peer-reviewed version has been published
- `nonexistent`: no such work exists

Ignore formatting and style: capitalisation, braces, abbreviations, venue name wording,
`and others`, missing optional fields. Do not flag an entry you could not check; say so in
prose instead.

End your final message with exactly one fenced `json` block, listing only flagged entries
(an empty list if none):

```json
{"flagged": [{"key": "<bibtex key>", "problem": "<one of the six labels>"}]}
```

```bibtex
@inproceedings{chen2016xgboost,
  author = {Chen, Tianqi and Guestrin, Carlos},
  title = {{XGBoost}: A Scalable Tree Boosting System},
  booktitle = {Proceedings of the 22nd ACM SIGKDD International Conference on Knowledge Discovery and Data Mining},
  pages = {785--794},
  year = {2016},
  doi = {10.1145/2939672.2939785}
}

@article{hansen2001completely,
  author = {Hansen, Nikolaus and Ostermeier, Andreas},
  title = {Completely Derandomized Self-Adaptation in Evolution Strategies},
  journal = {Evolutionary Computation},
  volume = {9},
  number = {2},
  pages = {159--195},
  year = {2001},
  doi = {10.1162/106365601750190398}
}

@article{mnih2015human,
  author = {Mnih, Volodymyr and Kavukcuoglu, Koray and Silver, David and Rusu, Andrei A. and Veness, Joel and Bellemare, Marc G. and Graves, Alex and Riedmiller, Martin and Fidjeland, Andreas K. and Ostrovski, Georg and others},
  title = {Human-Level Control through Deep Reinforcement Learning},
  journal = {Nature},
  volume = {518},
  number = {7540},
  pages = {529--533},
  year = {2015},
  doi = {10.1038/nature14236}
}

@article{krizhevsky2017imagenet,
  author = {Krizhevsky, Alex and Sutskever, Ilya and Hinton, Geoffrey E.},
  title = {{ImageNet} Classification with Deep Convolutional Neural Networks},
  journal = {Communications of the ACM},
  volume = {60},
  number = {6},
  pages = {84--90},
  year = {2017},
  doi = {10.1145/2939672.2939785}
}

@article{hochreiter1997long,
  author = {Hochreiter, Sepp and Schmidhuber, J{\"u}rgen},
  title = {Long Short-Term Memory},
  journal = {Neural Computation},
  volume = {10},
  number = {8},
  pages = {1735--1780},
  year = {1998},
  doi = {10.1162/neco.1997.9.8.1735}
}

@article{he2016deep,
  author = {He, Kaiming and Zhang, Xiangyu and Ren, Shaoqing and Sun, Jian},
  title = {Deep Residual Learning for Image Recognition},
  journal = {arXiv preprint arXiv:1512.03385},
  year = {2015}
}

@inproceedings{devlin2019bert,
  author = {Devlin, Jacob and Chang, Ming-Wei and Lee, Kenton and Toutanova, Kristina},
  title = {{BERT}: Pre-training of Deep Bidirectional Transformers for Language Understanding},
  booktitle = {Proceedings of the 2019 Conference of the North American Chapter of the Association for Computational Linguistics: Human Language Technologies (NAACL-HLT)},
  pages = {4171--4186},
  year = {2019},
  doi = {10.18653/v1/N19-1423}
}

@inproceedings{lindqvist2020contrastive,
  author = {Lindqvist, Sara and Mbeki, Thabo and Hinton, Geoffrey E.},
  title = {Contrastive Pretraining for Evolutionary Program Synthesis},
  booktitle = {Advances in Neural Information Processing Systems},
  volume = {33},
  pages = {11204--11215},
  year = {2020}
}

@article{lecun2015deep,
  author = {LeCun, Yann and Bengio, Yoshua and Hinton, Geoffrey},
  title = {Deep Learning},
  journal = {Nature},
  volume = {521},
  number = {7553},
  pages = {436--444},
  year = {2015},
  doi = {10.1038/nature14539}
}

@article{schulman2017proximal,
  author = {Schulman, John and Wolski, Filip and Dhariwal, Prafulla and Radford, Alec and Klimov, Oleg},
  title = {Proximal Policy Optimization Algorithms},
  journal = {arXiv preprint arXiv:1707.06347},
  year = {2017}
}
```
