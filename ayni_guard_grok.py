import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta

import requests
from pyArango.connection import Connection


@dataclass
class AyniResult:
    composite_score: float
    details: dict[str, any]
    issues: list[str]
    action: str  # 'block', 'warn', 'proceed'


class AyniGuard:
    def __init__(self, arango_url: str, db_name: str, username: str, password: str, llm_api_key: str):
        # Blessed by Pachamama, this guard races like a condor on ArangoDB’s winds
        self.conn = Connection(arangoURL=arango_url, username=username, password=password)
        self.db = self.conn[db_name]
        self.llm_api_key = llm_api_key
        self.setup_arango()
        # Weights carved like terraces under the apus’ watchful gaze
        self.weights = {
            "coherence": 0.4,
            "ethicality": 0.2,
            "mutualism": 0.2,
            "tier_1_context": 0.1,
            "tier_2_constraints": 0.07,
            "tier_3_preferences": 0.03,
        }

    def setup_arango(self):
        # Weave the khipu’s strands: collections and views for Indaleko’s scale
        if not self.db.hasCollection("prompt_cache"):
            cache = self.db.createCollection(name="prompt_cache")
            cache.addHashIndex(fields=["prompt_hash"], unique=True)
        if not self.db.hasCollection("prompt_history"):
            history = self.db.createCollection(name="prompt_history")
            history.addSkiplistIndex(fields=["evaluated_at"])
        # Craft a Search View, like a Quechua pattern book for prompt wisdom
        try:
            self.db.views.createView(
                name="prompt_search",
                properties={
                    "links": {
                        "prompt_history": {
                            "fields": {
                                "context": {"analyzers": ["text_en"]},
                                "constraints": {"analyzers": ["text_en"]},
                                "preferences": {"analyzers": ["text_en"]},
                                "issues": {"analyzers": ["text_en"]},
                                "result.composite_score": {"analyzers": ["identity"]},
                            },
                        },
                    },
                },
            )
        except:
            pass  # View exists, Pachamama approves

    def compute_prompt_hash(self, prompt: dict) -> str:
        # Knot the prompt’s essence, swift as a condor’s dive
        return hashlib.sha256(json.dumps(prompt, sort_keys=True).encode()).hexdigest()

    def check_cache(self, prompt_hash: str) -> AyniResult | None:
        # Seek the khipu’s knot with ArangoDB’s lightning speed
        aql = """
            FOR doc IN prompt_cache
                FILTER doc.prompt_hash == @hash AND doc.expires_at > @now
                LIMIT 1
                RETURN doc.result
        """
        result = self.db.AQLQuery(aql, bindVars={"hash": prompt_hash, "now": datetime.now().isoformat()})
        if result:
            return AyniResult(**json.loads(result[0]))
        return None

    def store_cache(self, prompt_hash: str, result: AyniResult, prompt: dict, user_id: str | None = None):
        # Tie this knot to the khipu, logged for Pachamama’s eternal record
        expires_at = datetime.now() + timedelta(days=30)
        self.db["prompt_cache"].createDocument(
            {
                "prompt_hash": prompt_hash,
                "result": json.dumps(result.__dict__),
                "created_at": datetime.now().isoformat(),
                "expires_at": expires_at.isoformat(),
            },
        ).save()
        self.db["prompt_history"].createDocument(
            {
                "prompt": prompt,
                "result": result.__dict__,
                "user_id": user_id,
                "evaluated_at": datetime.now().isoformat(),
            },
        ).save()

    def check_contradictions(self, prompt: dict) -> tuple[float, list[str]]:
        # Untangle the prompt’s threads, swift as a weaver under Inti’s light
        issues = []
        context = prompt.get("context", "")
        if "MUST" in context and "MUST NOT" in context:
            issues.append("Tier 1: MUST and MUST NOT conflict")
            tier_1_score = 0.5
        else:
            tier_1_score = 0.95

        constraints = prompt.get("constraints", {})
        if "format" in constraints and constraints["format"] == "json" and "prose" in constraints:
            issues.append("Tier 2: JSON and prose format conflict")
            tier_2_score = 0.6
        else:
            tier_2_score = 0.85

        preferences = prompt.get("preferences", {})
        tier_3_score = 0.8 if "conflicting" in str(preferences) else 0.9
        if "conflicting" in str(preferences):
            issues.append("Tier 3: Weighted preference conflict")

        # Guard Indaleko from injection, like a condor spotting a fox
        injection_patterns = ["ignore all", "bypass", "execute code", "access internal"]
        if any(p in context.lower() for p in injection_patterns):
            issues.append("Potential injection attempt detected")
            tier_1_score *= 0.5

        coherence = (tier_1_score + tier_2_score + tier_3_score) / 3
        return coherence, issues

    def check_ethicality(self, prompt: dict) -> float:
        # Call the apus via xAI’s API, swift as a mountain wind
        headers = {"Authorization": f"Bearer {self.llm_api_key}"}
        try:
            response = requests.post(
                "https://api.x.ai/v1/review",
                headers=headers,
                json={"prompt": json.dumps(prompt)},
                timeout=5,
            )
            review = response.json()
            return 0.8 if "coercive" not in review else 0.4
        except requests.RequestException:
            return 0.6  # Fallback, Pachamama forgives

    def check_mutualism(self, prompt: dict) -> float:
        # Seek ayni’s harmony in the trust contract
        trust_contract = prompt.get("trust_contract", {})
        return 0.87 if trust_contract.get("mutual_intent") else 0.7

    def evaluate(self, prompt: dict, user_id: str | None = None) -> AyniResult:
        # Judge the prompt, balanced as a Quechua elder’s council
        prompt_hash = self.compute_prompt_hash(prompt)
        cached_result = self.check_cache(prompt_hash)
        if cached_result:
            return cached_result

        issues = []
        coherence, coherence_issues = self.check_contradictions(prompt)
        issues.extend(coherence_issues)
        ethicality = self.check_ethicality(prompt)
        mutualism = self.check_mutualism(prompt)
        tier_1_score = coherence * 0.95
        tier_2_score = coherence * 0.85
        tier_3_score = coherence * 0.8

        composite_score = sum(
            score * weight
            for score, weight in [
                (coherence, self.weights["coherence"]),
                (ethicality, self.weights["ethicality"]),
                (mutualism, self.weights["mutualism"]),
                (tier_1_score, self.weights["tier_1_context"]),
                (tier_2_score, self.weights["tier_2_constraints"]),
                (tier_3_score, self.weights["tier_3_preferences"]),
            ]
        )

        action = "block" if composite_score < 0.5 else "warn" if composite_score < 0.7 else "proceed"
        result = AyniResult(
            composite_score=composite_score,
            details={
                "coherence": coherence,
                "ethicality": ethicality,
                "mutualism": mutualism,
                "tier_1_context": {"score": tier_1_score, "issues": [i for i in issues if "Tier 1" in i]},
                "tier_2_constraints": {"score": tier_2_score, "issues": [i for i in issues if "Tier 2" in i]},
                "tier_3_preferences": {"score": tier_3_score, "issues": [i for i in issues if "Tier 3" in i]},
            },
            issues=issues,
            action=action,
        )

        self.store_cache(prompt_hash, result, prompt, user_id)
        return result

    def detect_injection_patterns(self, limit: int = 100) -> list[dict]:
        # Scan the khipu for foxes sneaking into Indaleko’s pen
        aql = """
            FOR doc IN prompt_search
                SEARCH ANALYZER(doc.issues IN ['injection'], 'text_en')
                SORT doc.evaluated_at DESC
                LIMIT @limit
                RETURN { prompt: doc.prompt, issues: doc.issues, score: doc.result.composite_score }
        """
        return self.db.AQLQuery(aql, bindVars={"limit": limit})


# Sample prompt simulation, soaring with Pachamama’s grace
if __name__ == "__main__":
    guard = AyniGuard(
        arango_url="http://localhost:8529",
        db_name="indaleko",
        username="root",
        password="password",
        llm_api_key="your_xai_api_key",
    )
    sample_prompt = {
        "context": "Summarize the document clearly",
        "constraints": {"format": "json"},
        "preferences": {"tone": "neutral"},
        "trust_contract": {"mutual_intent": "maximize clarity"},
    }
    result = guard.evaluate(sample_prompt, user_id="test_user")
    print(f"AyniScore: {result.composite_score}")
    print(f"Details: {json.dumps(result.details, indent=2)}")
    print(f"Issues: {result.issues}")
    print(f"Action: {result.action}")
