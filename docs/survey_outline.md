# LLM²: All You Need to Know About Large Language Models
Four-Level Outline

## 1. Introduction and Survey Methodology

### 1.1 Scope and Problem Definition
#### 1.1.1 What Counts as an LLM Survey
#### 1.1.2 Scope Boundaries and Exclusions
#### 1.1.3 Terminology and Naming Conventions

### 1.2 Motivation for a Large-Scale Survey
#### 1.2.1 Why LLMs Require a New Survey Structure
#### 1.2.2 Growth of the Literature and Topic Fragmentation
#### 1.2.3 Challenges of Maintaining Coverage and Coherence

### 1.3 Literature Collection and Organization
#### 1.3.1 Data Sources and Search Strategy
#### 1.3.2 Inclusion and Exclusion Criteria
#### 1.3.3 Deduplication and Metadata Normalization
#### 1.3.4 Taxonomy Construction and Paper Clustering

### 1.4 Survey Contributions and Organization
#### 1.4.1 Main Contributions
#### 1.4.2 Structural Design of the Survey
#### 1.4.3 Reading Guide and Chapter Dependencies

### 1.5 Related Surveys and Comparative Analysis
#### 1.5.1 Prior Surveys on Foundation Models
#### 1.5.2 Prior Surveys on Specialized LLM Topics
#### 1.5.3 Positioning of This Survey

## 2. Foundations of Large Language Models

### 2.1 Architectural Evolution
#### 2.1.1 From RNNs to Transformers
#### 2.1.2 Decoder-Only, Encoder-Decoder, and Hybrid Architectures
#### 2.1.3 Mixture-of-Experts and Sparse Architectures

### 2.2 Pretraining Data
#### 2.2.1 Web-Scale Corpora
#### 2.2.2 High-Quality Filtering and Data Cleaning
#### 2.2.3 Domain-Specific and Multilingual Data
#### 2.2.4 Data Mixture Design and Reweighting

### 2.3 Training Objectives and Optimization Dynamics
#### 2.3.1 Next-Token Prediction
#### 2.3.2 Masked and Span Corruption Objectives
#### 2.3.3 Optimization Stability and Training Collapse
#### 2.3.4 Loss Landscape and Gradient Behavior

### 2.4 Tokenization and Vocabulary Design
#### 2.4.1 BPE, SentencePiece, and Unigram Models
#### 2.4.2 Vocabulary Expansion and Compression
#### 2.4.3 Domain-Aware Tokenization

### 2.5 Scaling Laws and Compute Allocation
#### 2.5.1 Parameter, Data, and Compute Scaling
#### 2.5.2 Optimal Training Budget Allocation
#### 2.5.3 Emergent Behavior and Scaling Thresholds

### 2.6 Incremental Pretraining and Weight Reuse
#### 2.6.1 Continued Pretraining
#### 2.6.2 Domain-Adaptive Pretraining
#### 2.6.3 Parameter Reuse and Initialization Strategies

## 3. Post-Training and Alignment

### 3.1 Instruction Tuning
#### 3.1.1 Supervised Fine-Tuning
#### 3.1.2 Instruction Data Construction
#### 3.1.3 Multi-Task Instruction Training

### 3.2 Preference Learning and Alignment
#### 3.2.1 Reinforcement Learning from Human Feedback
#### 3.2.2 Direct Preference Optimization
#### 3.2.3 Constitutional and Rule-Based Alignment

### 3.3 Self-Improvement and Synthetic Supervision
#### 3.3.1 Self-Instruct Methods
#### 3.3.2 Bootstrapped Reasoning Data
#### 3.3.3 Synthetic Data Quality Control

### 3.4 Post-Training for Reasoning
#### 3.4.1 Chain-of-Thought Distillation
#### 3.4.2 Verifier-Guided Training
#### 3.4.3 Deliberate Inference Enhancement

### 3.5 Continual Post-Training and Forgetting Mitigation
#### 3.5.1 Continual Learning
#### 3.5.2 Catastrophic Forgetting
#### 3.5.3 Replay and Regularization Methods

