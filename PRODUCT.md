# BioFlux Lab

<!-- impeccable:product-schema 1 -->

## Platform
web

## Stack
Python, COBRApy, PyTorch and scikit-learn for science. The user explicitly requested a richer non-Streamlit interface: React/TypeScript with a local FastAPI service is the primary UI. No hosted services. The original Streamlit app is an optional legacy interface.

## Users
The project owner and research reviewers exploring computational metabolic intervention discovery. Research familiarity is an assumption derived from the supplied brief.

## Product Purpose
Compare graph learning and conventional search for discovering solver-verified, growth-constrained succinate production interventions.

## Operating Context
A Windows laptop with an RTX 4060 GPU and 8 GB VRAM. Local reproducible experiments, followed by an interactive review of actual results.

## Capabilities and Constraints
Gene deletions, glucose/oxygen environments, growth and production simulation, surrogate training, uncertainty-guided discovery and comparative evaluation. FBA outputs are simulations, not biological validation. Model data and dependencies must come from established official sources.

## Evidence on Hand
Completed core and genome simulation experiments, safe neural checkpoints, solver cross-checks and audited artifacts are present. All numerical claims must derive from these recorded runs.

## Product Principles
- Solver verification precedes claims.
- Preserve model identity and evaluation provenance.
- Give simpler methods an equal evaluation budget.
- Make uncertainty and failure states visible.

## Delegated Decisions
The user explicitly authorized implementation and routine design choices without additional permission. Interface direction and defaults are implementation assumptions, not user-specified aesthetic preferences.
