import json
import os
from typing import Dict, List, Optional, Any
from pathlib import Path
from pydantic import BaseModel
from models.llms import llm_call


class Insight(BaseModel):
    key_learnings: List[str]
    improvement_areas: List[str]
    success_factors: List[str]


class MemoryEntry(BaseModel):
    task: str
    success: bool
    trajectory: List[Dict[str, Any]]
    url: str
    insights: Insight


class Memory:
    def __init__(self, memory_file: str = ".data/memory.json"):
        self.memory_file = memory_file
        self._ensure_memory_file()
        self.memory = self._load_memory()

    def _ensure_memory_file(self):
        """Ensure the memory file and directory exist."""
        Path(self.memory_file).parent.mkdir(parents=True, exist_ok=True)
        if not os.path.exists(self.memory_file):
            self._save_memory(
                {
                    "episodic": [],
                    "semantic": {},  # URL -> summary of site patterns and common issues
                    "procedural": {},  # URL -> summary of successful approaches
                }
            )

    def _load_memory(self) -> Dict:
        """Load memory from JSON file."""
        try:
            with open(self.memory_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {"episodic": [], "semantic": {}, "procedural": {}}

    def _save_memory(self, memory: Optional[Dict] = None):
        """Save memory to JSON file."""
        if memory is None:
            memory = self.memory
        with open(self.memory_file, "w") as f:
            json.dump(memory, f, indent=2)

    def _generate_site_summary(self, url: str, episodes: List[MemoryEntry]) -> str:
        """Generate a human-readable summary of site patterns and common issues."""
        if not episodes:
            return "No experience with this site yet."

        prompt = f"""Analyze the following episodes for the website {url} and provide a concise summary of:
1. Common patterns and behaviors observed
2. Typical issues and how to avoid them
3. Best practices for interacting with this site

Episodes:
{json.dumps([ep.dict() for ep in episodes], indent=2)}

Provide a clear, concise summary that would be helpful for future interactions with this site."""

        return llm_call(prompt=prompt, model="openai/gpt-4.1-mini").strip()

    def _generate_procedural_summary(
        self, url: str, successful_episodes: List[MemoryEntry]
    ) -> str:
        """Generate a human-readable summary of successful approaches."""
        if not successful_episodes:
            return "No successful approaches recorded yet."

        prompt = f"""Analyze the following successful episodes for the website {url} and provide a concise summary of:
1. Most effective approaches and strategies
2. Key steps that led to success
3. Tips for efficiently completing tasks on this site

Successful Episodes:
{json.dumps([ep.dict() for ep in successful_episodes], indent=2)}

Provide a clear, concise summary that would be helpful for future tasks on this site."""

        return llm_call(prompt=prompt, model="openai/gpt-4.1-mini").strip()

    def _generate_insights(self, task: str, result: str, success: bool) -> Insight:
        """Generate structured insights using LLM."""
        prompt = f"""Analyze the following task execution and provide key insights.
Task: {task}
Result: {result}
Success: {success}

Provide insights about what was learned, what could be improved, and what factors contributed to success or failure."""

        return llm_call(
            prompt=prompt, response_format=Insight, model="openai/gpt-4.1-mini"
        )

    def add_episode(
        self,
        task: str,
        success: bool,
        trajectory: List[Dict[str, Any]],
        url: str,
        insights: Insight,
    ):
        """Add a new episode to episodic memory and update semantic/procedural summaries."""
        entry = MemoryEntry(
            task=task,
            success=success,
            trajectory=trajectory,
            url=url,
            insights=insights,
        )

        self.memory["episodic"].append(entry.dict())

        url_episodes = [
            MemoryEntry(**ep) for ep in self.memory["episodic"] if ep["url"] == url
        ]

        self.memory["semantic"][url] = self._generate_site_summary(url, url_episodes)

        successful_episodes = [ep for ep in url_episodes if ep.success]
        self.memory["procedural"][url] = self._generate_procedural_summary(
            url, successful_episodes
        )

        self._save_memory()

    def get_site_summary(self, url: str) -> str:
        """Get the semantic summary for a specific site."""
        return self.memory["semantic"].get(url, "No experience with this site yet.")

    def get_procedural_summary(self, url: str) -> str:
        """Get the procedural summary for a specific site."""
        return self.memory["procedural"].get(
            url, "No successful approaches recorded yet."
        )

    def get_recent_episodes(self, url: str, limit: int = 5) -> List[Dict]:
        """Get the most recent episodes for a specific site."""
        episodes = [ep for ep in self.memory["episodic"] if ep["url"] == url]
        return sorted(episodes, key=lambda x: x.get("timestamp", ""), reverse=True)[
            :limit
        ]
