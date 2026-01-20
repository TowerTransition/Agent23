"""
Expert Lens Manager - Module for selecting expert lenses and managing content state.

This module handles the autonomous selection of expert lenses (e.g., "what everyone gets wrong",
"the real constraint", "where this breaks at scale"), manages state persistence to avoid
repetition, and creates content plans that guide the text generation process.
"""

import json
import os
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Fixed cycle of expert lenses
LENS_CYCLE = [
    "What Everyone Gets Wrong",
    "The Real Constraint",
    "How This Plays Out in Practice",
    "Where This Breaks at Scale",
    "The Hidden Tradeoff",
    "How We Evaluate It",
    "What Changes After Adoption",
    "The Open Question We're Exploring",
]

# Post types associated with each lens
POST_TYPES_BY_LENS = {
    "What Everyone Gets Wrong": ["Correction"],
    "The Real Constraint": ["Constraint-First"],
    "How This Plays Out in Practice": ["Workflow Walkthrough"],
    "Where This Breaks at Scale": ["Scale Failure Mode"],
    "The Hidden Tradeoff": ["Tradeoff Analysis"],
    "How We Evaluate It": ["Decision Framework"],
    "What Changes After Adoption": ["Second-Order Effects"],
    "The Open Question We're Exploring": ["Field Note"],
}

# Subtle brand anchoring phrases (rotated to avoid repetition)
# KEEP: These are neutral openers that add variety without shifting domain.
BRAND_PHRASES = [
    "What we're noticing:",
    "The real moment that matters:",
    "A grounded way to look at it:",
]

# Quiet brand anchors (subtle, non-salesy brand mentions)
# KEEP but CHANGE: Remove "AI workflow mapping across industries" because it causes domain drift.
QUIET_BRAND_ANCHORS = [
    "This is the kind of clarity-first framing we build at Elevare.",
    "Elevare lens: people move faster once the next step is clear.",
    "We keep studying what helps people act under pressure.",
]

# Brand signature
SIGNATURE = "— Elevare by Amaziah"

# Banned hype phrases (never use these)
BANNED_HYPE = {
    "unlock the power",
    "revolutionize",
    "game-changer",
    "are you ready",
    "cutting-edge",
    "seamless",
    "transform",
}

# Domain workflow skeletons - enforce decision + constraint + risk owner
# CHANGE: Align to your 3 trained domains only.
DOMAIN_WORKFLOW_MAP = {
    "Foreclosures": {
        "decision": "What is the next best step for the homeowner to take right now (without giving legal advice)?",
        "constraint": "High uncertainty, time pressure, emotional overwhelm, and incomplete information.",
        "risk_owner": "Homeowner (stress + missed deadlines) and any professionals they consult (accuracy and boundaries).",
        "human_roles": ["Homeowner", "Housing counselor / attorney", "Servicer / lender representative"],
    },
    "Assisted Living": {
        "decision": "What care path should the family explore next (without medical advice)?",
        "constraint": "Time pressure, limited availability, cost constraints, and family uncertainty/emotions.",
        "risk_owner": "Family decision-maker (fit and safety) and care provider team (quality and communication).",
        "human_roles": ["Family decision-maker", "Caregiver", "Community admissions / care team"],
    },
    "Trading Futures": {
        "decision": "Do we enter, exit, reduce risk, or stand down under the current rules?",
        "constraint": "Volatility, slippage, execution limits, and drawdown/consistency rules.",
        "risk_owner": "Trader (discipline and sizing) and prop firm/broker ruleset (compliance constraints).",
        "human_roles": ["Trader", "Risk rules / prop constraints", "Execution platform"],
    },
    # Default fallback for unknown domains
    "General": {
        "decision": "What action should be taken given current conditions and constraints?",
        "constraint": "Limited resources, time pressure, and uncertainty in outcomes.",
        "risk_owner": "Decision maker and stakeholders (consequences of poor decisions).",
        "human_roles": ["Decision maker", "Operator", "Stakeholder"],
    },
}

