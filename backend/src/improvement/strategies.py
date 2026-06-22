import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# Core system domains
ALL_DOMAINS = ["AI", "Automotive", "Energy", "IoT", "Mechanical", "Medical"]

# Deterministic domain-specific mapping of problems to technical improvement strategies with impact and rationale.
DOMAIN_RULES = {
    "AI": {
        "high_semantic_overlap": [
            {
                "strategy": "Replace standard CNN/Transformer layers with Spiking Neural Networks (SNN)",
                "impact": "high",
                "reason": "Reduces similarity to basic deep learning prior art by shifting to event-driven, neuromorphic processing."
            },
            {
                "strategy": "Implement privacy-preserving Federated Learning architectures",
                "impact": "medium",
                "reason": "Differentiates from centralized models by shifting model training to decentralized edge nodes without data pooling."
            }
        ],
        "high_graph_overlap": [
            {
                "strategy": "Integrate dynamic Neural Architecture Search (NAS) engines",
                "impact": "medium",
                "reason": "Generates optimized, non-obvious network designs dynamically, separating structural relational attributes."
            }
        ],
        "crowded_domain": [
            {
                "strategy": "Pivot to localized TinyML anomaly detection on constraint edge devices",
                "impact": "high",
                "reason": "Avoids crowded cloud-based deep learning patents by running inference completely offline on resource-constrained hardware."
            }
        ],
        "low_novelty": [
            {
                "strategy": "Incorporate neuro-symbolic reasoning layers",
                "impact": "high",
                "reason": "Combines connectionist neural networks with logic-based symbolic engines to achieve highly non-obvious decision pipelines."
            }
        ]
    },
    "Medical": {
        "high_semantic_overlap": [
            {
                "strategy": "Shift invasive blood/vital sensing to non-invasive optical spectroscopy",
                "impact": "high",
                "reason": "Avoids direct vital contact prior art by utilizing absorption spectrum signatures at specific wavelengths."
            },
            {
                "strategy": "Utilize sub-dermal capacitive coupling instead of galvanic leads",
                "impact": "medium",
                "reason": "Differentiates sensing mechanics by measuring electric field changes without direct skin conduction."
            }
        ],
        "high_graph_overlap": [
            {
                "strategy": "Implement a closed-loop biofeedback neuro-modulation control loop",
                "impact": "high",
                "reason": "Transitions the device from passive biosignal monitoring to active therapeutic feedback correction."
            }
        ],
        "crowded_domain": [
            {
                "strategy": "Target low-density clinical applications such as adaptive neurogaming rehabilitation",
                "impact": "medium",
                "reason": "Bypasses general patient monitoring spaces by tailoring feedback loops to cognitive motor rehabilitation."
            }
        ],
        "low_novelty": [
            {
                "strategy": "Integrate synthetic patient data augmentation using generative models",
                "impact": "medium",
                "reason": "Differentiates clinical training models by utilizing localized differential privacy patient data generators."
            }
        ]
    },
    "IoT": {
        "high_semantic_overlap": [
            {
                "strategy": "Implement hardware-enclave (TEE) decentralized device identity and routing",
                "impact": "high",
                "reason": "Secures sensor payload routing at the silicon layer, avoiding common software-based PKI prior art."
            },
            {
                "strategy": "Utilize LPWAN sensor mesh routing protocols",
                "impact": "medium",
                "reason": "Replaces simple point-to-point cellular/WiFi topologies with cooperative multi-hop low-power architectures."
            }
        ],
        "high_graph_overlap": [
            {
                "strategy": "Use multimodal sensor fusion on-edge",
                "impact": "high",
                "reason": "Bypasses crowded cloud-processing patent spaces by performing local feature blending directly on the microcontroller."
            }
        ],
        "crowded_domain": [
            {
                "strategy": "Combine with mechanical structural systems to target industrial wear telemetry",
                "impact": "medium",
                "reason": "Pivots the IoT utility from general environmental sensing to specific industrial machine component diagnostics."
            }
        ],
        "low_novelty": [
            {
                "strategy": "Integrate zero-power ambient RF energy harvesting",
                "impact": "high",
                "reason": "Eliminates battery dependencies entirely by powering nodes using environmental electromagnetic fields."
            }
        ]
    },
    "Automotive": {
        "high_semantic_overlap": [
            {
                "strategy": "Shift computer vision inputs from RGB cameras to FMCW LiDAR point clouds",
                "impact": "high",
                "reason": "Avoids overlap with basic visual object detection patents by using coherent range-rate measurements."
            }
        ],
        "high_graph_overlap": [
            {
                "strategy": "Implement V2X vehicle-to-everything predictive collision avoidance",
                "impact": "medium",
                "reason": "Expands isolated sensor capabilities by using cooperative wireless telemetry."
            }
        ],
        "crowded_domain": [
            {
                "strategy": "Add localized hardware-in-the-loop driver drowsiness biometric sensors",
                "impact": "medium",
                "reason": "Differentiates basic navigation or control utility by incorporating seat/steering biosensors."
            }
        ],
        "low_novelty": [
            {
                "strategy": "Integrate active electromagnetic suspension vibration energy recovery",
                "impact": "high",
                "reason": "Combines active chassis stability actuators with dynamic regenerative power generation."
            }
        ]
    },
    "Energy": {
        "high_semantic_overlap": [
            {
                "strategy": "Replace standard lithium-ion cells with solid-state sodium-ion chemistry",
                "impact": "high",
                "reason": "Differentiates battery physical layout and thermal requirements from common patent disclosures."
            }
        ],
        "high_graph_overlap": [
            {
                "strategy": "Deploy smart grid distributed peer-to-peer micro-transactions using smart contracts",
                "impact": "medium",
                "reason": "Integrates localized dispatching control logic directly into the transaction layer."
            }
        ],
        "crowded_domain": [
            {
                "strategy": "Target localized micro-hydro or micro-wind thermal management loops",
                "impact": "medium",
                "reason": "Bypasses grid-scale patents by focusing on residential-scale localized energy generation."
            }
        ],
        "low_novelty": [
            {
                "strategy": "Introduce thermoelectric thermal-runaway dampening sheets",
                "impact": "high",
                "reason": "Uses phase-change cooling coupled with peltier electricity generation for dual-safety."
            }
        ]
    },
    "Mechanical": {
        "high_semantic_overlap": [
            {
                "strategy": "Use compliant mechanisms instead of multi-part geared hinges",
                "impact": "high",
                "reason": "Achieves mechanical motion through elastic deformation of a single body, eliminating friction and wear patents."
            }
        ],
        "high_graph_overlap": [
            {
                "strategy": "Incorporate active piezoelectric damping elements",
                "impact": "medium",
                "reason": "Switches from passive structural isolation to active mechanical vibration attenuation."
            }
        ],
        "crowded_domain": [
            {
                "strategy": "Design with additive-manufacturing-optimized internal topology lattices",
                "impact": "medium",
                "reason": "Uses complex structures that can only be fabricated through 3D printing to achieve strength-to-weight ratios."
            }
        ],
        "low_novelty": [
            {
                "strategy": "Implement MEMS-encapsulated micro-nozzle valves for fluidic device telemetry",
                "impact": "medium",
                "reason": "Combines micro-fluidic control with silicon-etched channels for highly precise flow rates."
            }
        ]
    }
}

