# ui/incident_report_page.py

from __future__ import annotations


import json
import random
from datetime import datetime
from pathlib import Path
import re
from models.incident_model import IncidentModel, ResponsiblePartyFlags, IncidentStatusFlags


from PySide6.QtCore import Qt, QTimer, QAbstractTableModel, QModelIndex, QSize
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QTableView,
    QTabWidget,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

SEVERITY_OPTIONS = ["Minor", "Moderate", "Major", "Critical"]

RESPONSIBLE_PARTY_LABELS = {
    "MooseGremlin": "Moose Gremlin",
    "Lag": "Lag",
    "UserError": "User Error",
    "ESO": "ESO",
    "Unknown": "Unknown",
    "UnderInvestigation": "Under Investigation",
}

INCIDENT_STATUS_LABELS = {
    "Filed": "Filed",
    "PendingReview": "Pending Review",
    "RequiresFollowUp": "Requires Follow-Up",
    "Archived": "Archived",
}

def _build_incident_page(self) -> QWidget:
        self.incident_tab = QWidget()
        layout = QVBoxLayout(self.incident_tab)

        self.incident_report_number_label = QLabel("Unfiled")
        
        report_row = QHBoxLayout()
        report_row.addWidget(QLabel("Report Number:"))
        report_row.addWidget(self.incident_report_number_label)
        report_row.addStretch(1)
        layout.addLayout(report_row)

        grid = QHBoxLayout()
        left = QVBoxLayout()
        right = QVBoxLayout()

        left.addWidget(self._make_section("Location", self.inc_location))
        left.addWidget(self._make_section("Department", self.inc_department))
        left.addWidget(self._make_section("Severity", self.inc_severity))
        left.addWidget(self._make_section("Summary", self.inc_summary))
        left.addWidget(self._make_section("Suspected Cause", self.inc_suspected_cause))
        left.addWidget(self._make_section("Engineering Assessment", self.inc_engineering_assessment))
        left.addWidget(self._make_section("Coffee Recommendation", self.inc_coffee_recommendation))
        left.addWidget(self._make_incident_responsible_panel())

        right.addWidget(self._make_section("Observations", self.inc_observations))
        right.addWidget(self._make_section("Actions Taken", self.inc_actions_taken))
        right.addWidget(self._make_section("Recommendations", self.inc_recommendations))
        right.addWidget(self._make_section("Outstanding Questions", self.inc_outstanding_questions))
        right.addWidget(self._make_incident_status_panel())

        grid.addLayout(left)
        grid.addLayout(right)
        layout.addLayout(grid)

        actions = QHBoxLayout()
        self.incident_clear_btn = QPushButton("Clear")
        self.incident_save_btn = QPushButton("Save to OBS")
        self.incident_file_btn = QPushButton("Save to Archive")
        self.incident_load_btn = QPushButton("Load Incident")

        self.incident_clear_btn.clicked.connect(self.clear_incident)
        self.incident_save_btn.clicked.connect(self.save_incident)
        self.incident_load_btn.clicked.connect(self.load_incident)
        self.incident_file_btn.clicked.connect(self.file_incident_report)

        actions.addWidget(self.incident_clear_btn)
        actions.addWidget(self.incident_save_btn)
        actions.addWidget(self.incident_file_btn)
        actions.addWidget(self.incident_load_btn)
        layout.addLayout(actions)

        return self.incident_tab

def _make_incident_responsible_panel(self) -> QGroupBox:
        box = QGroupBox("Responsible Party")
        layout = QVBoxLayout(box)

        self.inc_party_checkboxes: dict[str, QCheckBox] = {}
        for field_name, label in RESPONSIBLE_PARTY_LABELS.items():
            checkbox = QCheckBox(label)
            self.inc_party_checkboxes[field_name] = checkbox
            layout.addWidget(checkbox)
        return box

def _make_incident_status_panel(self) -> QGroupBox:
        box = QGroupBox("Status")
        layout = QVBoxLayout(box)

        self.inc_status_checkboxes: dict[str, QCheckBox] = {}
        for field_name, label in INCIDENT_STATUS_LABELS.items():
            checkbox = QCheckBox(label)
            self.inc_status_checkboxes[field_name] = checkbox
            layout.addWidget(checkbox)
        return box

