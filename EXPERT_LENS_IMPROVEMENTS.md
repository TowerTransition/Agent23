# Expert Lens System - Improvements Based on Sample Code

## Key Improvements Integrated

Your sample code had several excellent improvements that have been integrated:

### 1. **Domain Workflow Skeletons** ✅
**What it does:** Enforces specific decision points, constraints, and risk owners for each domain.

**Implementation:**
- Added `DOMAIN_WORKFLOW_MAP` with skeletons for:
  - Real Estate
  - Logistics
  - Finance & Trading
  - Healthcare
  - General (fallback)
- Each skeleton includes:
  - `decision`: The key decision point
  - `constraint`: The actual limitation
  - `risk_owner`: Who bears the risk
  - `human_roles`: Key human roles in the workflow

**Hard Enforcement:** The system now **requires** these fields in every post. If missing, it raises an error.

### 2. **Consistent Brand Footer** ✅
**What it does:** Every post ends with the same brand footer for consistency.

**Implementation:**
- All posts end with: "Real-world systems. Real clarity.\n— Elevare by Amaziah"
- This footer appears in all training examples
- Optional quiet brand anchors can be added within content (e.g., "This is the kind of workflow mapping we document at Elevare") but the footer is always present

### 3. **Banned Hype Phrases** ✅
**What it does:** Prevents generic marketing language.

**Implementation:**
- Added `BANNED_HYPE` set with phrases like:
  - "unlock the power"
  - "revolutionize"
  - "game-changer"
  - "are you ready"
  - "cutting-edge"
  - "seamless"
  - "transform"
- Included in prompt as explicit "NEVER USE" instructions

### 4. **AI Framing Rules** ✅
**What it does:** Ensures AI is presented correctly (as support, not replacement).

**Implementation:**
- Added `AI_FRAMING_RULES`:
  - "AI is decision support, sequencing, or signal — never replacement"
  - AI support always includes qualification: "without [giving advice/stepping into legal guidance/directing trades/etc.]"
  - AI is always framed as "AI supports/helps by [action]" not "AI does [action]"
- Included in prompt instructions

### 5. **Reinforcement Statement** ✅
**What it does:** Every post ends with a short, actionable reinforcement statement before the footer.

**Implementation:**
- Posts end with a reinforcement statement (e.g., "Coordination reduces avoidable errors", "Structure conserves capacity")
- Followed by the brand footer: "Real-world systems. Real clarity.\n— Elevare by Amaziah"
- Reinforcement is always a short, declarative statement that reinforces the main point

### 6. **Hard Enforcement** ✅
**What it does:** Validates that required fields are present before generating content.

**Implementation:**
- Checks for `decision`, `constraint`, and `risk_owner` in workflow skeleton
- Raises `ValueError` if any are missing
- Ensures content plan always includes these elements

## Actual Post Output Formats (From Training Data)

The bot was trained on two post formats:

### Format 1: Structured Format
```
CONTEXT: [Situational context]
PROBLEM: [The core problem]
AI_SUPPORT: [How AI supports without replacing]
REINFORCEMENT: [Key takeaway]
FOOTER: Real-world systems. Real clarity.
— Elevare by Amaziah
HASHTAGS: #[tag1] #[tag2] #[tag3] #[tag4]
```

### Format 2: Narrative Format
```
[Main insight paragraph]

[Supporting explanation paragraph]

AI [helps/supports] by [specific action]—[qualification without advice].

[Reinforcement statement]

Real-world systems. Real clarity.
— Elevare by Amaziah

#[tag1] #[tag2] #[tag3] #[tag4]
```

## Content Plan Structure (Input to Generator)

The content plan that generates these posts includes:

```python
{
    "lens": "The Real Constraint",
    "post_type": "Constraint-First",
    "trend": "AI-assisted imaging triage",
    "domain": "Healthcare",
    
    # REQUIRED EXPERT ANCHORS (hard enforcement)
    "decision": "Which cases get reviewed first and which escalate now?",
    "constraint": "Backlog, limited clinician time, alert fatigue, liability boundaries.",
    "risk_owner": "Clinician and hospital system (missed or delayed escalation).",
    "human_roles": ["Clinician", "Radiologist", "Care coordinator"],
    
    # BRAND (NON-SALESY) - Always ends with:
    "footer": "Real-world systems. Real clarity.\n— Elevare by Amaziah",
    
    # GENERATOR GUARDRAILS
    "banned_phrases": ["unlock the power", "revolutionize", ...],
    "ai_framing_rules": [
        "AI is decision support, sequencing, or signal — never replacement",
        "Name one failure mode (handoff, drift, alert fatigue, incentives)"
    ],
    
    # Post structure elements that map to training formats
    "context": "...",  # Maps to CONTEXT: or opening paragraph
    "problem": "...",  # Maps to PROBLEM: or problem statement
    "ai_support": "...",  # Maps to AI_SUPPORT: or AI paragraph
    "reinforcement": "...",  # Maps to REINFORCEMENT: or reinforcement statement
    "hashtags": ["#tag1", "#tag2", "#tag3", "#tag4"]  # Exactly 4 hashtags
}
```

## Updated Prompt Structure

The prompt now explicitly includes:

1. **REQUIRED ELEMENTS section** - Decision, constraint, risk owner
2. **BANNED PHRASES** - Never use these
3. **AI FRAMING RULES** - How to present AI (always with qualification)
4. **CONTENT STRUCTURE** - Step-by-step with hard requirements matching training formats
5. **REINFORCEMENT & FOOTER** - Must end with reinforcement statement and brand footer
6. **HASHTAGS** - Exactly 4 hashtags required

## Example Outputs (From Training Data)

**Format 1 Example (Structured):**
```
CONTEXT: Foreclosure involves many moving parts.
PROBLEM: When information isn't coordinated, small details fall through the cracks and stress compounds.
AI_SUPPORT: AI supports clarity by organizing information—helping people see how pieces relate without stepping into legal guidance.
REINFORCEMENT: Coordination reduces avoidable errors.
FOOTER: Real-world systems. Real clarity.
— Elevare by Amaziah
HASHTAGS: #RealWorldAI #HousingStability #ProcessClarity #SystemDesign
```

**Format 2 Example (Narrative):**
```
Structure reduces decision fatigue.

Willpower depletes throughout the day. Structure removes the need to decide the same things repeatedly.

AI helps by automating routine decisions—preserving mental energy for choices that truly matter.

Structure conserves capacity.

Real-world systems. Real clarity.
— Elevare by Amaziah

#RealWorldAI #HousingStability #DecisionStructure #SystemDesign
```

**Key Training Patterns:**
- Always ends with "Real-world systems. Real clarity.\n— Elevare by Amaziah"
- Exactly 4 hashtags
- AI support always includes qualification ("without [advice/guidance/directing]")
- Reinforcement is a short, actionable statement
- No hype phrases or marketing language

## Benefits

1. **Cohesion**: Domain-specific workflows ensure consistent depth across industries
2. **Authority**: Hard requirements force expert-level analysis
3. **Differentiation**: Banned phrases prevent generic marketing speak
4. **Engagement**: Operational questions invite discussion
5. **Brand Building**: Quiet anchors demonstrate expertise without pitching

## Adding New Domains

To add a new domain workflow skeleton:

```python
DOMAIN_WORKFLOW_MAP["Your Domain"] = {
    "decision": "What is the key decision point?",
    "constraint": "What is the actual limitation?",
    "risk_owner": "Who bears the risk?",
    "human_roles": ["Role 1", "Role 2", "Role 3"],
}
```

The system will automatically use it when that domain is selected.

## Testing

The system now:
- ✅ Enforces decision/constraint/risk_owner in every post
- ✅ Uses consistent brand footer: "Real-world systems. Real clarity.\n— Elevare by Amaziah"
- ✅ Bans hype phrases
- ✅ Requires reinforcement statements
- ✅ Frames AI correctly with qualifications
- ✅ Uses domain-specific workflows
- ✅ Generates posts matching training data formats (structured or narrative)
- ✅ Always includes exactly 4 hashtags

All improvements from your sample code have been integrated!