### 3.6 Model Merging and Weight Fusion
#### 3.6.1 Model Averaging
#### 3.6.2 Task Arithmetic
#### 3.6.3 Conflict-Aware Merging
#### 3.6.4 Multi-Objective Fusion Strategies

## 4. Context Engineering, Retrieval, and External Tools

### 4.1 Prompting and In-Context Learning
#### 4.1.1 Prompt Design Principles
#### 4.1.2 Few-Shot and Zero-Shot Learning
#### 4.1.3 Prompt Robustness and Sensitivity

### 4.2 Retrieval-Augmented Generation
#### 4.2.1 Classical RAG
#### 4.2.2 GraphRAG and Structured Retrieval
#### 4.2.3 Retrieval Indexing and Query Formulation
#### 4.2.4 Retrieval Quality and Relevance Ranking

### 4.3 Memory Systems
#### 4.3.1 Short-Term and Long-Term Memory
#### 4.3.2 Episodic and Semantic Memory
#### 4.3.3 Memory Update and Retrieval Policies

### 4.4 Tool Use and Function Calling
#### 4.4.1 Tool Selection
#### 4.4.2 API Calling and Structured Outputs
#### 4.4.3 Tool Verification and Failure Recovery

### 4.5 Context Engineering
#### 4.5.1 Context Window Design
#### 4.5.2 Context Packing and Compression
#### 4.5.3 Context Routing and Prioritization

### 4.6 Automated Prompt Optimization
#### 4.6.1 Prompt Search
#### 4.6.2 Prompt Editing and Refinement
#### 4.6.3 Prompt Ensembles and Meta-Prompting

### 4.7 Multi-Turn Context Management
#### 4.7.1 Dialogue State Tracking
#### 4.7.2 Cross-Turn Consistency
#### 4.7.3 Long-Horizon Interaction Management

### 4.8 Faithfulness and Hallucination Mitigation in RAG
#### 4.8.1 Grounding and Attribution
#### 4.8.2 Hallucination Detection
#### 4.8.3 Verification and Re-Ranking

## 5. Reasoning Models and Deliberate Computation

### 5.1 Reasoning Task Taxonomy
#### 5.1.1 Logical Reasoning
#### 5.1.2 Mathematical Reasoning
#### 5.1.3 Scientific and Commonsense Reasoning

### 5.2 Test-Time Scaling
#### 5.2.1 Sampling-Based Deliberation
#### 5.2.2 Search and Tree-Based Decoding
#### 5.2.3 Compute-Time Trade-Offs

### 5.3 Explicit and Implicit Reasoning
#### 5.3.1 Chain-of-Thought
#### 5.3.2 Hidden Reasoning and Latent Deliberation
#### 5.3.3 Reasoning Trace Control

### 5.4 Self-Correction, Verification, and Reflection
#### 5.4.1 Answer Critique
#### 5.4.2 Self-Verification
#### 5.4.3 Reflection Loops and Error Recovery

### 5.5 Commonsense Reasoning and World Knowledge
#### 5.5.1 Commonsense Benchmarks
#### 5.5.2 Knowledge Recall and Inference
#### 5.5.3 Failure Modes in Commonsense Reasoning

### 5.6 Formal Reasoning and Theorem Proving
#### 5.6.1 Proof Generation
#### 5.6.2 Proof Checking
#### 5.6.3 Interactive Theorem Provers
#### 5.6.4 Symbolic Tool Integration

### 5.7 Multimodal Reasoning
#### 5.7.1 Visual Reasoning
#### 5.7.2 Cross-Modal Inference
#### 5.7.3 Reasoning over Tables, Charts, and Documents

### 5.8 Neuro-Symbolic Integration
#### 5.8.1 Symbolic Constraints
#### 5.8.2 Hybrid Reasoning Pipelines
#### 5.8.3 Logic-Augmented LLMs

### 5.9 World Models and Simulated Reasoning
#### 5.9.1 Internal Simulation
#### 5.9.2 Planning in Latent Space
#### 5.9.3 Environment Modeling

### 5.10 Reasoning Evaluation and Failure Analysis
#### 5.10.1 Benchmark Design
#### 5.10.2 Robustness and Generalization
#### 5.10.3 Error Taxonomy

## 6. Agentic LLMs and Planning Systems

