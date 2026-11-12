# Focused prior-art check

Checked against primary publisher/author sources during implementation, 28 October 2026. This is a focused positioning check, not a systematic literature review or a novelty determination.

- [ART: A machine learning Automated Recommendation Tool for synthetic biology (2020)](https://www.nature.com/articles/s41467-020-18008-4): already combines predictive ensembles, probabilistic modeling and recommendations for successive engineering cycles. Uncertainty-guided intervention recommendation is therefore not new by itself.
- [Combining mechanistic and machine learning models for predictive engineering and optimization of tryptophan metabolism (2020)](https://www.nature.com/articles/s41467-020-17910-1): establishes that hybrid mechanistic/ML optimization in metabolic engineering is prior art. BioFlux does not claim to originate the hybrid approach.
- [iML1515, a knowledgebase that computes Escherichia coli traits (2017)](https://www.nature.com/articles/nbt.3956): primary model publication and authoritative publisher supplement source. A genome-scale reconstruction is not empirical validation of a surrogate trained on its outputs.
- [COBRApy simulation documentation](https://cobrapy.readthedocs.io/en/latest/simulating.html): reference implementation for LP objectives, gene rules and reversible model contexts.

BioFlux's initial contribution is an inspectable experimental prototype: stoichiometric graph representation, grouped generalization tests, solver-verification boundaries and explicit online/upstream evaluation accounting. Whether that combination supports a publishable contribution remains open. A direct comparison with a published exact/bilevel strain-design method is not implemented; random, greedy and tree-guided search are explicitly named as heuristics.

The supplied brief named FlowGAT, MINN, FluxGAT and dAMN. Their specific claims are not repeated as verified findings here. The implemented experiments do not depend on those claims.
