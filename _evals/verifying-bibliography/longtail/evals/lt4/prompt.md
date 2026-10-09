---
name: lt4
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
@article{huo2026dislocation,
  author = {Huo, Wenyi and Kim, Hyoung Seop and Liaw, Peter K.},
  title = {Dislocation dynamics in noble-metal high-entropy alloys under nanoindentation: Neuroevolution potential insights},
  journal = {Applied Physics Letters},
  volume = {129},
  number = {4},
  pages = {041903},
  year = {2026},
  doi = {10.1063/5.0328063}
}

@article{chow2004adaptive,
  author = {Chow, Stephanie S. and Wilke, Claus O. and Ofria, Charles and Lenski, Richard E. and Adami, Christoph},
  title = {Adaptive Radiation from Resource Competition in Digital Organisms},
  journal = {Science},
  volume = {305},
  number = {5680},
  pages = {84--86},
  year = {2004}
}

@inproceedings{olmscheid2021improving,
  author = {Olmscheid, Christian and Wittenberg, David and Sobania, Dominik and Rothlauf, Franz},
  title = {Improving estimation of distribution genetic programming with novelty initialization},
  booktitle = {Proceedings of the Genetic and Evolutionary Computation Conference Companion},
  pages = {261--262},
  publisher = {ACM},
  year = {2021},
  doi = {10.1145/3449726.3459410}
}

@article{vandersmagt1994simderella,
  author = {van der Smagt, Patrick},
  title = {Simderella: A robot simulator for neuro-controller design},
  journal = {Neurocomputing},
  volume = {6},
  number = {2},
  pages = {281--285},
  year = {1994},
  doi = {10.1016/0925-2312(94)90063-9}
}

@article{misevic2006sexual,
  author = {Misevic, Dusan and Ofria, Charles and Lenski, Richard E},
  title = {Sexual reproduction reshapes the genetic architecture of digital organisms},
  journal = {Proceedings of the Royal Society B: Biological Sciences},
  volume = {273},
  number = {1585},
  pages = {457--464},
  year = {2006},
  doi = {10.1098/rspb.2005.3338}
}

@article{yu2026adaptive,
  author = {Yu, Xiaobing and Zhang, Hongqian and Liu, Shuang},
  title = {Adaptive strategy Q-learning differential evolution for microgrid scheduling optimization},
  journal = {Swarm and Evolutionary Computation},
  volume = {108},
  pages = {102509},
  year = {2026},
  doi = {10.1016/j.swevo.2026.102509}
}

@article{liu2026kriging,
  author = {Liu, Chang and Chen, Baide},
  title = {A kriging-assisted evolutionary algorithm with hybrid-metric infill sampling criterion for expensive many-objective optimization},
  journal = {Swarm and Evolutionary Computation},
  volume = {107},
  pages = {102451},
  year = {2026},
  doi = {10.1016/j.swevo.2026.102451}
}

@article{dalklc2026adaptive,
  author = {Dalkılıç, Şahin Burak and Özgür, Atilla and Erdem, Hamit},
  title = {Adaptive parameter control in genetic algorithms with a hybrid crossover operator},
  journal = {Swarm and Evolutionary Computation},
  volume = {107},
  pages = {102439},
  year = {2026},
  doi = {10.1016/j.swevo.2026.102439}
}

@article{wolpold2026neuroevolution,
  author = {Wolpold, Sarah and Voolstra, Christian R. and von Mammen, Sebastian},
  title = {A neuroevolution-driven agent-based model of coral larvae settlement},
  journal = {PLOS One},
  volume = {21},
  number = {9},
  pages = {e0355996},
  year = {2026},
  doi = {10.1371/journal.pone.0355996}
}
```