### 6.1 Single-Agent Architectures
#### 6.1.1 ReAct-Style Systems
#### 6.1.2 Planner-Executor Designs
#### 6.1.3 Tool-Oriented Agent Loops

### 6.2 Planning, Memory, and Reflection
#### 6.2.1 Task Decomposition
#### 6.2.2 Long-Term Goal Tracking
#### 6.2.3 Reflection and Self-Improvement

### 6.3 Multi-Agent Systems
#### 6.3.1 Coordination Protocols
#### 6.3.2 Role Assignment
#### 6.3.3 Consensus and Debate Mechanisms

### 6.4 Interactive Environments
#### 6.4.1 Web Environments
#### 6.4.2 Code Environments
#### 6.4.3 Embodied and Simulated Environments

### 6.5 Agent Evaluation and Safety
#### 6.5.1 Success Metrics
#### 6.5.2 Robustness and Reliability
#### 6.5.3 Misalignment and Unsafe Actions

### 6.6 Human-AI Collaboration
#### 6.6.1 Human-in-the-Loop Control
#### 6.6.2 Shared Decision-Making
#### 6.6.3 Interactive Task Support

### 6.7 Lifelong Learning and Adaptation in Agents
#### 6.7.1 Continual Adaptation
#### 6.7.2 Environment Shift Handling
#### 6.7.3 Memory Update Strategies

### 6.8 Agent Frameworks and Engineering Practices
#### 6.8.1 Orchestration Frameworks
#### 6.8.2 Logging, Monitoring, and Debugging
#### 6.8.3 Deployment Patterns

## 7. Multimodal Large Models

### 7.1 Multimodal Architectures
#### 7.1.1 Fusion Strategies
#### 7.1.2 Cross-Attention and Adapter Designs
#### 7.1.3 Unified vs Modular Architectures

### 7.2 Multimodal Data and Pretraining
#### 7.2.1 Image-Text Data
#### 7.2.2 Video-Text Data
#### 7.2.3 Audio-Text and Other Modalities
#### 7.2.4 Data Alignment and Cleaning

### 7.3 Multimodal Alignment
#### 7.3.1 Representation Alignment
#### 7.3.2 Contrastive Objectives
#### 7.3.3 Instruction Alignment for Multimodal Inputs

### 7.4 Multimodal Post-Training
#### 7.4.1 Task-Specific Fine-Tuning
#### 7.4.2 Preference Optimization
#### 7.4.3 Safety Alignment

### 7.5 Multimodal Reasoning
#### 7.5.1 Visual Question Answering
#### 7.5.2 Cross-Modal Reasoning
#### 7.5.3 Diagram, Chart, and Document Understanding

### 7.6 Multimodal In-Context Learning
#### 7.6.1 Few-Shot Multimodal Learning
#### 7.6.2 Cross-Modal Prompting
#### 7.6.3 Transfer Across Modalities

### 7.7 Unified Multimodal Generation
#### 7.7.1 Image Generation
#### 7.7.2 Video Generation
#### 7.7.3 Audio and Speech Generation

### 7.8 Cross-Modal Representation Learning
#### 7.8.1 Shared Embedding Spaces
#### 7.8.2 Alignment Metrics
#### 7.8.3 Generalization Across Modalities

## 8. Efficiency, Systems, and Deployment

### 8.1 Training Efficiency
#### 8.1.1 Optimization Algorithms
#### 8.1.2 Parallelism Strategies
#### 8.1.3 Memory-Efficient Training

### 8.2 Inference Efficiency
#### 8.2.1 KV Cache Optimization
#### 8.2.2 Decoding Acceleration
#### 8.2.3 Latency and Throughput Trade-Offs

### 8.3 Parameter-Efficient Fine-Tuning
#### 8.3.1 LoRA and Variants
#### 8.3.2 Adapters and Prefix Tuning
#### 8.3.3 Sparse and Selective Tuning

### 8.4 Deployment Architectures
#### 8.4.1 Cloud Deployment
#### 8.4.2 Edge Deployment
#### 8.4.3 Hybrid and Distributed Serving

