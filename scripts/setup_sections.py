import argparse
import shutil
from pathlib import Path


STRUCTURE = [
    {
        "chapter_dir": "01_introduction",
        "chapter_title": "1. Introduction and Survey Methodology",
        "sections": [
            (
                "1_1_scope_and_definitions",
                "1.1 Scope and Definitions",
                [
                    "Definitions and distinctions among large models, foundation models, LLMs, reasoning models, and multimodal LLMs",
                    "Scope and exclusions: pure vision generation, pure speech models, and traditional small models as baselines",
                ],
            ),
            (
                "1_2_motivation_for_a_large_scale_survey",
                "1.2 Motivation for a Large-Scale Survey",
                [
                    "Limitations of existing surveys: modular fragmentation and lack of unified taxonomy",
                    "Goals of this work: unified structure, cross-module comparison, and large-scale citation organization",
                ],
            ),
            (
                "1_3_literature_collection_and_organization",
                "1.3 Literature Collection and Organization",
                [
                    "Data sources, search strategies, time span, inclusion/exclusion criteria",
                    "Deduplication, clustering, citation network analysis, taxonomy construction, and quality control",
                ],
            ),
            (
                "1_4_contributions_and_organization",
                "1.4 Contributions and Organization",
                [
                    "Key contributions and unified perspective of this survey",
                    "Organization roadmap: from models to systems, from capabilities to deployment",
                ],
            ),
            (
                "1_5_related_surveys_and_comparative_review",
                "1.5 Related Surveys and Comparative Review",
                [
                    "Systematic classification and dimensional analysis of representative LLM surveys",
                    "Quantitative and qualitative gap analysis between existing surveys and this work",
                ],
            ),
            (
                "1_6_terminology_standardization_and_naming_conventions",
                "1.6 Terminology Standardization and Naming Conventions",
                [
                    "Unified definition of core technical terms resolving ambiguity across research works",
                    "Standardized specification of abbreviations for model architectures, training paradigms and evaluation methods",
                ],
            ),
            (
                "1_7_full_text_logical_framework_and_inter_module_correlation",
                "1.7 Full-Text Logical Framework and Inter-Module Correlation",
                [
                    "Progressive logical chain of each chapter and technical inheritance between adjacent modules",
                    "Correspondence between each section and the full-life-cycle framework of LLM research",
                ],
            ),
        ],
    },
    {
        "chapter_dir": "02_architecture",
        "chapter_title": "2. Architectures, Pretraining, and Scaling Foundations",
        "sections": [
            (
                "2_1_architectural_evolution",
                "2.1 Architectural Evolution",
                [
                    "Transformer paradigm, decoder-only vs encoder-decoder architectures",
                    "Dense models, mixture-of-experts (MoE), hybrid architectures, and sparse routing",
                    "Long-context architectures, memory augmentation, and recurrent/state-space extensions",
                ],
            ),
            (
                "2_2_pretraining_data",
                "2.2 Pretraining Data",
                [
                    "Data sources: web, books, code, scientific text, and conversational data",
                    "Data cleaning, deduplication, quality filtering, and privacy/legal concerns",
                    "Multilingual and domain-specific data (code, scientific corpora)",
                    "Synthetic data and curriculum design",
                ],
            ),
            (
                "2_3_objectives_and_training_dynamics",
                "2.3 Objectives and Training Dynamics",
                [
                    "Causal LM, denoising, span corruption, and mixed objectives",
                    "Scaling laws and compute-optimal training",
                    "Trade-offs between data quality, token budget, and model capacity",
                ],
            ),
            (
                "2_4_long_context_modeling",
                "2.4 Long-Context Modeling",
                [
                    "Context window scaling, positional encoding, compression, hierarchical memory",
                    "Long-document understanding, retrieval dependency, and pseudo-long-context issues",
                ],
            ),
            (
                "2_5_vocabulary_design_and_tokenization",
                "2.5 Vocabulary Design and Tokenization Technologies",
                [
                    "Evolution of tokenization paradigms including BPE, Unigram, WordPiece and SentencePiece",
                    "Tokenization optimization for multilingual, code and domain-specific corpora",
                ],
            ),
            (
                "2_6_pretraining_convergence_control_and_stability",
                "2.6 Pretraining Convergence Control and Stability Optimization",
                [
                    "Convergence metrics, overfitting identification and early stopping for large-scale pretraining",
                    "Training dynamics monitoring, loss spike resolution and stability control",
                ],
            ),
            (
                "2_7_incremental_pretraining_and_weight_reuse",
                "2.7 Incremental Pretraining and Weight Reuse Paradigms",
                [
                    "Warm-start initialization, small-to-large transfer and incremental pretraining strategies",
                    "Weight reuse, continuous pretraining and domain adaptation methods",
                ],
            ),
        ],
    },
    {
        "chapter_dir": "03_alignment",
        "chapter_title": "3. Post-Training and Alignment",
        "sections": [
            (
                "3_1_instruction_tuning",
                "3.1 Instruction Tuning",
                [
                    "Instruction dataset construction and supervised objectives",
                    "Generalization, formatting control, catastrophic forgetting, and data contamination",
                ],
            ),
            (
                "3_2_preference_learning_and_alignment",
                "3.2 Preference Learning and Alignment",
                [
                    "RLHF, RLAIF, DPO, ORPO and preference optimization frameworks",
                    "Reward design, noise, reward hacking, and over-alignment",
                ],
            ),
            (
                "3_3_post_training_for_reasoning",
                "3.3 Post-Training for Reasoning",
                [
                    "Process supervision, outcome supervision, RL-based reasoning optimization",
                    "Transition from general chat models to reasoning-oriented models",
                ],
            ),
            (
                "3_4_safety_and_policy_alignment",
                "3.4 Safety and Policy Alignment",
                [
                    "Refusal behavior, value alignment, controllability, and policy compliance",
                    "Trade-offs among helpfulness, harmlessness, and honesty",
                ],
            ),
            (
                "3_5_self_improvement_and_synthetic_supervision",
                "3.5 Self-Improvement and Synthetic Supervision",
                [
                    "Self-instruct, self-play, distillation, and synthetic preference data",
                    "Closed-loop self-training and bias accumulation",
                ],
            ),
            (
                "3_6_model_merging_and_weight_fusion",
                "3.6 Model Merging and Weight Fusion Technologies",
                [
                    "Linear merging, task arithmetic and LoRA weight fusion paradigms",
                    "Performance generalization, capability retention and cross-task interference",
                ],
            ),
            (
                "3_7_continual_post_training_and_forgetting_mitigation",
                "3.7 Continual Post-Training and Catastrophic Forgetting Mitigation",
                [
                    "Continual post-training paradigms and task incremental adaptation",
                    "Catastrophic forgetting mitigation including replay, regularization and modular fine-tuning",
                ],
            ),
            (
                "3_8_multi_task_post_training_and_negative_transfer",
                "3.8 Multi-Task Post-Training and Negative Transfer Mitigation",
                [
                    "Multi-task instruction tuning, data balancing and task grouping strategies",
                    "Negative transfer identification and mitigation in cross-task post-training",
                ],
            ),
        ],
    },
    {
        "chapter_dir": "04_context",
        "chapter_title": "4. Context Engineering, Retrieval, and External Tools",
        "sections": [
            (
                "4_1_prompting_and_in_context_learning",
                "4.1 Prompting and In-Context Learning",
                [
                    "Zero-shot, few-shot, role prompting, decomposition prompting",
                    "Sensitivity, robustness, and context length dependency",
                ],
            ),
            (
                "4_2_rag_and_graphrag",
                "4.2 RAG and GraphRAG",
                [
                    "Indexing, chunking, retrievers, reranking, fusion strategies",
                    "Faithfulness, citation grounding, multi-hop retrieval, and error propagation",
                ],
            ),
            (
                "4_3_memory_systems",
                "4.3 Memory Systems",
                [
                    "Session, episodic, and long-term memory architectures",
                    "Memory writing strategies, forgetting mechanisms, privacy and freshness",
                ],
            ),
            (
                "4_4_tool_use_and_function_calling",
                "4.4 Tool Use and Function Calling",
                [
                    "Tool selection, API interaction, code execution, environment interaction",
                    "Tool misuse, verification, recovery, and safety isolation",
                ],
            ),
            (
                "4_5_context_engineering",
                "4.5 Context Engineering",
                [
                    "Context retrieval, processing, and management pipeline",
                    "Trade-offs between cost, latency, controllability, and output quality",
                ],
            ),
            (
                "4_6_automatic_prompt_engineering_and_optimization",
                "4.6 Automatic Prompt Engineering and Optimization",
                [
                    "Automatic prompt generation and optimization including gradient-based, evolutionary and LLM-driven tuning",
                    "Prompt robustness enhancement, cross-task generalization and sensitivity mitigation",
                ],
            ),
            (
                "4_7_multi_turn_context_management_and_dialogue_tracking",
                "4.7 Multi-Turn Context Management and Dialogue State Tracking",
                [
                    "Multi-turn dialogue context compression, truncation and core information retention",
                    "Dialogue state tracking, context consistency and long-term dialogue memory management",
                ],
            ),
            (
                "4_8_rag_faithfulness_and_hallucination_mitigation",
                "4.8 RAG Faithfulness and Hallucination Mitigation",
                [
                    "Citation grounding, factuality verification and source attribution for RAG",
                    "Hallucination mitigation, error propagation control and multi-hop retrieval optimization",
                ],
            ),
        ],
    },
    {
        "chapter_dir": "05_reasoning",
        "chapter_title": "5. Reasoning Models",
        "sections": [
            ("5_1_taxonomy_of_reasoning_tasks", "5.1 Taxonomy of Reasoning Tasks", [
                "Mathematics, code, logic, planning, and scientific reasoning",
                "Neural, symbolic, and tool-augmented reasoning paradigms",
            ]),
            ("5_2_test_time_scaling", "5.2 Test-Time Scaling", [
                "Self-consistency, search, tree-based reasoning, verifiers",
                "Trade-offs between reasoning cost, accuracy, and latency",
            ]),
            ("5_3_explicit_vs_implicit_reasoning", "5.3 Explicit vs Implicit Reasoning", [
                "CoT, scratchpads, program-of-thought, process supervision",
                "Implicit reasoning and interpretability trade-offs",
            ]),
            ("5_4_self_correction_and_verification", "5.4 Self-Correction and Verification", [
                "Reflection, critique, debate, self-revision",
                "Verifier design, bias, and reward hacking",
            ]),
            ("5_5_limitations_of_reasoning_evaluation", "5.5 Limitations of Reasoning Evaluation", [
                "Benchmark contamination, memorization, leakage",
                "Process vs outcome evaluation, real vs benchmark performance",
            ]),
            ("5_6_commonsense_reasoning_and_world_knowledge", "5.6 Commonsense Reasoning and World Knowledge Grounding", [
                "Commonsense reasoning taxonomy including physical, social, temporal and causal reasoning",
                "World knowledge grounding, commonsense knowledge injection and reasoning hallucination mitigation",
            ]),
            ("5_7_formal_reasoning_and_theorem_proving", "5.7 Formal Reasoning and Theorem Proving", [
                "LLM-based formal logic reasoning, mathematical theorem proving and code formal verification",
                "Symbolic-neural hybrid reasoning, tool-augmented theorem proving and evaluation systems",
            ]),
            ("5_8_multimodal_reasoning_and_cross_modal_inference", "5.8 Multimodal Reasoning and Cross-Modal Logical Inference", [
                "Chart, document, video and 3D scene reasoning paradigms",
                "Cross-modal information alignment, logical chain construction and error propagation mitigation",
            ]),
            ("5_9_neuro_symbolic_integration_with_llms", "5.9 Neuro-Symbolic Integration with LLMs", [
                "Neuro-symbolic integration methods combining neural LLM reasoning with symbolic logic, knowledge graphs, and formal verification",
                "Hybrid architectures for reasoning, tool-augmented symbolic computation, and the trade-offs between neural flexibility and symbolic rigor",
            ]),
            ("5_10_world_models_and_llm_based_simulation", "5.10 World Models and LLM-Based Simulation", [
                "LLM-based world modeling, environment simulation, and grounded reasoning for physical and social domains",
                "World model evaluation, simulation fidelity, and the integration of LLMs with interactive environments for planning and decision-making",
            ]),
        ],
    },
    {
        "chapter_dir": "06_agents",
        "chapter_title": "6. Agentic LLMs",
        "sections": [
            ("6_1_single_agent_architectures", "6.1 Single-Agent Architectures", [
                "Perceive-plan-act-reflect loop",
                "Controller, planner, executor decomposition",
            ]),
            ("6_2_planning_memory_and_reflection", "6.2 Planning, Memory, and Reflection", [
                "Task decomposition, planning horizons, recovery strategies",
                "Memory-reflection interaction and failure modes",
            ]),
            ("6_3_multi_agent_systems", "6.3 Multi-Agent Systems", [
                "Role assignment, coordination, communication protocols",
                "Emergent collaboration and coordination failures",
            ]),
            ("6_4_interaction_environments", "6.4 Interaction Environments", [
                "Web agents, software agents, coding agents, robotics",
                "Simulation gaps and transferability challenges",
            ]),
            ("6_5_evaluation_and_safety_of_agents", "6.5 Evaluation and Safety of Agents", [
                "Success rate, efficiency, recovery ability",
                "Tool misuse, loops, lack of supervision",
            ]),
            ("6_6_human_agent_collaboration", "6.6 Human-Agent Collaboration and Interaction Paradigms", [
                "Human-in-the-loop agent architectures and interactive instruction following",
                "Human-agent feedback, user intention understanding and collaboration efficiency",
            ]),
            ("6_7_agent_lifelong_learning_and_environmental_adaptation", "6.7 Agent Lifelong Learning and Environmental Adaptation", [
                "Online learning in dynamic environments, experience replay and policy update",
                "Cross-environment transfer, domain adaptation and failure mode learning",
            ]),
            ("6_8_agent_development_frameworks_and_engineering", "6.8 Agent Development Frameworks and Engineering Practice", [
                "Mainstream agent frameworks, core component design and modular construction",
                "Engineering practice, deployment optimization and industrial case analysis",
            ]),
        ],
    },
    {
        "chapter_dir": "07_multimodal",
        "chapter_title": "7. Multimodal Large Models",
        "sections": [
            ("7_1_architectures", "7.1 Architectures", [
                "Vision encoders, connectors, unified vs modular designs",
                "Extensions to audio, video, documents, OCR",
            ]),
            ("7_2_data_and_pretraining", "7.2 Data and Pretraining", [
                "Image-text, speech-text, video-text, document-text corpora",
                "Data imbalance, labeling cost, quality issues",
            ]),
            ("7_3_post_training_and_alignment", "7.3 Post-Training and Alignment", [
                "Multimodal instruction tuning and alignment",
                "Hallucination and cross-modal inconsistency",
            ]),
            ("7_4_multimodal_reasoning", "7.4 Multimodal Reasoning", [
                "Document, chart, and video reasoning",
                "Integration with OCR and retrieval tools",
            ]),
            ("7_5_multimodal_safety", "7.5 Multimodal Safety", [
                "Cross-modal attacks, bias, privacy risks",
                "Gaps in evaluation and safety guarantees",
            ]),
            ("7_6_multimodal_in_context_learning_and_cross_modal_transfer", "7.6 Multimodal In-Context Learning and Cross-Modal Transfer", [
                "Few-shot/zero-shot cross-modal in-context learning paradigms",
                "Cross-modal knowledge alignment and generalized multimodal ICL enhancement",
            ]),
            ("7_7_unified_multimodal_generation_capabilities", "7.7 Unified Multimodal Generation Capabilities", [
                "LLM-driven cross-modal generation including text-to-image, text-to-video and multimodal-to-multimodal",
                "Multimodal generation alignment, hallucination control and generation quality evaluation",
            ]),
            ("7_8_cross_modal_alignment_and_representation_learning", "7.8 Cross-Modal Alignment and Representation Learning", [
                "Cross-modal representation alignment including contrastive learning and generative alignment",
                "Modality gap bridging, semantic consistency and cross-modal generalization",
            ]),
        ],
    },
    {
        "chapter_dir": "08_efficiency",
        "chapter_title": "8. Efficiency, Systems, and Deployment",
        "sections": [
            ("8_1_training_efficiency", "8.1 Training Efficiency", [
                "Parallelism, memory optimization, mixed precision",
                "Data efficiency and curriculum learning",
            ]),
            ("8_2_inference_efficiency", "8.2 Inference Efficiency", [
                "Quantization, pruning, distillation, speculative decoding",
                "Latency vs throughput vs quality trade-offs",
            ]),
            ("8_3_parameter_efficient_fine_tuning", "8.3 Parameter-Efficient Fine-Tuning", [
                "LoRA, adapters, prompt tuning",
                "Composition and interference issues",
            ]),
            ("8_4_deployment_architectures", "8.4 Deployment Architectures", [
                "Cloud, distributed, edge, and on-device deployment",
                "Stability, updates, and system bottlenecks",
            ]),
            ("8_5_cost_and_sustainability", "8.5 Cost and Sustainability", [
                "Training/inference economics",
                "Energy consumption and environmental impact",
            ]),
            ("8_6_hardware_accelerated_optimization_and_heterogeneous_deployment", "8.6 Hardware-Accelerated Optimization and Heterogeneous Deployment", [
                "Hardware-adapted optimization for GPU, NPU, FPGA, kernel optimization and operator fusion",
                "Heterogeneous computing, cloud-edge-end hybrid deployment and hardware-software co-design",
            ]),
            ("8_7_fault_tolerance_and_reliability_of_distributed_systems", "8.7 Fault Tolerance and Reliability of Distributed Systems", [
                "Fault tolerance, failure recovery and elastic scaling for distributed LLM training",
                "High-availability inference architecture, traffic scheduling and stability under high concurrency",
            ]),
            ("8_8_edge_deployment_and_lightweight_model_optimization", "8.8 Edge Deployment and Lightweight Model Optimization", [
                "End-to-end lightweight optimization for edge devices including quantization, pruning and sparse optimization",
                "Resource-constrained edge adaptation, on-device inference and lightweight deployment",
            ]),
            ("8_9_small_language_models_and_knowledge_distillation_at_scale", "8.9 Small Language Models and Knowledge Distillation at Scale", [
                "Small language model design principles, knowledge distillation from large to small models, and capability preservation techniques",
                "Evaluation of distilled models, task-specific small models, and the trade-offs between model size, inference cost, and capability",
            ]),
            ("8_10_llm_data_centers_and_infrastructure_architecture", "8.10 LLM Data Centers and Infrastructure Architecture", [
                "Data center architecture for LLM training and inference, including GPU cluster design, network topology, and storage systems",
                "Infrastructure optimization, power efficiency, cooling systems, and the environmental impact of large-scale LLM computing facilities",
            ]),
        ],
    },
    {
        "chapter_dir": "09_evaluation",
        "chapter_title": "9. Evaluation Frameworks",
        "sections": [
            ("9_1_benchmark_taxonomy", "9.1 Benchmark Taxonomy", [
                "General, domain-specific, and target-specific benchmarks",
                "Static vs dynamic vs environment-based evaluation",
            ]),
            ("9_2_capability_evaluation", "9.2 Capability Evaluation", [
                "Language, reasoning, coding, long-context, multilingual",
                "Multimodal and agent evaluation",
            ]),
            ("9_3_evaluation_methodologies", "9.3 Evaluation Methodologies", [
                "Human evaluation, pairwise comparison, rubric-based scoring",
                "LLM-as-a-judge and bias issues",
            ]),
            ("9_4_reliability_of_evaluation", "9.4 Reliability of Evaluation", [
                "Contamination, leakage, benchmark saturation",
                "Reproducibility and instability",
            ]),
            ("9_5_holistic_evaluation", "9.5 Holistic Evaluation", [
                "Utility, faithfulness, latency, cost, safety",
                "Shift from offline to online evaluation",
            ]),
        ],
    },
    {
        "chapter_dir": "10_safety",
        "chapter_title": "10. Safety, Trustworthiness, and Security",
        "sections": [
            ("10_1_reliability_and_hallucination", "10.1 Reliability and Hallucination", [
                "Factuality, uncertainty, calibration",
                "Grounding and uncertainty expression",
            ]),
            ("10_2_adversarial_and_system_security", "10.2 Adversarial and System Security", [
                "Jailbreaks, prompt injection, tool attacks",
                "Data poisoning, backdoors, extraction attacks",
            ]),
            ("10_3_privacy_copyright_and_fairness", "10.3 Privacy, Copyright, and Fairness", [
                "Memorization and privacy leakage",
                "Bias and fairness issues",
            ]),
            ("10_4_agent_risks", "10.4 Agent Risks", [
                "Goal misgeneralization and cascading failures",
                "Oversight and containment strategies",
            ]),
            ("10_5_trustworthy_systems", "10.5 Trustworthy Systems", [
                "Reliability, accountability, explainability",
                "Secure system design principles",
            ]),
            ("10_9_llm_watermarking_and_synthetic_text_detection", "10.9 LLM Watermarking and Synthetic Text Detection", [
                "LLM watermarking techniques including statistical watermarks, learning-based watermarks, and embedding-based approaches for generated text",
                "Synthetic text detection methods, watermark robustness, evasion attacks, and the trade-offs between watermark quality and text generation performance",
            ]),
            ("10_10_llm_operating_systems_and_system_level_security", "10.10 LLM Operating Systems and System-Level Security", [
                "LLM operating system architectures, system-level security mechanisms, and sandbox designs for LLM-based computing platforms",
                "Security challenges in LLM-integrated systems, access control, privilege management, and runtime monitoring frameworks",
            ]),
        ],
    },
    {
        "chapter_dir": "11_applications",
        "chapter_title": "11. Domain Adaptation, Multilinguality, and Applications",
        "sections": [
            ("11_1_domain_adaptation", "11.1 Domain Adaptation", [
                "Continued pretraining, RAG, fine-tuning",
                "Expert supervision and high-risk constraints",
            ]),
            ("11_2_multilingual_capabilities", "11.2 Multilingual Capabilities", [
                "Cross-lingual transfer and low-resource settings",
                "Cultural grounding and fairness",
            ]),
            ("11_3_high_value_applications", "11.3 High-Value Applications", [
                "Medicine, law, finance, education, science",
                "Deployment and validation challenges",
            ]),
            ("11_4_benchmark_vs_real_world_gap", "11.4 Benchmark vs Real-World Gap", [
                "Misalignment between benchmarks and real usage",
                "Human-in-the-loop and system auditing",
            ]),
            ("11_8_llms_in_legal_systems_and_regulatory_technology", "11.8 LLMs in Legal Systems and Regulatory Technology", [
                "LLM applications in legal systems including contract analysis, case law research, legal document drafting, and regulatory compliance automation",
                "Challenges of legal LLM deployment including hallucination in legal contexts, bias in legal reasoning, and regulatory framework adaptation",
            ]),
            ("11_9_llms_for_climate_sustainability_and_environmental_science", "11.9 LLMs for Climate, Sustainability, and Environmental Science", [
                "LLM applications for climate modeling, environmental monitoring, sustainability assessment, and ecological data analysis",
                "Green AI initiatives, LLM-driven environmental policy analysis, and the carbon footprint optimization of large-scale model training and deployment",
            ]),
        ],
    },
    {
        "chapter_dir": "12_discussion",
        "chapter_title": "12. Discussion and Future Directions",
        "sections": [
            ("12_1_unified_perspective", "12.1 Unified Perspective", [
                "Model-centric, system-centric, environment-centric paradigms",
                "Knowledge integration: parametric, retrieval, tool, interaction",
            ]),
            ("12_2_key_trade_offs", "12.2 Key Trade-offs", [
                "Scale vs alignment, reasoning vs efficiency, general vs specialized",
                "Benchmark performance vs real-world utility",
            ]),
            ("12_3_future_research_directions", "12.3 Future Research Directions", [
                "Trustworthy agents, persistent memory, scientific evaluation",
                "Data-centric post-training and multimodal interaction",
            ]),
            ("12_4_conclusion", "12.4 Conclusion", [
                "Evolution of large model research paradigms",
                "Toward survey as infrastructure rather than narrative",
            ]),
        ],
    },
    {
        "chapter_dir": "13_knowledge_editing",
        "chapter_title": "13. LLM Knowledge Editing and Lifecycle Management",
        "sections": [
            ("13_1_knowledge_editing_methods", "13.1 Knowledge Editing Methods", [
                "Model editing methods including ROME, MEMIT, KN, and insertion-level, modification-level, and erasure-level editing paradigms",
                "Editing scope, side effects, scalability, and batch editing challenges for large language models",
            ]),
            ("13_2_model_updating_and_continual_knowledge_acquisition", "13.2 Model Updating and Continual Knowledge Acquisition", [
                "Continual knowledge updating methods for LLMs, including knowledge injection, temporal knowledge adaptation, and dynamic knowledge bases",
                "Knowledge freshness maintenance, version control, and update-consistency evaluation across model revisions",
            ]),
            ("13_3_machine_unlearning_and_selective_forgetting", "13.3 Machine Unlearning and Selective Forgetting", [
                "Machine unlearning methods for LLMs, including exact unlearning, approximate unlearning, and gradient-based selective forgetting",
                "Unlearning verification, privacy guarantees, and the tension between forgetting completeness and model utility preservation",
            ]),
            ("13_4_knowledge_localization_and_circuit_analysis", "13.4 Knowledge Localization and Circuit Analysis", [
                "Knowledge localization methods in LLMs, including causal tracing, mechanistic interpretability, and knowledge circuit identification",
                "Circuit-level analysis of factual storage, relational reasoning, and multi-hop knowledge retrieval pathways in transformer architectures",
            ]),
            ("13_5_factual_consistency_and_knowledge_conflict_resolution", "13.5 Factual Consistency and Knowledge Conflict Resolution", [
                "Factual consistency evaluation and enhancement methods for LLMs, including knowledge conflict detection and multi-source knowledge reconciliation",
                "Knowledge conflict resolution strategies across parametric memory, retrieved context, and instruction-following constraints",
            ]),
            ("13_6_hallucination_as_knowledge_failure_mode", "13.6 Hallucination as Knowledge Failure Mode", [
                "Knowledge-level analysis of hallucination, distinguishing factual errors, fabricated reasoning, and source confabulation as distinct failure modes",
                "Knowledge-grounded hallucination mitigation strategies, including retrieval augmentation, knowledge verification, and confidence calibration",
            ]),
            ("13_7_knowledge_editing_evaluation_and_benchmarks", "13.7 Knowledge Editing Evaluation and Benchmarks", [
                "Evaluation frameworks and benchmarks for knowledge editing methods, including locality, generality, portability, and efficacy metrics",
                "Comprehensive comparison of editing approaches across model scales, task domains, and evaluation dimensions",
            ]),
        ],
    },
    {
        "chapter_dir": "14_scientific_discovery",
        "chapter_title": "14. LLM-Driven Scientific Discovery and Research Automation",
        "sections": [
            ("14_1_llms_in_drug_discovery_and_molecular_design", "14.1 LLMs in Drug Discovery and Molecular Design", [
                "LLM-based molecular design, drug-target interaction prediction, and de novo molecule generation with language model approaches",
                "Integration of LLMs with molecular databases, ADMET prediction, and multi-objective optimization in pharmaceutical research",
            ]),
            ("14_2_llms_for_code_generation_and_automated_software_engineering", "14.2 LLMs for Code Generation and Automated Software Engineering", [
                "LLM-driven code generation, program synthesis, and automated debugging across programming languages and domains",
                "Automated software engineering pipelines including test generation, code review, refactoring, and repository-level understanding",
            ]),
            ("14_3_llms_in_mathematical_discovery_and_theorem_proving", "14.3 LLMs in Mathematical Discovery and Theorem Proving", [
                "LLM-based mathematical reasoning, conjecture generation, and automated theorem proving in Lean, Isabelle, and Coq",
                "Neural-symbolic hybrid approaches, proof search strategies, and autoformalization of mathematical text",
            ]),
            ("14_4_llms_for_scientific_literature_review_and_hypothesis_generation", "14.4 LLMs for Scientific Literature Review and Hypothesis Generation", [
                "LLM-driven scientific literature mining, cross-paper synthesis, and automated hypothesis generation from research corpora",
                "Knowledge graph construction from scientific literature, citation analysis, and research trend prediction",
            ]),
            ("14_5_llms_in_experimental_design_and_data_analysis", "14.5 LLMs in Experimental Design and Data Analysis", [
                "LLM-assisted experimental design, statistical analysis planning, and automated data interpretation across scientific domains",
                "Integration of LLMs with automated laboratory systems, experiment optimization, and closed-loop scientific discovery",
            ]),
            ("14_6_llms_for_materials_science_and_physical_simulation", "14.6 LLMs for Materials Science and Physical Simulation", [
                "LLM applications in materials discovery, property prediction, and materials design with language model interfaces",
                "LLM-driven physical simulation, equation discovery, and scientific computing augmentation",
            ]),
            ("14_7_scientific_agent_systems_and_autonomous_research_pipelines", "14.7 Scientific Agent Systems and Autonomous Research Pipelines", [
                "End-to-end scientific agent systems integrating literature review, hypothesis generation, experimental design, and result interpretation",
                "Autonomous research pipelines, self-driving laboratories, and the future of AI-augmented scientific workflows",
            ]),
        ],
    },
    {
        "chapter_dir": "15_personalization",
        "chapter_title": "15. LLM Personalization, Creative Generation, and Human-AI Collaboration",
        "sections": [
            ("15_1_personalized_llm_systems_and_user_modeling", "15.1 Personalized LLM Systems and User Modeling", [
                "Personalized LLM systems including user profile modeling, preference learning, and adaptive response generation",
                "User modeling architectures, long-term preference tracking, and cross-session personalization strategies",
            ]),
            ("15_2_llm_personalization_techniques", "15.2 LLM Personalization Techniques (Profile, Memory, Adaptation)", [
                "Core personalization techniques including profile-based adaptation, personalized memory systems, and fine-tuning for individual users",
                "Personalization evaluation, privacy-preserving personalization, and the cold-start problem in LLM personalization",
            ]),
            ("15_3_conversational_ai_beyond_task_completion", "15.3 Conversational AI Beyond Task Completion", [
                "Conversational AI systems for open-domain dialogue, social chatbots, and relationship-building interactions with LLMs",
                "Long-term conversational engagement, emotional intelligence, and personality-consistent dialogue systems",
            ]),
            ("15_4_creative_generation_storytelling_music_and_art", "15.4 Creative Generation: Storytelling, Music, and Art with LLMs", [
                "LLM-driven creative generation including story generation, poetry, screenplay writing, and narrative design",
                "LLM applications in music composition, visual art prompting, and cross-modal creative collaboration",
            ]),
            ("15_5_llm_based_educational_systems_and_intelligent_tutoring", "15.5 LLM-Based Educational Systems and Intelligent Tutoring", [
                "LLM-powered educational systems including intelligent tutoring, adaptive learning, and automated assessment",
                "Pedagogical strategies with LLMs, student modeling, and the effectiveness of AI tutoring in classroom settings",
            ]),
            ("15_6_human_preference_elicitation_and_interactive_alignment", "15.6 Human Preference Elicitation and Interactive Alignment", [
                "Interactive alignment methods including real-time preference elicitation, feedback-driven adaptation, and human-in-the-loop optimization",
                "Preference aggregation across diverse user populations, ethical considerations, and alignment with individual vs collective values",
            ]),
            ("15_7_accessibility_inclusive_ai_and_special_populations", "15.7 Accessibility, Inclusive AI, and LLMs for Special Populations", [
                "LLM applications for accessibility including assistive technologies, sign language translation, and cognitive support tools",
                "Inclusive AI design, multilingual accessibility, and LLM-based support for neurodivergent and disabled populations",
            ]),
        ],
    },
]


