<div align="center">
  <h1>Exqutor Demo: Interactive Demonstration of Query Optimization for Vector-Augmented Queries</h1>
  <p><b>Accepted to ICDE'26</b></p>
  <p>
    <a href="https://arxiv.org/abs/2512.09695">Paper (arXiv)</a>
  </p>
</div>

## Overview

**Exqutor Demo** presents an interactive demonstration of **Exqutor** (**Extended Query Optimizer for Vector-augmented Analytical Queries**), an open-source framework for improving the performance of **vector-augmented queries (VAQs)** in generalized vector database systems.

VAQs combine **vector similarity search (VSS)** with relational operators such as **joins** and **filters**. However, existing query optimizers often treat vector predicates as black-box operators and rely on fixed or heuristic selectivity estimates, which can lead to inefficient query plans.

Exqutor addresses this problem by integrating **cardinality estimation for vector predicates directly into the query planning phase**. It supports two complementary techniques:

- **Exact Cardinality Query Optimization (ECQO)**: performs lightweight vector index probes during planning to compute exact predicate cardinalities.
- **Adaptive Sampling-Based Estimation**: approximates predicate cardinalities when vector indexes are unavailable.

By replacing heuristic selectivity with computed cardinalities in the optimizer cost model, Exqutor enables more efficient query plans **without modifying the execution engine or SQL interface**.

## What This Demo Shows

This demo allows users to interactively explore how Exqutor improves query planning for vector-augmented queries.

Specifically, the demo highlights:

- **Plan-level comparison** between baseline optimization and Exqutor
- **Threshold sensitivity** for vector distance predicates
- **Index-aware optimization**, including cases with and without vector indexes
- **Improved cardinality estimation** for vector predicates during planning

## Repository Structure

```bash
Exqutor_demo/
├── demo_web/
│   ├── app.py
│   └── index.html
├── figure/
│   ├── demo.pdf
│   └── overview.pdf
└── README.md
```

## Running the Demo

To run the demonstration, first navigate to the `demo_web` directory:

```sh
cd demo_web
```

Then launch the demo application:

```sh
python app.py
```

Once the application is running, access the demo interface through the local endpoint specified by the server configuration in `app.py`. Depending on the deployment setup, the frontend may also be opened directly via `index.html`.

## Demo Material

Additional materials for the demonstration are available in:

- [`figure/overview.pdf`](./figure/overview.pdf): high-level overview of the demonstration
- [`figure/demo.pdf`](./figure/demo.pdf): captured screenshots of the demo interface

## Paper

- **ICDE 2026**: Exqutor was accepted to ICDE 2026.
- **arXiv**: [Paper link](https://arxiv.org/abs/XXXX.XXXXX)

## Citation

If you use Exqutor in your research, please cite:

~~~bibtex
@inproceedings{exqutor_icde2026,
  title={Exqutor: Query Optimization for Vector-Augmented Queries via Planning-Time Cardinality Estimation},
  author={...},
  booktitle={ICDE},
  year={2026}
}
~~~

## Contact

For questions or issues, please open a GitHub issue or contact the authors.