### 8.5 Cost and Sustainability
#### 8.5.1 Energy Consumption
#### 8.5.2 Carbon Footprint
#### 8.5.3 Cost-Aware Model Serving

### 8.6 Hardware Acceleration and Heterogeneous Systems
#### 8.6.1 GPU, TPU, and NPU Acceleration
#### 8.6.2 Quantization and Sparsification
#### 8.6.3 Compiler and Kernel Optimization

### 8.7 Distributed Systems, Fault Tolerance, and Reliability
#### 8.7.1 Distributed Training
#### 8.7.2 Failure Recovery
#### 8.7.3 Checkpointing and Resilience

### 8.8 Edge Deployment and Lightweight Optimization
#### 8.8.1 On-Device Inference
#### 8.8.2 Memory Footprint Reduction
#### 8.8.3 Offline and Low-Power Use Cases

### 8.9 Small Models, Distillation, and Compression
#### 8.9.1 Knowledge Distillation
#### 8.9.2 Model Pruning
#### 8.9.3 Quantization-Aware Training

### 8.10 Data Centers and Infrastructure Architectures
#### 8.10.1 Serving Infrastructure
#### 8.10.2 Scheduling and Load Balancing
#### 8.10.3 System-Level Observability

## 9. Evaluation Frameworks and Benchmarking

### 9.1 Benchmark Taxonomy
#### 9.1.1 Capability Benchmarks
#### 9.1.2 Task-Specific Benchmarks
#### 9.1.3 Multidimensional Benchmark Suites

### 9.2 Capability Evaluation
#### 9.2.1 Language Understanding
#### 9.2.2 Reasoning Ability
#### 9.2.3 Multimodal Capability
#### 9.2.4 Agentic Performance

### 9.3 Evaluation Methodology
#### 9.3.1 Human Evaluation
#### 9.3.2 Automatic Metrics
#### 9.3.3 LLM-as-a-Judge
#### 9.3.4 Statistical Reliability

### 9.4 Reliability, Robustness, and Consistency
#### 9.4.1 Robustness to Perturbations
#### 9.4.2 Consistency Across Prompts
#### 9.4.3 Out-of-Distribution Generalization

### 9.5 Holistic Evaluation
#### 9.5.1 Multi-Objective Scoring
#### 9.5.2 Trade-Off Analysis
#### 9.5.3 Scenario-Based Evaluation

### 9.6 Cross-Model Comparison and Leaderboard Design
#### 9.6.1 Ranking Bias
#### 9.6.2 Benchmark Contamination
#### 9.6.3 Fair Comparison Protocols

### 9.7 Longitudinal Evaluation and Regression Tracking
#### 9.7.1 Model Version Drift
#### 9.7.2 Capability Regression
#### 9.7.3 Temporal Benchmarking

### 9.8 Automated Evaluation Pipelines and Toolchains
#### 9.8.1 Evaluation Automation
#### 9.8.2 Continuous Testing
#### 9.8.3 Reproducible Benchmarking

## 10. Safety, Trustworthiness, and Security

### 10.1 Hallucination, Error, and Uncertainty
#### 10.1.1 Hallucination Taxonomy
#### 10.1.2 Confidence Calibration
#### 10.1.3 Uncertainty Estimation

### 10.2 Adversarial Safety and System Security
#### 10.2.1 Prompt Injection
#### 10.2.2 Jailbreaks and Evasion
#### 10.2.3 Secure Tool Use

### 10.3 Privacy, Copyright, and Fairness
#### 10.3.1 Data Privacy
#### 10.3.2 Memorization and Leakage
#### 10.3.3 Fairness and Bias
#### 10.3.4 Copyright and Policy Constraints

### 10.4 Reliability and Controllability
#### 10.4.1 Safe Generation
#### 10.4.2 Behavioral Constraints
#### 10.4.3 Action Boundaries

### 10.5 Trustworthy Systems and Risk Governance
#### 10.5.1 Risk Assessment
#### 10.5.2 Monitoring and Escalation
#### 10.5.3 Human Oversight

### 10.6 Content Moderation and Harm Mitigation
#### 10.6.1 Toxicity Detection
#### 10.6.2 Abuse Prevention
#### 10.6.3 Policy Enforcement