RAG_FILES = {
    "rag_candidates.csv": "candidates.csv",
    "rag_selected.csv": "selected.csv",
    "rag_notes.jsonl": "notes.jsonl",
}


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build_section_readme(chapter_title: str, section_title: str, paragraphs: list[str]) -> str:
    lines = [
        f"# {section_title}",
        "",
        f"Chapter: {chapter_title}",
        "",
        "## Focus",
    ]
    for index, paragraph in enumerate(paragraphs, start=1):
        lines.append(f"- Para {index}: {paragraph}")
    lines.extend(
        [
            "",
            "## Working Files",
            "- `candidates.csv`: keyword-retrieved candidate papers",
            "- `selected.csv`: filtered papers with complete title/abstract/year/authors",
            "- `notes.jsonl`: LLM annotations with decision, category, and one-sentence summary",
            "- `draft.md`: optional drafting notes for this subsection",
            "",
            "## Minimal Workflow",
            "1. Run `build_candidates.py` to create `candidates.csv`.",
            "2. Run `filter_selected.py` to create `selected.csv`.",
            "3. Run `annotate_with_llm.py` to create `notes.jsonl`.",
        ]
    )
    return "\n".join(lines) + "\n"


def build_index(structure: list[dict]) -> str:
    lines = ["# Section Workspace", "", "This folder mirrors the outline at the subsection level.", ""]
    for chapter in structure:
        chapter_path = chapter["chapter_dir"]
        lines.append(f"## {chapter['chapter_title']}")
        for section_dir, section_title, _ in chapter["sections"]:
            lines.append(f"- `{chapter_path}/{section_dir}`: {section_title}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def move_rag_files(base_dir: Path) -> None:
    source_dir = base_dir / "04_context"
    target_dir = source_dir / "4_2_rag_and_graphrag"
    target_dir.mkdir(parents=True, exist_ok=True)
    for source_name, target_name in RAG_FILES.items():
        source_path = source_dir / source_name
        if source_path.exists():
            shutil.move(str(source_path), str(target_dir / target_name))


def main() -> None:
    parser = argparse.ArgumentParser(description="Create subsection folders that mirror the outline.")
    parser.add_argument(
        "--sections-dir",
        default="2_sections",
        help="Path to the 2_sections directory.",
    )
    args = parser.parse_args()

    sections_dir = Path(args.sections_dir)
    sections_dir.mkdir(parents=True, exist_ok=True)

    for chapter in STRUCTURE:
        chapter_dir = sections_dir / chapter["chapter_dir"]
        chapter_dir.mkdir(parents=True, exist_ok=True)
        for section_dir, section_title, paragraphs in chapter["sections"]:
            section_path = chapter_dir / section_dir
            section_path.mkdir(parents=True, exist_ok=True)
            readme_path = section_path / "README.md"
            if not readme_path.exists():
                readme_text = build_section_readme(
                    chapter_title=chapter["chapter_title"],
                    section_title=section_title,
                    paragraphs=paragraphs,
                )
                write_text(readme_path, readme_text)

    move_rag_files(sections_dir)
    write_text(sections_dir / "README.md", build_index(STRUCTURE))

    print(f"Section structure prepared under {sections_dir}")


if __name__ == "__main__":
    main()
