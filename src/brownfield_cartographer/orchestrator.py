from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .agents.hydrologist import HydrologistAgent
from .agents.surveyor import SurveyorAgent
from .graph.knowledge_graph import KnowledgeGraph


MODULE_GRAPH_FILENAME = "module_graph.json"
LINEAGE_GRAPH_FILENAME = "lineage_graph.json"


@dataclass
class OrchestratorConfig:
    repo_path: Path
    output_dir: Path
    output_format: str = "json"


class Orchestrator:
    """
    Coordinates agents to build module and lineage graphs.
    """

    def __init__(self, repo_path: Path, output_dir: Path, output_format: str = "json") -> None:
        self.config = OrchestratorConfig(
            repo_path=repo_path,
            output_dir=output_dir,
            output_format=output_format,
        )
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.kg = KnowledgeGraph()

    @property
    def repo_path(self) -> Path:
        return self.config.repo_path

    @property
    def output_dir(self) -> Path:
        return self.config.output_dir

    def run_surveyor(self) -> None:
        surveyor = SurveyorAgent()
        surveyor.run(self.repo_path, self.kg)
        module_graph_path = self.output_dir / MODULE_GRAPH_FILENAME
        self.kg.save_module_graph(module_graph_path)

    def run_hydrologist(self) -> None:
        hydrologist = HydrologistAgent()
        hydrologist.run(self.repo_path, self.kg)
        lineage_graph_path = self.output_dir / LINEAGE_GRAPH_FILENAME
        self.kg.save_lineage_graph(lineage_graph_path)

    def run_all(self) -> None:
        """
        Run all currently implemented agents sequentially.
        """
        self.run_surveyor()
        self.run_hydrologist()