### 10.7 Governance, Regulation, and Compliance
#### 10.7.1 Model Governance
#### 10.7.2 Regulatory Frameworks
#### 10.7.3 Auditing and Accountability

### 10.8 Interpretability and Auditability
#### 10.8.1 Mechanistic Interpretability
#### 10.8.2 Post-Hoc Explainability
#### 10.8.3 Auditing Model Decisions

### 10.9 Watermarking, Provenance, and Synthetic Text Detection
#### 10.9.1 Watermark Design
#### 10.9.2 Detection Methods
#### 10.9.3 Provenance and Attribution

### 10.10 System-Level Security for LLMs
#### 10.10.1 Secure Deployment
#### 10.10.2 Access Control
#### 10.10.3 Defense-in-Depth Strategies

## 11. Domain Adaptation, Multilinguality, and Applications

### 11.1 Domain Adaptation
#### 11.1.1 General Domain Transfer
#### 11.1.2 Specialized Knowledge Injection
#### 11.1.3 Industry-Specific Fine-Tuning

### 11.2 Multilingual Capabilities
#### 11.2.1 Cross-Lingual Transfer
#### 11.2.2 Low-Resource Languages
#### 11.2.3 Multilingual Evaluation

### 11.3 Open-Source and Closed-Source Ecosystems
#### 11.3.1 Open Model Development
#### 11.3.2 Closed Model Ecosystems
#### 11.3.3 Licensing and Community Dynamics

### 11.4 Low-Code and No-Code LLM Applications
#### 11.4.1 Application Builders
#### 11.4.2 Workflow Automation
#### 11.4.3 End-User Customization

### 11.5 High-Risk Domain Applications and Compliance
#### 11.5.1 Healthcare
#### 11.5.2 Finance
#### 11.5.3 Public Sector and Compliance

### 11.6 LLMs in Legal Systems
#### 11.6.1 Legal Drafting
#### 11.6.2 Legal Retrieval and Analysis
#### 11.6.3 Court and Contract Applications

### 11.7 Climate, Sustainability, and Environmental Science
#### 11.7.1 Climate Analysis
#### 11.7.2 Sustainability Modeling
#### 11.7.3 Environmental Decision Support

### 11.8 Real-World Deployment and Application Gaps
#### 11.8.1 Production Constraints
#### 11.8.2 User Experience Challenges
#### 11.8.3 Reliability in Deployment

### 11.9 Industry Adoption and Business Value
#### 11.9.1 Product Integration
#### 11.9.2 Workflow Transformation
#### 11.9.3 Economic Impact

## 12. Knowledge Editing and Model Lifecycle Management

### 12.1 Knowledge Editing Methods
#### 12.1.1 Local Editing
#### 12.1.2 Global Editing
#### 12.1.3 Batch Editing

### 12.2 Continual Knowledge Acquisition and Model Updates
#### 12.2.1 Streaming Updates
#### 12.2.2 Incremental Knowledge Injection
#### 12.2.3 Update Stability

### 12.3 Machine Unlearning and Selective Forgetting
#### 12.3.1 Data Removal
#### 12.3.2 Targeted Forgetting
#### 12.3.3 Privacy and Compliance Use Cases

### 12.4 Knowledge Localization and Causal Analysis
#### 12.4.1 Parameter Localization
#### 12.4.2 Circuit Analysis
#### 12.4.3 Causal Intervention Methods

### 12.5 Factual Consistency and Conflict Resolution
#### 12.5.1 Fact Verification
#### 12.5.2 Conflict Detection
#### 12.5.3 Resolution Strategies

### 12.6 Hallucination as a Failure Mode of Knowledge Maintenance
#### 12.6.1 Missing Knowledge
#### 12.6.2 Corrupted Knowledge
#### 12.6.3 Drift and Degradation

### 12.7 Evaluation and Benchmarks for Knowledge Editing
#### 12.7.1 Editing Success
#### 12.7.2 Side Effects
#### 12.7.3 Retention and Generalization

## 13. Scientific Discovery and Research Automation

### 13.1 Drug Discovery and Molecular Design
#### 13.1.1 Molecular Property Prediction
#### 13.1.2 De Novo Design
#### 13.1.3 Candidate Screening

