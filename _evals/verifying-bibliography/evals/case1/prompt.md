---
name: bib-case1
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

@article{breiman2001random,
  author = {Breiman, Leo},
  title = {Random Forests},
  journal = {Machine Learning},
  volume = {45},
  number = {1},
  pages = {5--32},
  year = {2001},
  doi = {10.1023/A:1010933404324}
}

@article{rumelhart1986learning,
  author = {Rumelhart, David E. and Hinton, Geoffrey E. and Williams, Ronald J.},
  title = {Learning Representations by Back-Propagating Errors},
  journal = {Nature},
  volume = {323},
  number = {6088},
  pages = {533--536},
  year = {1986},
  doi = {10.1038/323533a0}
}

@inproceedings{chen2016xgboost,
  author = {Chen, Tianqi and Guestrin, Carlos},
  title = {{XGBoost}: A Scalable Tree Boosting System},
  booktitle = {Proceedings of the 22nd ACM SIGKDD International Conference on Knowledge Discovery and Data Mining},
  pages = {785--794},
  year = {2016},
  doi = {10.1145/2939672.2939785}
}

@inproceedings{larsen2021gradient,
  author = {Larsen, Mikkel and Okafor, Chidi},
  title = {Gradient-Free Symbolic Regression with Evolved Attention Operators},
  booktitle = {Proceedings of the 38th International Conference on Machine Learning},
  series = {Proceedings of Machine Learning Research},
  volume = {139},
  pages = {6120--6131},
  year = {2021}
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
  title = {Playing {Atari} with Deep Reinforcement Learning},
  journal = {Nature},
  volume = {518},
  number = {7540},
  pages = {529--533},
  year = {2015},
  doi = {10.1038/nature14236}
}

@article{deb2002fast,
  author = {Deb, Kalyanmoy and Pratap, Amrit and Agarwal, Sameer and Meyarivan, T. and Zitzler, Eckart},
  title = {A Fast and Elitist Multiobjective Genetic Algorithm: {NSGA-II}},
  journal = {IEEE Transactions on Evolutionary Computation},
  volume = {6},
  number = {2},
  pages = {182--197},
  year = {2002},
  doi = {10.1109/4235.996017}
}
```