@property
def inc_location(self) -> QLineEdit:
        if not hasattr(self, "_inc_location"):
            self._inc_location = self._build_field("Location")
        return self._inc_location

@property
def inc_department(self) -> QLineEdit:
        if not hasattr(self, "_inc_department"):
            self._inc_department = self._build_field("Department")
        return self._inc_department

@property
def inc_severity(self) -> QComboBox:
        if not hasattr(self, "_inc_severity"):
            self._inc_severity = QComboBox()
            for option in SEVERITY_OPTIONS:
                self._inc_severity.addItem(option)
        return self._inc_severity

@property
def inc_summary(self) -> QTextEdit:
        if not hasattr(self, "_inc_summary"):
            self._inc_summary = QTextEdit()
            self._inc_summary.setPlaceholderText("Summary")
        return self._inc_summary

@property
def inc_suspected_cause(self) -> QLineEdit:
        if not hasattr(self, "_inc_suspected_cause"):
            self._inc_suspected_cause = self._build_field("Suspected Cause")
        return self._inc_suspected_cause

@property
def inc_engineering_assessment(self) -> QTextEdit:
        if not hasattr(self, "_inc_engineering_assessment"):
            self._inc_engineering_assessment = QTextEdit()
            self._inc_engineering_assessment.setPlaceholderText("Engineering Assessment")
        return self._inc_engineering_assessment

@property
def inc_coffee_recommendation(self) -> QLineEdit:
        if not hasattr(self, "_inc_coffee_recommendation"):
            self._inc_coffee_recommendation = self._build_field("Coffee Recommendation")
        return self._inc_coffee_recommendation

@property
def inc_observations(self) -> QTextEdit:
        if not hasattr(self, "_inc_observations"):
            self._inc_observations = QTextEdit()
            self._inc_observations.setPlaceholderText("Observations")
        return self._inc_observations

@property
def inc_actions_taken(self) -> QTextEdit:
        if not hasattr(self, "_inc_actions_taken"):
            self._inc_actions_taken = QTextEdit()
            self._inc_actions_taken.setPlaceholderText("Actions Taken")
        return self._inc_actions_taken

@property
def inc_recommendations(self) -> QTextEdit:
        if not hasattr(self, "_inc_recommendations"):
            self._inc_recommendations = QTextEdit()
            self._inc_recommendations.setPlaceholderText("Recommendations")
        return self._inc_recommendations

@property
def inc_outstanding_questions(self) -> QTextEdit:
        if not hasattr(self, "_inc_outstanding_questions"):
            self._inc_outstanding_questions = QTextEdit()
            self._inc_outstanding_questions.setPlaceholderText("Outstanding Questions")
        return self._inc_outstanding_questions

    
def _collect_incident_model(self) -> IncidentModel:
        party = ResponsiblePartyFlags(
            **{name: cb.isChecked() for name, cb in self.inc_party_checkboxes.items()}
        )
        status = IncidentStatusFlags(
            **{name: cb.isChecked() for name, cb in self.inc_status_checkboxes.items()}
        )
        report_number = self.incident_report_number_label.text()
        if report_number == "Unfiled":
            report_number = ""

        return IncidentModel(
            ReportNumber=report_number,
            Location=self.inc_location.text(),
            Department=self.inc_department.text(),
            Severity=self.inc_severity.currentText(),
            Summary=self.inc_summary.toPlainText(),
            SuspectedCause=self.inc_suspected_cause.text(),
            EngineeringAssessment=self.inc_engineering_assessment.toPlainText(),
            CoffeeRecommendation=self.inc_coffee_recommendation.text(),
            Observations=self.inc_observations.toPlainText(),
            ActionsTaken=self.inc_actions_taken.toPlainText(),
            Recommendations=self.inc_recommendations.toPlainText(),
            OutstandingQuestions=self.inc_outstanding_questions.toPlainText(),
            ResponsibleParty=party,
            Status=status,
        )

