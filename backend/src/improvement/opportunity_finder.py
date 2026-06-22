import logging
from typing import Any, Dict, List
from .strategies import identify_primary_domain, ALL_DOMAINS

logger = logging.getLogger(__name__)

# Structured crossover knowledge base (Primary Domain, Underrepresented Domain) -> Actionable Suggestions
DOMAIN_CROSSOVERS = {
    ("AI", "Medical"): [
        "Deep learning EEG anomaly detection for non-invasive patient diagnostics",
        "Generative adversarial networks for synthetic patient ECG baseline modeling"
    ],
    ("AI", "Automotive"): [
        "Neuro-symbolic logic engines for safety-critical autonomous path planning",
        "Edge-based computer vision models optimized for real-time ADAS collision avoidance"
    ],
    ("AI", "Energy"): [
        "Deep reinforcement learning for real-time smart grid demand forecasting",
        "Predictive battery state-of-health estimation using recurrent neural networks"
    ],
    ("AI", "IoT"): [
        "TinyML anomaly detection on low-power sensor nodes",
        "Edge AI local feature extraction for decentralized behavioral analytics"
    ],
    ("AI", "Mechanical"): [
        "Generative design algorithms for structural topology optimization",
        "AI-driven predictive tool wear estimation in high-precision CNC machines"
    ],
    
    ("Medical", "AI"): [
        "Computer-aided diagnostic classifiers for early disease detection in clinical scans",
        "Neural network filters for patient motion artifact removal in bio-signals"
    ],
    ("Medical", "Automotive"): [
        "In-cabin capacitive vital sensors for real-time driver fatigue detection",
        "Biometric seating systems with autonomic nervous system monitoring"
    ],
    ("Medical", "Energy"): [
        "Thermoelectric body-heat harvesting for ultra-low-power cardiac pacemakers",
        "Piezoelectric kinetic energy generation for self-powered implants"
    ],
    ("Medical", "IoT"): [
        "Wearable multi-parameter biosensor telemetry patches",
        "Secure remote patient vital telemetry over low-power wide-area networks"
    ],
    ("Medical", "Mechanical"): [
        "Monolithic compliant joints for prosthetic limb finger linkages",
        "Surgical robots using zero-backlash flexure joints"
    ],

    ("IoT", "AI"): [
        "TinyML models for local network anomaly detection directly on edge gateways",
        "Local federated learning clients running on microcontrollers for user privacy"
    ],
    ("IoT", "Automotive"): [
        "Cooperative V2X vehicle-to-everything ad-hoc mesh networks",
        "Distributed road-surface telemetry using solar-powered ambient sensor arrays"
    ],
    ("IoT", "Energy"): [
        "Distributed wireless sensor grids for transformer thermal monitoring",
        "Solar battery charge telemetry reporting via LPWAN protocols"
    ],
    ("IoT", "Mechanical"): [
        "MEMS-based smart structural vibration strain gauges",
        "Piezoelectric ambient vibration energy harvesting for autonomous sensors"
    ],
    ("IoT", "Medical"): [
        "Secure remote patient vital telemetry over low-power wide-area networks",
        "Connected wearable biosensor meshes for continuous outpatient monitoring"
    ],

    ("Automotive", "AI"): [
        "Vehicular object detection models utilizing FMCW LiDAR point clouds",
        "Reinforcement learning algorithms for adaptive cruise and lane-keeping"
    ],
    ("Automotive", "Energy"): [
        "Regenerative braking energy recovery charging loops",
        "Phase-change thermal runaway containment sleeves for EV battery packs"
    ],
    ("Automotive", "IoT"): [
        "V2V vehicle-to-vehicle dynamic platoon coordination networks",
        "Connected fleet asset telemetry tracking over LPWAN bands"
    ],
    ("Automotive", "Mechanical"): [
        "Active electromagnetic dampers with kinetic regeneration capability",
        "Lightweight composite chassis joining systems for structural safety"
    ],
    ("Automotive", "Medical"): [
        "Steering-wheel embedded ECG sensors for heart-rate variability alerts",
        "Autonomous passenger cabin medical emergency detection and routing"
    ],

    ("Energy", "AI"): [
        "AI-driven localized grid dispatching using load forecasting models",
        "Predictive thermal runway models for grid-scale battery enclosures"
    ],
    ("Energy", "Automotive"): [
        "Bi-directional vehicle-to-grid power integration systems",
        "Aerodynamic solar auxiliary panels integrated into vehicle bodywork"
    ],
    ("Energy", "IoT"): [
        "Smart meter wireless mesh networks for neighborhood distribution grids",
        "Remote battery module health telemetry networks"
    ],
    ("Energy", "Mechanical"): [
        "Aero-elastic vibration dampening mechanisms for wind turbine blades",
        "Flywheel kinetic energy storage containers using magnetic bearings"
    ],
    ("Energy", "Medical"): [
        "Piezoelectric heart-pump kinetic power units",
        "Thermoelectric temperature-differential patches for active implants"
    ],

    ("Mechanical", "AI"): [
        "Reinforcement learning for high-precision robotic assembly paths",
        "Computer vision inspection arrays for structural surface defect detection"
    ],
    ("Mechanical", "Automotive"): [
        "Compliant active suspension linkages for road bump isolation",
        "Integrated dual-clutch transmission mechanical gears"
    ],
    ("Mechanical", "Energy"): [
        "High-efficiency micro-turbine runners for low-head hydro generation",
        "Dual-fluid high-efficiency heat exchangers for geothermal plants"
    ],
    ("Mechanical", "IoT"): [
        "Pneumatic actuator position sensors with embedded LPWAN transceivers",
        "MEMS-encapsulated micro-nozzle valves for fluidic device telemetry"
    ],
    ("Mechanical", "Medical"): [
        "Monolithic elastic joints for prosthetic limb finger linkages",
        "Surgical robots using zero-backlash flexure joints"
    ],
}

# Fallbacks in case domain is completely unknown
DEFAULT_OPPORTUNITIES = [
    "Acoustic sensor fusion", 
    "Edge AI local inference", 
    "Ambient thermal energy harvesting"
]

def find_low_density_opportunities(
    user_idea: str,
    retrieved_patents: List[Dict[str, Any]]
) -> List[str]:
    """
    Finds underexplored crossover combinations using a non-naive knowledge base.
    """
    # 1. Identify primary domain using the shared helper
    primary_domain = identify_primary_domain(user_idea, retrieved_patents)

    # 2. Count domains in retrieved patents to sort other domains by density
    domain_counts = {d: 0 for d in ALL_DOMAINS}
    for hit in retrieved_patents:
        domain = hit.get("domain")
        if domain in domain_counts:
            domain_counts[domain] += 1

    # 3. Sort adjacent domains by count ascending (least dense first)
    underrepresented = [
        d for d in ALL_DOMAINS 
        if d != primary_domain
    ]
    underrepresented.sort(key=lambda d: domain_counts.get(d, 0))

    # 4. Generate crossover directions from knowledge base
    crossover_directions = []
    for target_domain in underrepresented:
        key = (primary_domain, target_domain)
        options = DOMAIN_CROSSOVERS.get(key, [])
        for opt in options:
            if opt not in crossover_directions:
                crossover_directions.append(opt)
            if len(crossover_directions) >= 3:
                break
        if len(crossover_directions) >= 3:
            break

    if not crossover_directions:
        crossover_directions = list(DEFAULT_OPPORTUNITIES)

    logger.info(
        "Opportunity finder crossover complete: primary=%s, underrepresented=%s -> options=%s",
        primary_domain, underrepresented[:2], crossover_directions[:3]
    )

    return crossover_directions[:3]