### 13.2 Code Generation and Automated Software Engineering
#### 13.2.1 Program Synthesis
#### 13.2.2 Code Repair
#### 13.2.3 Software Testing and Debugging

### 13.3 Mathematical Discovery and Theorem Proving
#### 13.3.1 Conjecture Generation
#### 13.3.2 Proof Assistance
#### 13.3.3 Formal Verification

### 13.4 Literature Review and Hypothesis Generation
#### 13.4.1 Automated Literature Synthesis
#### 13.4.2 Research Gap Discovery
#### 13.4.3 Hypothesis Construction

### 13.5 Experimental Design and Data Analysis
#### 13.5.1 Experimental Planning
#### 13.5.2 Statistical Analysis
#### 13.5.3 Scientific Decision Support

### 13.6 Materials Science and Physics Simulation
#### 13.6.1 Materials Discovery
#### 13.6.2 Simulation-Assisted Research
#### 13.6.3 Physics-Informed Modeling

### 13.7 Scientific Agents and Autonomous Research Pipelines
#### 13.7.1 Agentic Research Systems
#### 13.7.2 Closed-Loop Discovery
#### 13.7.3 Human-Scientist Collaboration

## 14. Human-AI Collaboration, Personalization, and Creative Generation

### 14.1 User Modeling and Personalized Systems
#### 14.1.1 Preference Modeling
#### 14.1.2 Adaptive Interaction
#### 14.1.3 Long-Term User Profiles

### 14.2 Personalization Techniques
#### 14.2.1 Retrieval-Based Personalization
#### 14.2.2 Memory-Enhanced Personalization
#### 14.2.3 Fine-Tuned Personalization

### 14.3 Conversational AI Beyond Task Completion
#### 14.3.1 Social Interaction
#### 14.3.2 Supportive Dialogue
#### 14.3.3 Long-Horizon Conversation

### 14.4 Creative Generation
#### 14.4.1 Story Generation
#### 14.4.2 Music Generation
#### 14.4.3 Art and Design Generation

### 14.5 Educational Systems and Intelligent Tutoring
#### 14.5.1 Personalized Learning
#### 14.5.2 Tutoring and Feedback
#### 14.5.3 Assessment and Adaptation

### 14.6 Human Preference Acquisition and Interactive Alignment
#### 14.6.1 Preference Elicitation
#### 14.6.2 Interactive Correction
#### 14.6.3 Human Feedback Loops

### 14.7 Accessibility, Inclusion, and Special Populations
#### 14.7.1 Assistive Technologies
#### 14.7.2 Inclusive Interface Design
#### 14.7.3 Support for Special Needs Users

## 15. Discussion and Future Directions

### 15.1 Unified Perspective on LLM Research
#### 15.1.1 Core Technical Trajectory
#### 15.1.2 Cross-Chapter Synthesis
#### 15.1.3 Persistent Structural Patterns

### 15.2 Key Trade-Offs and Open Tensions
#### 15.2.1 Scale vs Efficiency
#### 15.2.2 Capability vs Safety
#### 15.2.3 Flexibility vs Control
#### 15.2.4 Generality vs Specialization

### 15.3 Unresolved Problems
#### 15.3.1 Robust Reasoning
#### 15.3.2 Reliable Grounding
#### 15.3.3 Long-Term Memory and Lifelong Learning
#### 15.3.4 Evaluation at Scale

### 15.4 Future Research Directions
#### 15.4.1 Next-Generation Architectures
#### 15.4.2 Scalable Alignment
#### 15.4.3 Agentic and Multimodal Intelligence
#### 15.4.4 Scientific and Social Impact

### 15.5 Limitations of This Survey
#### 15.5.1 Scope Limitations
#### 15.5.2 Classification Limitations
#### 15.5.3 Rapidly Evolving Literature

### 15.6 Industrial Trends and Long-Term Outlook
#### 15.6.1 Deployment Trends
#### 15.6.2 Ecosystem Evolution
#### 15.6.3 Research-to-Product Translation

### 15.7 Conclusion
#### 15.7.1 Summary of Key Findings
#### 15.7.2 Final Remarks
