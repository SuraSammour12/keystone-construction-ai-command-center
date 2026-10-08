"""
Pydantic schemas used with llm.with_structured_output().
Every LLM call that returns structured data uses one of these.
"""
from typing import Literal
from pydantic import BaseModel, Field


class OrchestratorDecision(BaseModel):
    """LLM router output. Task type + extracted entities."""
    task_type: Literal["report", "email", "transfer", "status", "unknown"]
    project_name: str = Field(default="", description="Project name if mentioned")
    email_recipient: str = Field(default="", description="Recipient if email task")
    transfer_from_project: str = Field(default="", description="Source project for transfer")
    transfer_to_project: str = Field(default="", description="Destination project for transfer")
    transfer_amount: float = Field(default=0.0, ge=0.0)


class AnalysisEvaluation(BaseModel):
    """Rubric for budget/schedule/risk analyses. Total is 0-10."""
    data_usage: int = Field(ge=0, le=2)
    root_cause: int = Field(ge=0, le=2)
    specificity: int = Field(ge=0, le=2)
    completeness: int = Field(ge=0, le=2)
    professionalism: int = Field(ge=0, le=2)
    feedback: str = Field(description="2-3 sentences on what to improve")

    @property
    def total(self) -> int:
        return (self.data_usage + self.root_cause + self.specificity
                + self.completeness + self.professionalism)


class ReportEvaluation(BaseModel):
    """Rubric for the executive report. Total is 0-10."""
    executive_summary: int = Field(ge=0, le=2)
    data_accuracy: int = Field(ge=0, le=2)
    structure: int = Field(ge=0, le=2)
    recommendations: int = Field(ge=0, le=2)
    brevity: int = Field(ge=0, le=2)
    feedback: str

    @property
    def total(self) -> int:
        return (self.executive_summary + self.data_accuracy + self.structure
                + self.recommendations + self.brevity)


class EmailEvaluation(BaseModel):
    """Rubric for drafted emails. Total is 0-10."""
    subject_line: int = Field(ge=0, le=2)
    tone: int = Field(ge=0, le=2)
    clarity: int = Field(ge=0, le=2)
    action_items: int = Field(ge=0, le=2)
    purpose_match: int = Field(ge=0, le=2)
    feedback: str

    @property
    def total(self) -> int:
        return (self.subject_line + self.tone + self.clarity
                + self.action_items + self.purpose_match)


class EmailSensitivity(BaseModel):
    """LLM classification of email sensitivity."""
    sensitivity: Literal["LOW", "MEDIUM", "HIGH"]
    reason: str = Field(description="One sentence explaining the classification")