"""
Migration planner for converting existing prompts to the prompt management system.

This script analyzes the prompt inventory and creates a migration plan with recommendations
for converting each prompt to use the new prompt management system.
"""

import argparse
import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class MigrationStep:
    """A single step in the migration plan."""

    file_path: str
    line_number: int
    prompt_id: str
    current_code: str
    proposed_code: str
    priority: str  # high, medium, low
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class MigrationPlan:
    """Complete migration plan for converting prompts."""

    steps: list[MigrationStep] = field(default_factory=list)
    inventory_path: str | None = None
    generated_timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    template_definitions: dict[str, dict[str, Any]] = field(default_factory=dict)

    def add_step(self, step: MigrationStep) -> None:
        """Add a migration step to the plan."""
        self.steps.append(step)

    def by_priority(self) -> dict[str, list[MigrationStep]]:
        """Group steps by priority."""
        result: dict[str, list[MigrationStep]] = {}
        for step in self.steps:
            if step.priority not in result:
                result[step.priority] = []
            result[step.priority].append(step)
        return result

    def by_file(self) -> dict[str, list[MigrationStep]]:
        """Group steps by file path."""
        result: dict[str, list[MigrationStep]] = {}
        for step in self.steps:
            if step.file_path not in result:
                result[step.file_path] = []
            result[step.file_path].append(step)
        return result

    def save_json(self, file_path: str) -> None:
        """Save plan to JSON file."""
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "steps": [step.to_dict() for step in self.steps],
                    "inventory_path": self.inventory_path,
                    "generated_timestamp": self.generated_timestamp,
                    "template_definitions": self.template_definitions,
                    "step_count": len(self.steps),
                    "priority_distribution": {priority: len(steps) for priority, steps in self.by_priority().items()},
                },
                f,
                indent=2,
            )
        logger.info(f"Migration plan saved to {file_path}")

    def save_report(self, file_path: str) -> None:
        """Save a human-readable report."""
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("# Prompt Migration Plan\n\n")
            f.write(f"Generated: {self.generated_timestamp}\n\n")

            f.write("## Summary\n\n")
            f.write(f"- Total migration steps: {len(self.steps)}\n")

            # Priority distribution
            f.write("## Priority Distribution\n\n")
            for priority, steps in self.by_priority().items():
                f.write(f"- {priority.capitalize()}: {len(steps)} steps\n")
            f.write("\n")

            # Template definitions
            f.write("## New Template Definitions\n\n")
            for template_id, definition in self.template_definitions.items():
                f.write(f"### {template_id}\n\n")
                f.write("```python\n")
                f.write(f'"{template_id}": {{\n')
                f.write(f'    "description": "{definition["description"]}",\n')
                f.write(f'    "content": """\n{definition["content"]}\n"""\n')
                f.write("},\n")
                f.write("```\n\n")

            # List all steps by file
            f.write("## Migration Steps By File\n\n")
            for file_path, steps in self.by_file().items():
                f.write(f"### {file_path}\n\n")
                for i, step in enumerate(sorted(steps, key=lambda s: s.line_number), 1):
                    f.write(f"#### Step {i} (Line {step.line_number})\n\n")
                    f.write(f"**Priority**: {step.priority}\n\n")
                    f.write(f"**Rationale**: {step.rationale}\n\n")
                    f.write(f"**Current Code**:\n\n```python\n{step.current_code}\n```\n\n")
                    f.write(f"**Proposed Code**:\n\n```python\n{step.proposed_code}\n```\n\n")

            # Migration steps by priority
            f.write("## Migration Steps By Priority\n\n")

            for priority in ["high", "medium", "low"]:
                steps = self.by_priority().get(priority, [])
                if not steps:
                    continue

                f.write(f"### {priority.capitalize()} Priority Steps\n\n")
                for i, step in enumerate(steps, 1):
                    f.write(f"#### {i}. {step.file_path}:{step.line_number}\n\n")
                    f.write(f"**Rationale**: {step.rationale}\n\n")
                    f.write(f"**Current Code**:\n\n```python\n{step.current_code}\n```\n\n")
                    f.write(f"**Proposed Code**:\n\n```python\n{step.proposed_code}\n```\n\n")

        logger.info(f"Migration report saved to {file_path}")


