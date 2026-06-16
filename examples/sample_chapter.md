# Chapter 2: Model Foundations

## 2.1 Transformer-Based Language Models

Modern large language models build on the Transformer architecture, which replaced recurrent sequence modeling with self-attention and parallel token processing [@vaswani2017attention]. This change made it practical to train large models on web-scale corpora and later enabled broad transfer across tasks.

## 2.2 Scaling And Emergent Behavior

Scaling increased the importance of pretraining objectives, data mixture design, and evaluation beyond narrow supervised benchmarks. Few-shot prompting showed that sufficiently large language models can adapt to tasks from natural-language demonstrations without gradient updates [@brown2020language].

## 2.3 Alignment And Instruction Following

Instruction tuning and human feedback changed the deployment path for LLMs by turning pretrained models into interactive assistants. RLHF-style pipelines optimize helpfulness and preference alignment while introducing new evaluation and safety tradeoffs [@ouyang2022training].