DEFAULT_STRATEGIES = [
    {
        "strategy": "Optimize system configuration parameters for specific edge nodes",
        "impact": "medium",
        "reason": "Fine-tunes operational parameters without modifying the core system architecture."
    },
    {
        "strategy": "Perform a wider multi-jurisdictional patent analysis",
        "impact": "low",
        "reason": "Identifies minor niche prior art in regions outside primary filing office."
    }
]

def identify_primary_domain(user_idea: str, retrieved_patents: List[Dict[str, Any]]) -> str:
    """
    Identifies the primary domain based on count frequency in retrieved patents 
    with keyword fallback.
    """
    domain_counts = {d: 0 for d in ALL_DOMAINS}
    for hit in retrieved_patents:
        domain = hit.get("domain")
        if domain in domain_counts:
            domain_counts[domain] += 1

    primary_domain = None
    max_count = 0
    for d, count in domain_counts.items():
        if count > max_count:
            max_count = count
            primary_domain = d

    if not primary_domain:
        idea_lower = user_idea.lower()
        if any(kw in idea_lower for kw in ["eeg", "seizure", "medical", "clinical", "health", "care", "brain", "patient", "disease"]):
            primary_domain = "Medical"
        elif any(kw in idea_lower for kw in ["vehicle", "car", "automotive", "road", "pothole", "driver", "adas", "lidar"]):
            primary_domain = "Automotive"
        elif any(kw in idea_lower for kw in ["solar", "battery", "energy", "grid", "turbine", "power", "cell"]):
            primary_domain = "Energy"
        elif any(kw in idea_lower for kw in ["sensor", "iot", "wearable", "smart", "wireless", "telemetry", "enclave"]):
            primary_domain = "IoT"
        elif any(kw in idea_lower for kw in ["ai", "machine learning", "neural", "deep learning", "model", "cnn", "transformer"]):
            primary_domain = "AI"
        else:
            primary_domain = "Mechanical"
            
    return primary_domain

def choose_improvement_strategies(problems: List[str], domain: str) -> List[Dict[str, str]]:
    """
    Deterministic domain-aware strategy selection engine.
    Converts detected problems into technical improvement strategies tailored to the domain.
    Each strategy contains 'strategy', 'impact', and 'reason'.
    """
    strategies = []
    seen = set()
    
    if domain not in DOMAIN_RULES:
        domain = "AI"  # Default fallback
        
    rules = DOMAIN_RULES[domain]
    
    for problem in problems:
        if problem in rules:
            for item in rules[problem]:
                strategy_text = item["strategy"]
                if strategy_text not in seen:
                    seen.add(strategy_text)
                    strategies.append(item)
                    
    # Sort strategies so "high" impact comes first, then "medium", then "low"
    impact_order = {"high": 0, "medium": 1, "low": 2}
    strategies.sort(key=lambda x: impact_order.get(x["impact"].lower(), 3))

    if not strategies:
        strategies = list(DEFAULT_STRATEGIES)

    logger.info("Domain-aware strategy engine selected %d strategies for domain %s", len(strategies), domain)
    return strategies
