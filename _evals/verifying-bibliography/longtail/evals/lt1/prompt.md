---
name: lt1
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
@article{lau2003censors,
  author = {Lau, Nelson C. and Bartel, David P.},
  title = {Censors of the Genome},
  journal = {Scientific American},
  volume = {289},
  number = {2},
  pages = {34--41},
  year = {2003}
}

@article{deshpande2026comparison,
  author = {Deshpande, Rachit and Desai, Shantanu},
  title = {Comparison of symbolic regression algorithms in Star/galaxy/quasar separation},
  journal = {arXiv preprint arXiv:2602.24022},
  year = {2026}
}

@inproceedings{lehman2018surprising,
  author = {Lehman, Joel and Clune, Jeff and Misevic, Dusan},
  title = {The Surprising Creativity of Digital Evolution},
  booktitle = {The 2018 Conference on Artificial Life},
  pages = {55--56},
  publisher = {MIT Press},
  year = {2018},
  doi = {10.1162/isal_a_00016}
}

@article{clune2008natural,
  author = {Clune, Jeff and Misevic, Dusan and Ofria, Charles and Lenski, Richard E. and Elena, Santiago F. and Sanjuán, Rafael},
  title = {Natural Selection Fails to Optimize Mutation Rates for Long-Term Adaptation on Rugged Fitness Landscapes},
  journal = {PLoS Computational Biology},
  volume = {4},
  number = {9},
  pages = {e1000187},
  year = {2008}
}

@incollection{koza1991hierarchical,
  author = {Koza, John R.},
  title = {A Hierarchical Approach to Learning the Boolean Multiplexer Function},
  booktitle = {Foundations of Genetic Algorithms},
  pages = {171--192},
  publisher = {Elsevier},
  year = {1991},
  doi = {10.1016/b978-0-08-050684-5.50014-8}
}

@article{zhang2026multi,
  author = {Zhang, Wei and Liu, Yang and Chen, Hao},
  title = {A multi-population differential evolution with adaptive restart for dynamic constrained optimization},
  journal = {Swarm and Evolutionary Computation},
  volume = {108},
  pages = {102531},
  year = {2026}
}

@inproceedings{wittenberg2022denoising,
  author = {Wittenberg, David and Rothlauf, Franz},
  title = {Denoising autoencoder genetic programming for real-world symbolic regression},
  booktitle = {Proceedings of the Genetic and Evolutionary Computation Conference Companion},
  pages = {612--614},
  publisher = {ACM},
  year = {2022},
  doi = {10.1145/3520304.3528921}
}

@inproceedings{demelo2019batch,
  author = {de Melo, Vinícius V. and Vargas, Danilo Vasconcellos and Banzhaf, Wolfgang},
  title = {Batch tournament selection for genetic programming: the quality of lexicase, the speed of tournament},
  booktitle = {Proceedings of the Genetic and Evolutionary Computation Conference},
  pages = {994--1002},
  publisher = {ACM},
  year = {2019},
  doi = {10.1145/3321707.3321793}
}

@inproceedings{wong2014grammar,
  author = {Wong, Pak-Kan and Lo, Leung-Yau and Wong, Man-Leung and Leung, Kwong-Sak},
  title = {Grammar-Based Genetic Programming with Bayesian network},
  booktitle = {2014 IEEE Congress on Evolutionary Computation (CEC)},
  pages = {739--746},
  publisher = {IEEE},
  year = {2014},
  doi = {10.1109/cec.2014.6900423}
}

@article{grabowski2013case,
  author = {Grabowski, Laura M. and Bryson, David M. and Dyer, Fred C. and Pennock, Robert T. and Ofria, Charles},
  title = {A Case Study of the De Novo Evolution of a Complex Odometric Behavior in Digital Organisms},
  journal = {PLoS ONE},
  volume = {8},
  number = {4},
  pages = {e60466},
  year = {2013},
  doi = {10.1371/journal.pone.0060466}
}
```
