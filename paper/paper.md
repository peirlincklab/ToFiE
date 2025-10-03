---
title: "ToFiE: Python framework for Fiber Topology Extraction from microscopy Images."
tags:
  - Python
  - biology
  - microscopy 
authors:
  - name: Risa Togo
    affiliation: 1,2
  - name: Sara Cardona
    affiliation: 1
  - name: Irene Nagle
    affiliation: 2
  - name: Gijsje H. Koenderink
    affiliation: 2
  - name: Behrooz Fereidoonnezhad
    affiliation: 1
  - name: Mathias Peirlinck
    affiliation: 1
affiliations:
  - name: dept. Biomechanical Engineering, Faculty of Mechanical Engineering, Delft University of Technology
    index: 1
  - name: dept. Biomechanical Engineering, Faculty of Mechanical Engineering, Delft University of Technology
    index: 1
date: 3 October 2025
bibliography: paper.bib
---

# Summary
Begin your paper with a summary of the high-level functionality of your software for a non-specialist reader. Avoid jargon in this section.

# Statement of need
A Statement of need section that clearly illustrates the research purpose of the software and places it in the context of related work - i.e. we eventually refer to arxiv preprint [@Togo:2025] here once that is online.

`ToFiE` is a Python package for ... Python
enables wrapping low-level languages (e.g., C) for speed without losing
flexibility or ease-of-use in the user-interface. The API for `ToFiE` was
designed to provide a class-based and user-friendly interface to ...

# Mathematics

Single dollars ($) are required for inline mathematics e.g. $f(x) = e^{\pi/x}$

Double dollars make self-standing equations:

$$\Theta(x) = \left\{\begin{array}{l}
0\textrm{ if } x < 0\cr
1\textrm{ else}
\end{array}\right.$$

You can also use plain \LaTeX for equations
\begin{equation}\label{eq:fourier}
\hat f(\omega) = \int_{-\infty}^{\infty} f(x) e^{i\omega x} dx
\end{equation}
and refer to \autoref{eq:fourier} from text.

# Citations

Citations to entries in paper.bib should be in
[rMarkdown](http://rmarkdown.rstudio.com/authoring_bibliographies_and_citations.html)
format.

If you want to cite a software repository URL (e.g. something on GitHub without a preferred
citation) then you can do it with the example BibTeX entry below for @fidgit.

For a quick reference, the following citation commands can be used:
- `@author:2001`  ->  "Author et al. (2001)"
- `[@author:2001]` -> "(Author et al., 2001)"
- `[@author1:2001; @author2:2001]` -> "(Author1 et al., 2001; Author2 et al., 2002)"

# Figures

Figures can be included like this:
![Caption for example figure.\label{fig:example}](figure.png)
and referenced from text using \autoref{fig:example}.

Figure sizes can be customized by adding an optional second parameter:
![Caption for example figure.](figure.png){ width=20% }

# Usage
Mention (if applicable) a representative set of past or ongoing research projects using the software and recent scholarly publications enabled by it.
Mention arxiv submission October 2025.

# Acknowledgements

# References
A list of key references, including to other software addressing related needs. Note that the references should include full names of venues, e.g., journals and conferences, not abbreviations only understood in the context of a specific discipline.
