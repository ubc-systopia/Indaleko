"""
Tool for inventorying and analyzing current prompt usage in the codebase.

This script scans the codebase for all LLM prompt usage, categorizes them,
and prepares a migration plan for converting them to the new prompt management system.
"""

import argparse
import json
import logging
import re
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
class PromptLocation:
    """Information about a prompt's location in code."""

    file_path: str
    line_number: int
    function_name: str | None = None
    class_name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class PromptUsage:
    """Information about a single prompt's usage."""

    content: str
    location: PromptLocation
    provider: str  # openai, anthropic, etc.
    estimated_tokens: int
    is_template: bool = False
    has_variables: bool = False
    migration_complexity: str = "unknown"  # easy, medium, hard

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result = asdict(self)
        result["location"] = self.location.to_dict()
        return result


@dataclass
class PromptInventory:
    """Inventory of all prompt usage in the codebase."""

    prompts: list[PromptUsage] = field(default_factory=list)
    total_token_estimate: int = 0
    scan_timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def add_prompt(self, prompt: PromptUsage) -> None:
        """Add a prompt to the inventory."""
        self.prompts.append(prompt)
        self.total_token_estimate += prompt.estimated_tokens

    def by_provider(self) -> dict[str, list[PromptUsage]]:
        """Group prompts by provider."""
        result: dict[str, list[PromptUsage]] = {}
        for prompt in self.prompts:
            if prompt.provider not in result:
                result[prompt.provider] = []
            result[prompt.provider].append(prompt)
        return result

    def by_complexity(self) -> dict[str, list[PromptUsage]]:
        """Group prompts by migration complexity."""
        result: dict[str, list[PromptUsage]] = {}
        for prompt in self.prompts:
            if prompt.migration_complexity not in result:
                result[prompt.migration_complexity] = []
            result[prompt.migration_complexity].append(prompt)
        return result

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "prompts": [p.to_dict() for p in self.prompts],
            "total_token_estimate": self.total_token_estimate,
            "scan_timestamp": self.scan_timestamp,
            "prompt_count": len(self.prompts),
            "provider_distribution": {provider: len(prompts) for provider, prompts in self.by_provider().items()},
            "complexity_distribution": {
                complexity: len(prompts) for complexity, prompts in self.by_complexity().items()
            },
        }

    def save_json(self, file_path: str) -> None:
        """Save inventory to JSON file."""
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)
        logger.info(f"Inventory saved to {file_path}")

    def save_report(self, file_path: str) -> None:
        """Save a human-readable report."""
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("# Prompt Usage Inventory Report\n\n")
            f.write(f"Generated: {self.scan_timestamp}\n\n")

            f.write("## Summary\n\n")
            f.write(f"- Total prompts found: {len(self.prompts)}\n")
            f.write(f"- Estimated total tokens: {self.total_token_estimate:,}\n\n")

            # Provider distribution
            f.write("## Provider Distribution\n\n")
            for provider, prompts in self.by_provider().items():
                f.write(f"- {provider}: {len(prompts)} prompts\n")
            f.write("\n")

            # Complexity distribution
            f.write("## Migration Complexity\n\n")
            for complexity, prompts in self.by_complexity().items():
                f.write(f"- {complexity}: {len(prompts)} prompts\n")
            f.write("\n")

            # List all prompts
            f.write("## Detailed Prompt Inventory\n\n")
            for i, prompt in enumerate(self.prompts, 1):
                f.write(f"### Prompt {i}\n\n")
                f.write(f"- **File**: {prompt.location.file_path}\n")
                f.write(f"- **Line**: {prompt.location.line_number}\n")
                if prompt.location.function_name:
                    f.write(f"- **Function**: {prompt.location.function_name}\n")
                if prompt.location.class_name:
                    f.write(f"- **Class**: {prompt.location.class_name}\n")
                f.write(f"- **Provider**: {prompt.provider}\n")
                f.write(f"- **Template**: {'Yes' if prompt.is_template else 'No'}\n")
                f.write(f"- **Variables**: {'Yes' if prompt.has_variables else 'No'}\n")
                f.write(f"- **Tokens**: ~{prompt.estimated_tokens:,}\n")
                f.write(f"- **Migration Complexity**: {prompt.migration_complexity}\n")
                f.write(f"- **Content Preview**:\n\n```\n{prompt.content[:300]}")
                if len(prompt.content) > 300:
                    f.write("...\n```\n\n")
                else:
                    f.write("\n```\n\n")

        logger.info(f"Report saved to {file_path}")