class MigrationPlanner:
    """Tool for planning prompt migrations."""

    def __init__(
        self,
        inventory_path: str,
        guardian_import: str = "from query.utils.prompt_management.guardian.llm_guardian import LLMGuardian",
    ):
        """Initialize with path to prompt inventory file."""
        self.inventory_path = Path(inventory_path)
        if not self.inventory_path.exists():
            raise ValueError(f"Inventory file {inventory_path} does not exist")

        self.guardian_import = guardian_import
        self.template_counter = 0
        self.existing_templates: set[str] = set()
        self.template_definitions: dict[str, dict[str, Any]] = {}

    def load_inventory(self) -> dict[str, Any]:
        """Load prompt inventory from file."""
        with open(self.inventory_path, encoding="utf-8") as f:
            return json.load(f)

    def generate_template_id(self, prompt_content: str, provider: str) -> str:
        """Generate a template ID based on content."""
        self.template_counter += 1

        # Generate a descriptive name based on content
        words = prompt_content.split()[:3]
        word_part = "_".join(words)[:20].lower()
        word_part = "".join(c if c.isalnum() else "_" for c in word_part)

        return f"{provider}_{word_part}_{self.template_counter}"

    def create_template_definition(self, prompt_content: str, provider: str, complexity: str) -> str:
        """Create a template definition and return the template ID."""
        template_id = self.generate_template_id(prompt_content, provider)

        # Extract a short description
        description = prompt_content.split(".")[0][:50] + "..."

        self.template_definitions[template_id] = {
            "description": description,
            "content": prompt_content,
            "complexity": complexity,
            "provider": provider,
        }

        return template_id

    def generate_migration_code(self, prompt_content: str, provider: str, has_variables: bool) -> str:
        """Generate migration code for a prompt."""
        if provider == "unknown":
            provider = "openai"  # Default to OpenAI for unknown providers

        template_id = self.create_template_definition(prompt_content, provider, "medium" if has_variables else "low")

        if has_variables:
            # Code for prompts with variables
            return f"""# Initialize LLMGuardian once at module level
from query.utils.prompt_management.guardian.llm_guardian import LLMGuardian
from query.utils.prompt_management.data_models import PromptVariable

# Create guardian instance (typically in __init__ or at module level)
guardian = LLMGuardian()

# Replace direct prompt with template-based completion
variables = [
    PromptVariable(name="var1", value=var1),
    # Add other variables as needed
]

completion, metadata = guardian.get_completion_from_template(
    template_id="{template_id}",
    variables=variables,
    provider="{provider}"
)"""
        else:
            # Code for simple prompts without variables
            return f"""# Initialize LLMGuardian once at module level
from query.utils.prompt_management.guardian.llm_guardian import LLMGuardian

# Create guardian instance (typically in __init__ or at module level)
guardian = LLMGuardian()

# Replace direct prompt with template-based completion
completion, metadata = guardian.get_completion_from_template(
    template_id="{template_id}",
    variables=[],  # No variables needed
    provider="{provider}"
)"""

    def determine_priority(self, tokens: int, provider: str, complexity: str) -> str:
        """Determine migration priority based on characteristics."""
        # High priority for high token count or complex prompts
        if tokens > 1000 or complexity == "hard":
            return "high"
        # Medium priority for medium complexity or moderate token count
        elif tokens > 500 or complexity == "medium":
            return "medium"
        # Low priority for the rest
        else:
            return "low"

    def create_migration_plan(self) -> MigrationPlan:
        """Create a migration plan from inventory."""
        inventory = self.load_inventory()
        plan = MigrationPlan(inventory_path=str(self.inventory_path))

        for prompt in inventory["prompts"]:
            # Extract relevant info
            content = prompt["content"]
            file_path = prompt["location"]["file_path"]
            line_number = prompt["location"]["line_number"]
            provider = prompt["provider"]
            has_variables = prompt["has_variables"]
            complexity = prompt["migration_complexity"]
            tokens = prompt["estimated_tokens"]

            # Generate unique ID for prompt
            prompt_id = f"{file_path.replace('/', '_')}_{line_number}"

            # Current code placeholder (would need full file access for actual code)
            current_code = f'# Original prompt usage\nprompt = "{content[:50]}..."\n# ... LLM call with this prompt'

            # Generate new code
            proposed_code = self.generate_migration_code(content, provider, has_variables)

            # Determine priority
            priority = self.determine_priority(tokens, provider, complexity)

            # Create rationale
            rationale = f"Migrate {tokens} token prompt to template-based approach. "
            if complexity == "hard":
                rationale += "This prompt has complex structure or excessive length. "
            if has_variables:
                rationale += "Variables need to be extracted and properly structured. "
            rationale += f"Using the {provider} provider."

            # Create step
            step = MigrationStep(
                file_path=file_path,
                line_number=line_number,
                prompt_id=prompt_id,
                current_code=current_code,
                proposed_code=proposed_code,
                priority=priority,
                rationale=rationale,
            )

            plan.add_step(step)

        # Add template definitions to plan
        plan.template_definitions = self.template_definitions

        return plan


def main() -> None:
    """Run the migration planner tool."""
    parser = argparse.ArgumentParser(description="Create migration plan for prompts")
    parser.add_argument(
        "--inventory",
        type=str,
        required=True,
        help="Path to prompt inventory JSON file",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./results",
        help="Directory to save results (default: ./results)",
    )

    args = parser.parse_args()

    logger.info(f"Reading inventory from: {args.inventory}")
    planner = MigrationPlanner(args.inventory)
    plan = planner.create_migration_plan()

    logger.info(f"Created migration plan with {len(plan.steps)} steps")

    # Create output directory if it doesn't exist
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save plan as JSON and report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    plan.save_json(output_dir / f"migration_plan_{timestamp}.json")
    plan.save_report(output_dir / f"migration_plan_report_{timestamp}.md")


if __name__ == "__main__":
    main()
