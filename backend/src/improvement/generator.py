import os
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# Attempt to load the new google-genai client
try:
    from google import genai
    from google.genai import types
    
    api_key = os.getenv("GOOGLE_API_KEY")
    if api_key:
        client = genai.Client(api_key=api_key)
        logger.info("Gemini Client successfully initialized in Improvement Generator!")
    else:
        logger.warning("GOOGLE_API_KEY not found. Improvement Generator will use fallback templates.")
        client = None
except ImportError as e:
    logger.warning("Failed to import google.genai package (%s). Improvement Generator will use fallback templates.", e)
    client = None

def generate_llm_explanation(
    idea: str,
    diagnosis: List[str],
    weaknesses: List[str],
    strategies: List[Dict[str, str]],
    alternative_directions: List[str]
) -> str:
    """
    LLM Explanation Generator.
    Acts as a patent advisor explaining the system's deterministic diagnosis and strategies.
    Does NOT decide the diagnosis or strategies, only explains them.
    Falls back gracefully if the Gemini API/Client is unavailable.
    """
    if not client:
        logger.warning("Gemini Client not initialized. Generating fallback template explanation.")
        return _generate_fallback_explanation(idea, diagnosis, weaknesses, strategies, alternative_directions)

    # Format strategies with impact and reason for prompt injection
    formatted_strategies = "\n".join(
        f"- **{s['strategy']}** (Impact: {s['impact'].upper()}): {s['reason']}"
        for s in strategies
    )

    prompt = f"""You are a professional patent innovation advisor.
The system has already analyzed the user's invention idea and determined specific diagnoses, weaknesses, strategies, and low-density directions.

USER'S INVENTION IDEA:
"{idea}"

SYSTEM DIAGNOSIS:
{", ".join(diagnosis) if diagnosis else "No critical overlaps detected"}

DETECTED WEAKNESSES:
{chr(10).join('- ' + w for w in weaknesses) if weaknesses else "- No specific weaknesses found"}

SELECTED TECHNICAL STRATEGIES:
{formatted_strategies if strategies else "No strategies selected"}

ALTERNATIVE LOW-DENSITY OPPORTUNITIES:
{", ".join(alternative_directions) if alternative_directions else "No specific alternative directions selected"}

STRICT CRITICAL RULES:
1. Explain ONLY the provided diagnosis, weaknesses, and strategies.
2. Do NOT invent your own analysis, diagnosis, or strategy. 
3. Do NOT create new technical recommendations.
4. Do NOT perform independent reasoning.
5. Do NOT introduce new technologies.
6. Generate actionable, structured, and professional recommendations explaining how the user can modify their idea based strictly on the provided strategies and opportunities. Explain the technical rationale for each of the selected strategies in relation to the identified weaknesses.
7. Keep the explanation clear, professional, and practical for an inventor. Use Markdown for formatting. Do not include introductory or concluding meta-chatter.
"""

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1
            )
        )
        explanation = response.text.strip()
        if not explanation:
            raise ValueError("Empty response received from Gemini.")
        return explanation
    except Exception as e:
        logger.error("Gemini API call failed (%s). Generating fallback explanation.", e)
        return _generate_fallback_explanation(idea, diagnosis, weaknesses, strategies, alternative_directions)

def _generate_fallback_explanation(
    idea: str,
    diagnosis: List[str],
    weaknesses: List[str],
    strategies: List[Dict[str, str]],
    alternative_directions: List[str]
) -> str:
    """
    Deterministic fallback explanation builder in case of Gemini client/network failure.
    """
    lines = [
        "### Patent Innovation & Improvement Recommendations",
        "",
        "Based on our system's deterministic assessment of your invention idea, we have identified the following areas for improvement:",
        "",
        "#### 1. Weakness Diagnosis",
    ]
    
    for w in weaknesses:
        lines.append(f"- {w}")
    if not weaknesses:
        lines.append("- No critical weaknesses detected.")
        
    lines.extend([
        "",
        "#### 2. Selected Improvement Strategies",
        "To bypass the identified prior art obstacles, we recommend implementing the following structural modifications:",
        ""
    ])
    
    for s in strategies:
        lines.append(f"- **{s['strategy']}** (Impact: {s['impact'].upper()}): {s['reason']}")
    if not strategies:
        lines.append("- No specific strategies required.")
        
    lines.extend([
        "",
        "#### 3. Alternative Low-Density Directions",
        "To maximize your probability of patent grant, consider pivoting or integrating your concept into these underexplored adjacent domains:",
        ""
    ])
    
    for d in alternative_directions:
        lines.append(f"- **{d}**: Integrate this technology to create a non-obvious, multi-domain crossover utility that current patent holders do not cover.")
    if not alternative_directions:
        lines.append("- No alternative directions identified.")
        
    lines.extend([
        "",
        "These adjustments are designed to decrease prior art similarity and move your design into a less congested, more defensible IP space."
    ])
    
    return "\n".join(lines)
