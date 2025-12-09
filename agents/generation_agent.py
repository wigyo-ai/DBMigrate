"""
Generation Agent
Analyzes discovery and validation results to generate migration plan and recommendations.
"""

import logging
from typing import Dict, Optional
import json
from gpte_client import GPTeClient

logger = logging.getLogger(__name__)


class GenerationAgent:
    """Agent responsible for generating migration plan and approval recommendation."""

    def __init__(self, gpte_client: GPTeClient):
        """
        Initialize Generation Agent.

        Args:
            gpte_client: Configured GPTe client for AI assistance
        """
        self.client = gpte_client
        self.migration_plan = {}
        self.recommendation = None  # Will be 'APPROVE' or 'DENY'
        self.human_decision = None  # Will store user's approval/denial

    def run(self, discovery_data: Dict, validation_data: Dict) -> Dict[str, any]:
        """
        Run generation process to create migration plan and recommendation.

        Args:
            discovery_data: Results from Discovery Agent
            validation_data: Results from Validation Agent

        Returns:
            Dictionary containing migration plan and recommendation
        """
        logger.info("Generation Agent starting...")

        result = {
            'status': 'running',
            'migration_plan': {},
            'risk_assessment': {},
            'recommendation': None,
            'awaiting_approval': False
        }

        try:
            # Generate migration plan using GPTe
            logger.info("Generating migration plan...")
            plan = self._generate_migration_plan(discovery_data, validation_data)
            result['migration_plan'] = plan

            # Perform risk assessment
            logger.info("Performing risk assessment...")
            risks = self._assess_risks(discovery_data, validation_data, plan)
            result['risk_assessment'] = risks

            # Generate recommendation
            logger.info("Generating recommendation...")
            recommendation = self._generate_recommendation(
                discovery_data, validation_data, plan, risks
            )
            result['recommendation'] = recommendation
            self.recommendation = recommendation.get('decision', 'DENY')

            # Store for later reference
            self.migration_plan = result

            result['status'] = 'completed'
            result['awaiting_approval'] = True

            logger.info(f"Generation Agent completed with recommendation: {self.recommendation}")

        except Exception as e:
            logger.error(f"Generation failed: {e}")
            result['status'] = 'failed'
            result['error'] = str(e)

        return result

    def _generate_migration_plan(self, discovery_data: Dict, validation_data: Dict) -> Dict[str, any]:
        """
        Generate detailed migration plan using GPTe.

        Args:
            discovery_data: Discovery results
            validation_data: Validation results

        Returns:
            Dictionary containing migration plan
        """
        logger.info("Generating migration plan with GPTe...")

        role = """Create a detailed, actionable migration plan for moving data from a source
        PostgreSQL database to a destination PostgreSQL database. Base your plan on the
        discovery and validation results provided."""

        tasks = [
            "Analyze the database compatibility between source and destination",
            "Determine the optimal migration approach (table-by-table, schema-based, etc.)",
            "Estimate the total migration time based on data sizes",
            "Identify the order in which tables should be migrated (considering dependencies)",
            "Specify batch sizes and performance optimization strategies",
            "Define checkpoint and rollback procedures",
            "List pre-migration preparation steps",
            "List post-migration verification steps",
            "Provide a timeline with phases and milestones"
        ]

        context = {
            'discovery': discovery_data,
            'validation': validation_data
        }

        response = self.client.send_agent_prompt(
            agent_name="Generation Agent (Plan Creation)",
            role=role,
            tasks=tasks,
            context=context
        )

        if not response['success']:
            logger.error("Failed to generate migration plan")
            return {
                'error': response.get('error', 'Unknown error'),
                'plan': 'Failed to generate plan'
            }

        # Try to parse structured response
        parsed = self.client.parse_json_response(response['response'])
        if parsed:
            return parsed

        # Return raw response if parsing fails
        return {
            'plan_text': response['response'],
            'raw': True
        }

    def _assess_risks(self, discovery_data: Dict, validation_data: Dict, plan: Dict) -> Dict[str, any]:
        """
        Assess migration risks using GPTe.

        Args:
            discovery_data: Discovery results
            validation_data: Validation results
            plan: Migration plan

        Returns:
            Dictionary containing risk assessment
        """
        logger.info("Assessing risks with GPTe...")

        role = """Perform a comprehensive risk assessment for the proposed database migration.
        Identify potential issues, data loss scenarios, downtime risks, and compatibility problems."""

        tasks = [
            "Identify HIGH, MEDIUM, and LOW risk factors",
            "Assess potential for data loss or corruption",
            "Evaluate downtime requirements and impact",
            "Identify version compatibility issues",
            "Assess storage and performance requirements on destination",
            "Identify schema or data type incompatibilities",
            "Evaluate rollback complexity and feasibility",
            "Provide risk mitigation strategies for each identified risk"
        ]

        context = {
            'discovery': discovery_data,
            'validation': validation_data,
            'migration_plan': plan
        }

        response = self.client.send_agent_prompt(
            agent_name="Generation Agent (Risk Assessment)",
            role=role,
            tasks=tasks,
            context=context
        )

        if not response['success']:
            logger.error("Failed to assess risks")
            return {
                'error': response.get('error', 'Unknown error'),
                'risks': 'Failed to assess risks'
            }

        # Try to parse structured response
        parsed = self.client.parse_json_response(response['response'])
        if parsed:
            return parsed

        # Return raw response if parsing fails
        return {
            'risk_text': response['response'],
            'raw': True
        }

    def _generate_recommendation(self, discovery_data: Dict, validation_data: Dict,
                                  plan: Dict, risks: Dict) -> Dict[str, any]:
        """
        Generate final APPROVE or DENY recommendation using GPTe.

        Args:
            discovery_data: Discovery results
            validation_data: Validation results
            plan: Migration plan
            risks: Risk assessment

        Returns:
            Dictionary containing recommendation with decision and reasoning
        """
        logger.info("Generating recommendation with GPTe...")

        role = """Based on all available information about the database migration (discovery,
        validation, migration plan, and risk assessment), provide a final recommendation of
        either APPROVE or DENY for proceeding with the full migration."""

        tasks = [
            "Review all discovery findings for compatibility",
            "Review validation results for data integrity",
            "Assess whether the migration plan is sound and complete",
            "Evaluate if risks are acceptable or can be mitigated",
            "Make a clear decision: APPROVE or DENY",
            "Provide detailed reasoning for your decision",
            "If APPROVE: list conditions or prerequisites that must be met",
            "If DENY: list specific issues that must be resolved before reconsidering",
            "Provide confidence level (HIGH, MEDIUM, LOW) in your recommendation"
        ]

        # Add explicit instruction in context
        context = {
            'discovery': discovery_data,
            'validation': validation_data,
            'migration_plan': plan,
            'risk_assessment': risks,
            'instructions': """Your response MUST include a clear decision field with value 'APPROVE' or 'DENY'.
            Structure your response as JSON with at minimum these fields:
            {
              "decision": "APPROVE" or "DENY",
              "confidence": "HIGH/MEDIUM/LOW",
              "reasoning": "detailed explanation",
              "conditions": ["list of conditions if APPROVE"],
              "blockers": ["list of blockers if DENY"]
            }"""
        }

        response = self.client.send_agent_prompt(
            agent_name="Generation Agent (Recommendation)",
            role=role,
            tasks=tasks,
            context=context
        )

        if not response['success']:
            logger.error("Failed to generate recommendation")
            return {
                'decision': 'DENY',
                'confidence': 'LOW',
                'reasoning': 'Failed to generate recommendation due to API error',
                'error': response.get('error', 'Unknown error')
            }

        # Try to parse structured response
        parsed = self.client.parse_json_response(response['response'])
        if parsed and 'decision' in parsed:
            # Normalize decision to uppercase
            parsed['decision'] = parsed['decision'].upper()
            if parsed['decision'] not in ['APPROVE', 'DENY']:
                parsed['decision'] = 'DENY'
                parsed['reasoning'] = (parsed.get('reasoning', '') +
                                      " [Decision normalized to DENY due to invalid response]")
            return parsed

        # Try to extract decision from text if JSON parsing fails
        response_text = response['response'].upper()
        if 'APPROVE' in response_text and 'DENY' not in response_text:
            decision = 'APPROVE'
        else:
            decision = 'DENY'

        return {
            'decision': decision,
            'confidence': 'MEDIUM',
            'reasoning': response['response'],
            'raw': True,
            'note': 'Decision extracted from unstructured response'
        }

    def set_human_decision(self, approved: bool, reason: str = "") -> Dict[str, any]:
        """
        Record human approval or denial decision.

        Args:
            approved: True if approved, False if denied
            reason: Optional reason for the decision

        Returns:
            Dictionary containing decision status
        """
        self.human_decision = {
            'approved': approved,
            'reason': reason,
            'timestamp': None  # Could add timestamp here
        }

        logger.info(f"Human decision recorded: {'APPROVED' if approved else 'DENIED'}")

        return {
            'recorded': True,
            'decision': 'APPROVED' if approved else 'DENIED',
            'can_proceed': approved
        }

    def can_proceed_to_execution(self) -> bool:
        """
        Check if migration can proceed to execution phase.

        Returns:
            True if human approval received, False otherwise
        """
        return (self.human_decision is not None and
                self.human_decision.get('approved', False))

    def get_summary(self) -> Dict[str, any]:
        """
        Get a summary of generation findings and recommendation.

        Returns:
            Dictionary containing generation summary
        """
        if not self.migration_plan:
            return {'error': 'No migration plan available'}

        return {
            'plan_generated': bool(self.migration_plan.get('migration_plan')),
            'risk_assessed': bool(self.migration_plan.get('risk_assessment')),
            'ai_recommendation': self.recommendation,
            'human_decision': (
                'APPROVED' if self.human_decision and self.human_decision.get('approved')
                else 'DENIED' if self.human_decision
                else 'PENDING'
            ),
            'can_proceed': self.can_proceed_to_execution()
        }
