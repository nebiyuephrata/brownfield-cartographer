from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional

from .agents.hydrologist import HydrologistAgent
from .agents.semanticist import SemanticistAgent
from .agents.surveyor import SurveyorAgent
from .graph.knowledge_graph import KnowledgeGraph


logger = logging.getLogger(__name__)

MODULE_GRAPH_FILENAME = "module_graph.json"
LINEAGE_GRAPH_FILENAME = "lineage_graph.json"


@dataclass
class OrchestratorConfig:
    repo_path: Path
    output_dir: Path
    output_format: str = "json"
    run_surveyor: bool = True
    run_hydrologist: bool = True
    enable_semanticist: bool = True
    ignore_globs: List[str] = field(default_factory=list)
    log_level: str = "INFO"


class Orchestrator:
    """
    Coordinates agents to build module and lineage graphs.
    """

    def __init__(
        self,
        repo_path: Path,
        output_dir: Path,
        output_format: str = "json",
        run_surveyor: bool = True,
        run_hydrologist: bool = True,
        enable_semanticist: bool = True,
        ignore_globs: Optional[Iterable[str]] = None,
        log_level: str = "INFO",
    ) -> None:
        self.config = OrchestratorConfig(
            repo_path=repo_path,
            output_dir=output_dir,
            output_format=output_format,
            run_surveyor=run_surveyor,
            run_hydrologist=run_hydrologist,
            enable_semanticist=enable_semanticist,
            ignore_globs=list(ignore_globs) if ignore_globs is not None else [],
            log_level=log_level,
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
        if not self.config.run_surveyor:
            return
        logger.info("Running Surveyor (module graph)...")
        surveyor = SurveyorAgent(ignore_globs=self.config.ignore_globs)
        surveyor.run(self.repo_path, self.kg)
        module_graph_path = self.output_dir / MODULE_GRAPH_FILENAME
        self.kg.save_module_graph(module_graph_path)
        logger.info("Module graph written to %s", module_graph_path)

    def run_hydrologist(self) -> None:
        if not self.config.run_hydrologist:
            return
        logger.info("Running Hydrologist (lineage graph)...")
        hydrologist = HydrologistAgent()
        hydrologist.run(self.repo_path, self.kg)
        lineage_graph_path = self.output_dir / LINEAGE_GRAPH_FILENAME
        self.kg.save_lineage_graph(lineage_graph_path)
        logger.info("Lineage graph written to %s", lineage_graph_path)

    def run_semanticist(self) -> None:
        if not self.config.enable_semanticist:
            return
        logger.info("Running Semanticist (summaries)...")
        semanticist = SemanticistAgent()
        semanticist.run(self.kg)
        module_graph_path = self.output_dir / MODULE_GRAPH_FILENAME
        lineage_graph_path = self.output_dir / LINEAGE_GRAPH_FILENAME
        self.kg.save_module_graph(module_graph_path)
        self.kg.save_lineage_graph(lineage_graph_path)

    def run_all(self) -> None:
        """
        Run Surveyor then Hydrologist then Semanticist in sequence with no manual
        intervention. Serialization writes module_graph.json and lineage_graph.json
        to the configured output directory; per-file errors are isolated by the agents.
        """
        self.run_surveyor()
        self.run_hydrologist()
        self.run_semanticist()

