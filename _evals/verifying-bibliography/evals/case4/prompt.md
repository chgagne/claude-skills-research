---
name: bib-case4
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
@article{hochreiter1997long,
  author = {Hochreiter, Sepp and Schmidhuber, J{\"u}rgen},
  title = {Long Short-Term Memory},
  journal = {Neural Computation},
  volume = {9},
  number = {8},
  pages = {1735--1780},
  year = {1997},
  doi = {10.1162/neco.1997.9.8.1735}
}

@article{hansen2001completely,
  author = {Hansen, Nikolaus and Ostermeier, Andreas},
  title = {Covariance Matrix Adaptation for Derandomized Evolution Strategies},
  journal = {Evolutionary Computation},
  volume = {9},
  number = {2},
  pages = {159--195},
  year = {2001},
  doi = {10.1162/106365601750190398}
}

@article{lecun2015deep,
  author = {LeCun, Yann and Bengio, Yoshua and Hinton, Geoffrey and Schmidhuber, J{\"u}rgen},
  title = {Deep Learning},
  journal = {Nature},
  volume = {521},
  number = {7553},
  pages = {436--444},
  year = {2015},
  doi = {10.1038/nature14539}
}

@article{silver2016mastering,
  author = {Silver, David and Huang, Aja and Maddison, Chris J. and Guez, Arthur and Sifre, Laurent and van den Driessche, George and Schrittwieser, Julian and Antonoglou, Ioannis and Panneershelvam, Veda and Lanctot, Marc and others},
  title = {Mastering the Game of {Go} with Deep Neural Networks and Tree Search},
  journal = {Nature},
  volume = {529},
  number = {7587},
  pages = {484--489},
  year = {2016},
  doi = {10.1038/nature16961}
}

@inproceedings{he2016deep,
  author = {He, Kaiming and Zhang, Xiangyu and Ren, Shaoqing and Sun, Jian},
  title = {Deep Residual Learning for Image Recognition},
  booktitle = {Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition (CVPR)},
  pages = {770--778},
  year = {2016},
  doi = {10.1109/CVPR.2016.90}
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

@article{ronneberger2015unet,
  author = {Ronneberger, Olaf and Fischer, Philipp and Brox, Thomas},
  title = {{U-Net}: Convolutional Networks for Biomedical Image Segmentation},
  journal = {arXiv preprint arXiv:1505.04597},
  year = {2015}
}

@article{mnih2015human,
  author = {Mnih, Volodymyr and Kavukcuoglu, Koray and Silver, David and Rusu, Andrei A. and Veness, Joel and Bellemare, Marc G. and Graves, Alex and Riedmiller, Martin and Fidjeland, Andreas K. and Ostrovski, Georg and others},
  title = {Human-Level Control through Deep Reinforcement Learning},
  journal = {Nature},
  volume = {518},
  number = {7540},
  pages = {529--541},
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
  doi = {10.1145/3065386}
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
```
