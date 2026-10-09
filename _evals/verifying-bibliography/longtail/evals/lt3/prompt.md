---
name: lt3
tags: [bibliography, longtail]
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
@article{anelic2026explainable,
  author = {Anđelić, Nikola and Šegota, Sandi Baressi and Mrzljak, Vedran},
  title = {Explainable multi-sensor fusion for robot movement classification using genetic programming-based symbolic expressions},
  journal = {Knowledge-Based Systems},
  volume = {351},
  pages = {116925},
  year = {2026},
  doi = {10.1016/j.knosys.2026.116925}
}

@article{nguyen2016understanding,
  author = {Nguyen, A. and Yosinski, J. and Clune, J.},
  title = {Understanding Innovation Engines: Automated Creativity and Improved Stochastic Optimization via Deep Learning},
  journal = {Evolutionary Computation},
  volume = {24},
  number = {3},
  pages = {545--572},
  year = {2016}
}

@article{pant2026electron,
  author = {Pant, Nick and Ha, Viet-Anh and Kim, Donghwan and Giustino, Feliciano},
  title = {Electron correlation in semiconductors and insulators via symbolic regression},
  journal = {arXiv preprint arXiv:2608.04291},
  year = {2026}
}

@incollection{kelly2019improving,
  author = {Kelly, Jonathan and Hemberg, Erik and O'Reilly, Una-May},
  title = {Improving Genetic Programming with Novel Exploration - Exploitation Control},
  booktitle = {Lecture Notes in Computer Science},
  pages = {64--80},
  publisher = {Springer International Publishing},
  year = {2019},
  doi = {10.1007/978-3-030-16670-0_5}
}

@incollection{weimer2013advances,
  author = {Weimer, Westley},
  title = {Advances in Automated Program Repair and a Call to Arms},
  booktitle = {Lecture Notes in Computer Science},
  pages = {1--3},
  publisher = {Springer Berlin Heidelberg},
  year = {2013},
  doi = {10.1007/978-3-642-39742-4_1}
}

@incollection{madigan2000bacterial,
  author = {Madigan, Michael T.},
  title = {Bacterial Habitats in Extreme Environments},
  booktitle = {Journey to Diverse Microbial Worlds},
  pages = {61--72},
  publisher = {Springer Netherlands},
  year = {2000},
  doi = {10.1007/978-94-011-4269-4_5}
}

@incollection{shan2006survey,
  author = {Shan, Yin and McKay, Robert I. and Essam, Daryl and Abbass, Hussein A.},
  title = {A Survey of Probabilistic Model Building Genetic Programming},
  booktitle = {Studies in Computational Intelligence},
  pages = {121--160},
  publisher = {Springer Berlin Heidelberg},
  year = {2006},
  doi = {10.1007/978-3-540-34954-9_6}
}

@article{kirschner1998evolvability,
  author = {Kirschner, Marc and Gerhart, John},
  title = {Evolvability},
  journal = {Proceedings of the National Academy of Sciences},
  volume = {95},
  number = {15},
  pages = {8420--8427},
  year = {1998},
  doi = {10.1073/pnas.95.15.8420}
}

@article{wang2026evolutionary,
  author = {Wang, Jing and Zhou, Xin and Huang, Lei and Li, Ming},
  title = {An evolutionary multitask optimization framework with knowledge transfer for symbolic regression},
  journal = {Knowledge-Based Systems},
  volume = {353},
  pages = {117104},
  year = {2026}
}

@article{hasegawa2008bayesian,
  author = {Hasegawa, Y. and Iba, H.},
  title = {A Bayesian Network Approach to Program Generation},
  journal = {IEEE Transactions on Evolutionary Computation},
  volume = {12},
  number = {6},
  pages = {750--764},
  year = {2008},
  doi = {10.1109/tevc.2008.920679}
}
```
