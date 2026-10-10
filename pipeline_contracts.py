from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any

def _now():
    return datetime.now(timezone.utc).isoformat()

@dataclass
class PipelineArtifact:
    name: str
    path: str
    kind: str
    checksum_sha256: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass
class PipelineError:
    code: str
    message: str
    retryable: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass
class PipelineStageResult:
    stage: str
    status: str
    run_id: str
    short_id: str
    started_at: str
    finished_at: str
    artifacts: list[PipelineArtifact] = field(default_factory=list)
    errors: list[PipelineError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)

@dataclass
class PipelineContext:
    run_id: str
    short_id: str
    created_at: str = field(default_factory=_now)
    stages: list[PipelineStageResult] = field(default_factory=list)

    def add(self, result: PipelineStageResult):
        self.stages.append(result)

    def to_dict(self):
        return asdict(self)


@dataclass
class PipelineManifest:
    """Canonical immutable summary of one pipeline execution.

    Stage-specific manifests may keep their existing schemas; this object is
    the cross-stage index that ties them together without making any stage own
    another stage's internals.
    """
    schema_version: str
    run_id: str
    short_id: str
    generated_at: str = field(default_factory=_now)
    status: str = "RUNNING"
    artifacts: list[PipelineArtifact] = field(default_factory=list)
    stages: list[PipelineStageResult] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_artifact(self, artifact: PipelineArtifact):
        self.artifacts.append(artifact)

    def add_stage(self, result: PipelineStageResult):
        self.stages.append(result)

    def to_dict(self):
        return asdict(self)
