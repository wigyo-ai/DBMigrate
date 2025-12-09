"""
H2O.ai GPTe API Client Wrapper
Handles communication with H2O GPTe using the official Python SDK.
"""

import logging
import time
from typing import Dict, List, Optional
import json
import urllib3

# Suppress SSL warnings for internal instances
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    from h2ogpte import H2OGPTE
except ImportError:
    raise ImportError(
        "h2ogpte SDK not installed. Please install it with: pip install h2ogpte"
    )

logger = logging.getLogger(__name__)


class GPTeClient:
    """Wrapper for H2O.ai GPTe SDK interactions."""

    def __init__(self, api_url: str, api_key: str, model_id: str = "gpt-4-turbo-2024-04-09"):
        """
        Initialize GPTe client.

        Args:
            api_url: H2O GPTe API URL
            api_key: API authentication key
            model_id: Model identifier (default: gpt-4-turbo-2024-04-09)
        """
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self.model_id = model_id
        self.conversation_history = []
        self.max_retries = 3
        self.retry_delay = 2  # seconds

        # Initialize H2OGPTE client
        try:
            self.client = H2OGPTE(
                address=self.api_url,
                api_key=self.api_key,
                verify=False  # Disable SSL verification for internal instances
            )
            logger.info(f"H2OGPTE client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize H2OGPTE client: {e}")
            raise ConnectionError(f"Failed to initialize H2OGPTE client: {str(e)}")

    def create_session(self) -> str:
        """
        Create a new chat session (handled internally by SDK).

        Returns:
            Session ID (managed by SDK)
        """
        # The H2OGPTE SDK manages sessions internally
        logger.info("Using H2OGPTE SDK session management")
        return "sdk_managed"

    def send_message(self, message: str, context: Optional[Dict] = None) -> Dict[str, any]:
        """
        Send a message to the GPTe API and get response.

        Args:
            message: The message/prompt to send
            context: Optional context dictionary to include

        Returns:
            Dictionary containing the response
        """
        # Build the full prompt with context if provided
        full_prompt = message
        if context:
            context_str = json.dumps(context, indent=2)
            full_prompt = f"{message}\n\nContext:\n```json\n{context_str}\n```"

        for attempt in range(self.max_retries):
            try:
                # Use the H2OGPTE SDK to send the question
                response = self.client.answer_question(
                    question=full_prompt,
                    llm=self.model_id,
                    timeout=120
                )

                # Extract response text from SDK response
                response_text = response.content if hasattr(response, 'content') else str(response)

                # Store in conversation history
                self.conversation_history.append({
                    'role': 'user',
                    'content': message
                })
                self.conversation_history.append({
                    'role': 'assistant',
                    'content': response_text
                })

                return {
                    'success': True,
                    'response': response_text,
                    'raw_data': response
                }

            except Exception as e:
                logger.error(f"API request failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                return {
                    'success': False,
                    'error': str(e),
                    'response': ''
                }

        return {
            'success': False,
            'error': 'Max retries exceeded',
            'response': ''
        }

    def send_agent_prompt(self, agent_name: str, role: str, tasks: List[str],
                          context: Optional[Dict] = None) -> Dict[str, any]:
        """
        Send a structured prompt for an agent.

        Args:
            agent_name: Name of the agent
            role: Role description for the agent
            tasks: List of specific tasks the agent should perform
            context: Optional context data

        Returns:
            Dictionary containing agent response
        """
        # Build structured prompt
        prompt = f"""You are the {agent_name} agent for a PostgreSQL database migration system.

Role: {role}

Tasks to perform:
"""
        for i, task in enumerate(tasks, 1):
            prompt += f"{i}. {task}\n"

        prompt += """
Please analyze the provided context and complete all tasks.
Return your findings in a clear, structured format using JSON where appropriate.
"""

        return self.send_message(prompt, context)

    def parse_json_response(self, response: str) -> Optional[Dict]:
        """
        Attempt to parse JSON from agent response.

        Args:
            response: Agent response string

        Returns:
            Parsed JSON dictionary or None if parsing fails
        """
        try:
            # Try direct JSON parse
            return json.loads(response)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            if '```json' in response:
                start = response.find('```json') + 7
                end = response.find('```', start)
                if end != -1:
                    try:
                        return json.loads(response[start:end].strip())
                    except json.JSONDecodeError:
                        pass

            # Try to extract JSON from text
            start = response.find('{')
            end = response.rfind('}')
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(response[start:end + 1])
                except json.JSONDecodeError:
                    pass

            return None

    def reset_conversation(self):
        """Reset conversation history."""
        self.conversation_history = []
        logger.info("Conversation history reset")

    def get_conversation_history(self) -> List[Dict]:
        """
        Get the current conversation history.

        Returns:
            List of conversation messages
        """
        return self.conversation_history.copy()

    def get_available_models(self) -> List[str]:
        """
        Get list of available LLM models.

        Returns:
            List of model names
        """
        try:
            models = self.client.get_llms()
            logger.info(f"Available models: {models}")
            return models
        except Exception as e:
            logger.warning(f"Could not retrieve available models: {e}")
            return [self.model_id]


class AgentOrchestrator:
    """Orchestrates multiple GPTe agents for database migration workflow."""

    def __init__(self, gpte_client: GPTeClient):
        """
        Initialize agent orchestrator.

        Args:
            gpte_client: Configured GPTe client instance
        """
        self.client = gpte_client
        self.workflow_state = {
            'discovery': {'status': 'pending', 'result': None},
            'validation': {'status': 'pending', 'result': None},
            'generation': {'status': 'pending', 'result': None},
            'execution': {'status': 'pending', 'result': None}
        }

    def get_workflow_state(self) -> Dict:
        """Get current workflow state."""
        return self.workflow_state.copy()

    def update_agent_status(self, agent_name: str, status: str, result: any = None):
        """
        Update status of an agent in the workflow.

        Args:
            agent_name: Name of the agent
            status: Status (pending, running, completed, failed)
            result: Optional result data
        """
        if agent_name in self.workflow_state:
            self.workflow_state[agent_name]['status'] = status
            if result is not None:
                self.workflow_state[agent_name]['result'] = result

    def reset_workflow(self):
        """Reset workflow state to initial state."""
        for agent in self.workflow_state:
            self.workflow_state[agent] = {'status': 'pending', 'result': None}
        self.client.reset_conversation()