def _apply_incident_model(self, model: IncidentModel) -> None:
        self.incident_report_number_label.setText(model.ReportNumber or "Unfiled")
        self.inc_location.setText(model.Location)
        self.inc_department.setText(model.Department)
        if model.Severity in SEVERITY_OPTIONS:
            self.inc_severity.setCurrentText(model.Severity)
        elif self.inc_severity.count() > 0:
            self.inc_severity.setCurrentIndex(0)
        self.inc_summary.setPlainText(model.Summary)
        self.inc_suspected_cause.setText(model.SuspectedCause)
        self.inc_engineering_assessment.setPlainText(model.EngineeringAssessment)
        self.inc_coffee_recommendation.setText(model.CoffeeRecommendation)
        self.inc_observations.setPlainText(model.Observations)
        self.inc_actions_taken.setPlainText(model.ActionsTaken)
        self.inc_recommendations.setPlainText(model.Recommendations)
        self.inc_outstanding_questions.setPlainText(model.OutstandingQuestions)

        for field_name, checkbox in self.inc_party_checkboxes.items():
            checkbox.setChecked(getattr(model.ResponsibleParty, field_name))
        for field_name, checkbox in self.inc_status_checkboxes.items():
            checkbox.setChecked(getattr(model.Status, field_name))

def clear_incident(self) -> None:
        self._apply_incident_model(IncidentModel())
        self.status_label.setText("Incident Report cleared")

def load_incident(self) -> None:
        self.status_label.setText("Loading incident...")
        try:
            model = self.incident_json_service.load()
            self._apply_incident_model(model)
            self.status_label.setText("Incident loaded")
        except Exception as exc:  # pragma: no cover - UI path guard
            self.status_label.setText(f"Incident load failed: {exc}")

def save_incident(self) -> None:
        self.status_label.setText("Saving incident...")
        try:
            model = self._collect_incident_model()
            self.incident_json_service.save(model)
            self.status_label.setText("Incident saved")
        except Exception as exc:  # pragma: no cover - UI path guard
            self.status_label.setText(f"Incident save failed: {exc}")

def file_incident_report(self) -> None:
            self.status_label.setText("Filing incident report...")
            try:
                model = self._collect_incident_model()
    
                def build_lines(report_id: str, number: int) -> list[str]:
                    party_active = [
                        RESPONSIBLE_PARTY_LABELS[name]
                        for name, checked in model.ResponsibleParty.__dict__.items()
                        if checked
                    ]
                    status_active = [
                        INCIDENT_STATUS_LABELS[name]
                        for name, checked in model.Status.__dict__.items()
                        if checked
                    ]
                    return [
                        f"# Incident Report {report_id}",
                        "",
                        f"- Location: {model.Location or 'Unknown'}",
                        f"- Department: {model.Department or 'Unknown'}",
                        f"- Severity: {model.Severity or 'Unknown'}",
                        f"- Summary: {model.Summary or 'None recorded'}",
                        f"- Suspected Cause: {model.SuspectedCause or 'Unknown'}",
                        f"- Engineering Assessment: {model.EngineeringAssessment or 'None recorded'}",
                        f"- Coffee Recommendation: {model.CoffeeRecommendation or 'None'}",
                        f"- Observations: {model.Observations or 'None recorded'}",
                        f"- Actions Taken: {model.ActionsTaken or 'None recorded'}",
                        f"- Recommendations: {model.Recommendations or 'None recorded'}",
                        f"- Outstanding Questions: {model.OutstandingQuestions or 'None'}",
                        f"- Responsible Party: {', '.join(party_active) or 'None marked'}",
                        f"- Status: {', '.join(status_active) or 'None marked'}",
                        f"- Filed: {datetime.now().isoformat(timespec='seconds')}",
                        "",
                    ]
    
                report_id, report_path = self.archive_service.file_form("IR", build_lines)
    
                model.ReportNumber = report_id
                model.Status.Filed = True
                self._apply_incident_model(model)
                self.incident_json_service.save(model)
    
                self.status_label.setText(f"Incident filed: {report_id} ({report_path.name})")
            except Exception as exc:  # pragma: no cover - UI path guard
                self.status_label.setText(f"Incident report failed: {exc}")