class PromptScanner:
    """Scanner for finding prompts in code files."""

    # Common patterns for prompts in different LLM providers
    PATTERNS = {
        # OpenAI patterns
        "openai": [
            r'openai\.Completion\.create\s*\(\s*[^)]*prompt\s*=\s*[\'"](.+?)[\'"]',
            r"openai\.ChatCompletion\.create\s*\(\s*[^)]*messages\s*=\s*(\[.+?\])",
            r"client\.chat\.completions\.create\s*\(\s*[^)]*messages\s*=\s*(\[.+?\])",
            r'openai_connector\.get_completion\s*\(\s*[\'"](.+?)[\'"]',
        ],
        # Anthropic patterns
        "anthropic": [
            r'anthropic\.Completion\.create\s*\(\s*[^)]*prompt\s*=\s*[\'"](.+?)[\'"]',
            r'anthropic_connector\.get_completion\s*\(\s*[\'"](.+?)[\'"]',
            r'client\.messages\.create\s*\(\s*[^)]*prompt\s*=\s*[\'"](.+?)[\'"]',
        ],
        # Gemma patterns
        "gemma": [
            r'gemma_connector\.get_completion\s*\(\s*[\'"](.+?)[\'"]',
        ],
        # General patterns
        "general": [
            r'llm\.generate_response\s*\(\s*[\'"](.+?)[\'"]',
            r'get_llm_response\s*\(\s*[\'"](.+?)[\'"]',
            r'SYSTEM_PROMPT\s*=\s*[\'"](.+?)[\'"]',
            r'USER_PROMPT\s*=\s*[\'"](.+?)[\'"]',
            r'prompt\s*=\s*[f]?[\'"](.+?)[\'"]',
        ],
    }

    def __init__(self, root_dir: str):
        """Initialize scanner with root directory."""
        self.root_dir = Path(root_dir)
        if not self.root_dir.exists():
            raise ValueError(f"Directory {root_dir} does not exist")

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for a text string."""
        # Simple approximation: 4 chars = 1 token
        return len(text) // 4

    def determine_complexity(self, prompt: str, is_template: bool, has_variables: bool) -> str:
        """Determine migration complexity based on prompt characteristics."""
        if len(prompt) < 100 and not is_template and not has_variables:
            return "easy"
        elif len(prompt) < 500 and not is_template and has_variables:
            return "medium"
        elif is_template or len(prompt) > 500:
            return "hard"
        return "medium"

    def is_python_file(self, path: Path) -> bool:
        """Check if a file is a Python file."""
        return path.suffix == ".py"

    def scan_file(self, file_path: Path) -> list[PromptUsage]:
        """Scan a single file for prompt usage."""
        if not self.is_python_file(file_path):
            return []

        prompts: list[PromptUsage] = []

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            lines = content.split("\n")

            # Extract current class and function for context
            current_class = None
            current_function = None

            for i, line in enumerate(lines):
                # Track class and function definitions for context
                class_match = re.match(r"\s*class\s+(\w+)", line)
                if class_match:
                    current_class = class_match.group(1)

                func_match = re.match(r"\s*def\s+(\w+)", line)
                if func_match:
                    current_function = func_match.group(1)

                # Check for prompts
                for provider, patterns in self.PATTERNS.items():
                    for pattern in patterns:
                        if re.search(pattern, line):
                            # Get full multiline string if needed
                            prompt_text = line
                            if "'''" in line or '"""' in line:
                                # Find multiline string
                                start_idx = i
                                end_idx = i
                                while end_idx < len(lines) - 1:
                                    if (
                                        "'''" in lines[end_idx] and "'''" in lines[start_idx] and end_idx != start_idx
                                    ) or (
                                        '"""' in lines[end_idx] and '"""' in lines[start_idx] and end_idx != start_idx
                                    ):
                                        break
                                    end_idx += 1

                                prompt_text = "\n".join(lines[start_idx : end_idx + 1])

                            # Extract the actual prompt content
                            prompt_match = re.search(pattern, prompt_text)
                            if prompt_match:
                                prompt_content = prompt_match.group(1)

                                # Determine if it's a template with variables
                                is_template = "{" in prompt_content and "}" in prompt_content
                                has_variables = 'f"' in prompt_text or "f'" in prompt_text

                                # Only use provider from pattern if it's not "general"
                                actual_provider = provider if provider != "general" else "unknown"

                                prompt_location = PromptLocation(
                                    file_path=str(file_path.relative_to(self.root_dir)),
                                    line_number=i + 1,
                                    function_name=current_function,
                                    class_name=current_class,
                                )

                                estimated_tokens = self.estimate_tokens(prompt_content)
                                complexity = self.determine_complexity(prompt_content, is_template, has_variables)

                                prompt_usage = PromptUsage(
                                    content=prompt_content,
                                    location=prompt_location,
                                    provider=actual_provider,
                                    estimated_tokens=estimated_tokens,
                                    is_template=is_template,
                                    has_variables=has_variables,
                                    migration_complexity=complexity,
                                )

                                prompts.append(prompt_usage)

            return prompts

        except Exception as e:
            logger.error(f"Error scanning file {file_path}: {e}")
            return []

    def scan_directory(self) -> PromptInventory:
        """Scan all Python files in directory for prompt usage."""
        inventory = PromptInventory()

        for file_path in self.root_dir.glob("**/*.py"):
            # Skip tests and venv
            if (
                "venv" in str(file_path)
                or ".venv" in str(file_path)
                or "test_" in file_path.name
                or "/tests/" in str(file_path)
            ):
                continue

            logger.debug(f"Scanning {file_path}")
            prompts = self.scan_file(file_path)

            for prompt in prompts:
                inventory.add_prompt(prompt)

        return inventory


def main() -> None:
    """Run the prompt inventory tool."""
    parser = argparse.ArgumentParser(description="Inventory prompt usage in codebase")
    parser.add_argument(
        "--root-dir",
        type=str,
        default=".",
        help="Root directory to scan (default: current directory)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./results",
        help="Directory to save results (default: ./results)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info(f"Scanning directory: {args.root_dir}")
    scanner = PromptScanner(args.root_dir)
    inventory = scanner.scan_directory()

    logger.info(f"Found {len(inventory.prompts)} prompts")
    logger.info(f"Estimated total tokens: {inventory.total_token_estimate:,}")

    # Create output directory if it doesn't exist
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save inventory as JSON and report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    inventory.save_json(output_dir / f"prompt_inventory_{timestamp}.json")
    inventory.save_report(output_dir / f"prompt_inventory_report_{timestamp}.md")


if __name__ == "__main__":
    main()