# AI framing rules (how to present AI in content)
# CHANGE: Make these domain-neutral so they don't force 'AI' framing for foreclosure/assisted living posts.
# If you still want AI-only posts sometimes, keep these but only apply them conditionally in the prompt builder.
AI_FRAMING_RULES = [
    "Be clear about boundaries: support and education, not advice or guarantees",
    "Name one real constraint (time, uncertainty, capacity, rules, or emotional bandwidth)",
    "End with one grounded question that invites reflection or a next step",
]


class ExpertLensManager:
    """
    Manages expert lens selection, state persistence, and content planning.
    
    This class handles:
    - Rotating through expert lenses on a fixed cycle
    - Tracking which domains/trends have been covered to avoid repetition
    - Creating content plans that guide the text generation process
    - Persisting state to avoid repeating content
    """
    
    def __init__(self, state_path: str = "cache/content_state.json"):
        """
        Initialize the ExpertLensManager.
        
        Args:
            state_path: Path to the JSON file for state persistence
        """
        self.state_path = state_path
        self.logger = logging.getLogger(__name__)
        
        # Ensure cache directory exists (only if state_path has a directory component)
        state_dir = os.path.dirname(self.state_path)
        if state_dir:  # Only create directory if path contains a directory component
            os.makedirs(state_dir, exist_ok=True)
        # If state_path is just a filename (no directory), file will be created in current directory
    
    def load_state(self) -> Dict[str, Any]:
        """
        Load state from persistent storage.
        
        Returns:
            Dictionary containing lens index and history
        """
        if not os.path.exists(self.state_path):
            return {"lens_i": -1, "history": []}
        
        try:
            with open(self.state_path, "r", encoding="utf-8") as f:
                state = json.load(f)
                # Ensure required keys exist
                if "lens_i" not in state:
                    state["lens_i"] = -1
                if "history" not in state:
                    state["history"] = []
                return state
        except (json.JSONDecodeError, IOError) as e:
            self.logger.warning(f"Error loading state from {self.state_path}: {e}. Using default state.")
            return {"lens_i": -1, "history": []}
    
    def save_state(self, state: Dict[str, Any]) -> bool:
        """
        Save state to persistent storage.
        
        Args:
            state: State dictionary to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure cache directory exists (only if state_path has a directory component)
            state_dir = os.path.dirname(self.state_path)
            if state_dir:  # Only create directory if path contains a directory component
                os.makedirs(state_dir, exist_ok=True)
            # If state_path is just a filename (no directory), file will be created in current directory
            with open(self.state_path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
            return True
        except (IOError, OSError) as e:
            self.logger.error(f"Error saving state to {self.state_path}: {e}")
            return False
    
    def pick_plan(
        self,
        trend_candidates: List[Dict[str, Any]],
        platform: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Select an expert lens, pick a trend, and create a content plan.
        
        This method:
        1. Rotates to the next lens in the fixed cycle
        2. Picks the best trend, avoiding recently covered domains
        3. Rotates brand phrases to avoid repetition
        4. Creates a plan that guides content generation
        
        Args:
            trend_candidates: List of trend dictionaries with keys:
                - "trend" or "title": Trend description
                - "domain": Domain/category (e.g., "Healthcare", "Customer Support")
                - "score": Optional relevance score (higher is better)
                - "description": Optional detailed description
                - "hashtags": Optional list of hashtags
            platform: Optional platform name (for platform-specific planning)
            
        Returns:
            Dictionary containing:
                - "lens": Selected expert lens
                - "post_type": Associated post type
                - "trend": Selected trend title
                - "domain": Domain of selected trend
                - "trend_description": Full trend description
                - "hashtags": Trend hashtags
                - "brand_phrase": Selected brand anchoring phrase
                - "signature": Brand signature
                - "workflow_focus": Instruction for workflow analysis
                - "constraint_focus": Instruction for constraint identification
        """
        state = self.load_state()
        history = state.get("history", [])
        
        # 1) Pick next lens (cycle)
        state["lens_i"] = (state.get("lens_i", -1) + 1) % len(LENS_CYCLE)
        lens = LENS_CYCLE[state["lens_i"]]
        post_type = POST_TYPES_BY_LENS.get(lens, ["Analysis"])[0]
        
        self.logger.info(f"Selected lens: {lens} (post type: {post_type})")
        
        # 2) Pick best trend, avoid repeating domain if possible
        # Get recently covered domains (last 2-3 posts)
        recent_domains = {h.get("domain") for h in history[-3:] if h.get("domain")}
        
        # Sort by score (if available), highest first
        # Use score if present (including 0), otherwise fall back to relevance
        sorted_candidates = sorted(
            trend_candidates,
            key=lambda x: x.get("score") if "score" in x else x.get("relevance", 0),
            reverse=True
        )
        
        # Try to pick a trend from a domain not recently covered
        picked = None
        for candidate in sorted_candidates:
            domain = candidate.get("domain") or candidate.get("category", "General")
            if domain not in recent_domains:
                picked = candidate
                break
        
        # If all domains were recently covered, use the highest-scoring trend
        if not picked:
            picked = sorted_candidates[0] if sorted_candidates else {}
        
        trend_title = picked.get("trend") or picked.get("title", "AI Innovation")
        trend_description = picked.get("description") or picked.get("trend", trend_title)
        domain = picked.get("domain") or picked.get("category", "General")
        hashtags = picked.get("hashtags", [])
        
        self.logger.info(f"Selected trend: {trend_title} (domain: {domain})")
        
        # 3) Attach enforced workflow skeleton from domain
        workflow = DOMAIN_WORKFLOW_MAP.get(domain) or DOMAIN_WORKFLOW_MAP.get("General")
        if not workflow:
            self.logger.warning(f"No workflow skeleton for domain '{domain}', using General")
            workflow = DOMAIN_WORKFLOW_MAP["General"]
        
        # HARD ENFORCEMENT: Every post must include these
        required_fields = ["decision", "constraint", "risk_owner"]
        for field in required_fields:
            if not workflow.get(field):
                raise ValueError(f"Missing required workflow field '{field}' for domain '{domain}'")
        
        # 4) Rotate brand phrases
        brand_phrase = BRAND_PHRASES[len(history) % len(BRAND_PHRASES)]
        quiet_anchor = QUIET_BRAND_ANCHORS[len(history) % len(QUIET_BRAND_ANCHORS)]
        
        # 5) Create workflow and constraint focus based on lens
        workflow_focus, constraint_focus = self._get_lens_instructions(lens)
        
        plan = {
            "lens": lens,
            "post_type": post_type,
            "trend": trend_title,
            "trend_description": trend_description,
            "domain": domain,
            "hashtags": hashtags,
            
            # REQUIRED EXPERT ANCHORS (hard enforcement)
            "decision": workflow["decision"],
            "constraint": workflow["constraint"],
            "risk_owner": workflow["risk_owner"],
            "human_roles": workflow.get("human_roles", []),
            
            # BRAND (NON-SALESY)
            "brand_phrase": brand_phrase,
            "quiet_brand_anchor": quiet_anchor,
            "signature": SIGNATURE,
            
            # GENERATOR GUARDRAILS
            "banned_phrases": list(BANNED_HYPE),
            "ai_framing_rules": AI_FRAMING_RULES,
            
            # Lens-specific instructions
            "workflow_focus": workflow_focus,
            "constraint_focus": constraint_focus,
            "platform": platform,
        }
        
        # 5) Persist history
        history.append({
            "date": datetime.utcnow().strftime("%Y-%m-%d"),
            "lens": lens,
            "post_type": post_type,
            "domain": domain,
            "trend": trend_title,
            "platform": platform,
        })
        
        # Keep only last 12 entries (as per sample code)
        state["history"] = history[-12:]
        self.save_state(state)
        
        return plan
    
    def _get_lens_instructions(self, lens: str) -> tuple:
        """
        Get workflow and constraint focus instructions based on the selected lens.
        
        Args:
            lens: Selected expert lens
            
        Returns:
            Tuple of (workflow_focus, constraint_focus) strings
        """
        instructions = {
            "What Everyone Gets Wrong": (
                "Map the common misconception or misunderstanding about this trend. "
                "Identify where people typically go wrong in their thinking.",
                "The real constraint is often misunderstood. Identify what people think "
                "the constraint is vs. what it actually is."
            ),
            "The Real Constraint": (
                "Map the actual workflow or process where this trend is applied. "
                "Identify the real bottlenecks and limitations.",
                "Name the specific constraint that limits this trend's effectiveness. "
                "This is the actual barrier, not the perceived one."
            ),
            "How This Plays Out in Practice": (
                "Map the step-by-step workflow of how this trend is actually implemented. "
                "Show the real-world process from start to finish.",
                "Identify where human decision points occur in the workflow. "
                "These are the moments where judgment is required."
            ),
            "Where This Breaks at Scale": (
                "Map the workflow at small scale, then identify where it fails when scaled up. "
                "Show the transition point where things break.",
                "The constraint that emerges at scale. This is different from small-scale constraints. "
                "Identify the specific bottleneck that appears when volume increases."
            ),
            "The Hidden Tradeoff": (
                "Map the workflow to show where tradeoffs are made. "
                "Identify the decision points where one benefit is gained at the cost of another.",
                "The constraint that forces the tradeoff. This is the limitation that makes "
                "the tradeoff necessary."
            ),
            "How We Evaluate It": (
                "Map the evaluation workflow. Show how decisions are made about whether "
                "this trend is working or not.",
                "The constraint in evaluation. What makes it hard to measure success? "
                "What limits our ability to assess effectiveness?"
            ),
            "What Changes After Adoption": (
                "Map the workflow before and after adoption. Show what changes in the process. "
                "Identify second-order effects.",
                "The new constraint that emerges after adoption. What limitation appears "
                "that didn't exist before?"
            ),
            "The Open Question We're Exploring": (
                "Map the current workflow and identify the unknown areas. "
                "Show where we're still learning and exploring.",
                "The constraint we're trying to understand. What limitation are we "
                "investigating? What question are we trying to answer?"
            ),
        }
        
        return instructions.get(lens, (
            "Map the real-world workflow where this trend is applied.",
            "Identify the key constraint or limitation in this context."
        ))
    
    def get_lens_cycle(self) -> List[str]:
        """
        Get the list of available lenses.
        
        Returns:
            List of lens names
        """
        return LENS_CYCLE.copy()
    
    def get_current_lens_index(self) -> int:
        """
        Get the current lens index in the cycle.
        
        Returns:
            Current lens index (0-based)
        """
        state = self.load_state()
        return state.get("lens_i", -1)
    
    def get_recent_history(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get recent content history.
        
        Args:
            limit: Number of recent entries to return
            
        Returns:
            List of recent history entries
        """
        state = self.load_state()
        history = state.get("history", [])
        return history[-limit:]
    
    def get_domain_workflow(self, domain: str) -> Optional[Dict[str, Any]]:
        """
        Get workflow skeleton for a specific domain.
        
        Args:
            domain: Domain name (e.g., "Real Estate", "Healthcare")
            
        Returns:
            Dictionary containing workflow skeleton, or None if not found
        """
        return DOMAIN_WORKFLOW_MAP.get(domain) or DOMAIN_WORKFLOW_MAP.get("General")
    
    @staticmethod
    def get_available_domains() -> List[str]:
        """
        Get list of available domains with workflow skeletons.
        
        Returns:
            List of domain names
        """
        return [d for d in DOMAIN_WORKFLOW_MAP.keys() if d != "General"]
