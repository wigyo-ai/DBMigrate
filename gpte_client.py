"""
H2O.ai GPTe API Client Wrapper
Handles communication with H2O GPTe for agent orchestration.
"""

import requests
import logging
import time
from typing import Dict, List, Optional
import json

logger = logging.getLogger(__name__)


class GPTeClient:
    """Wrapper for H2O.ai GPTe API interactions."""

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
        self.session_id = None
        self.conversation_history = []
        self.max_retries = 3
        self.retry_delay = 2  # seconds

    def _get_headers(self) -> Dict[str, str]:
        """Get API request headers."""
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

    def create_session(self) -> str:
        """
        Create a new chat session.

        Returns:
            Session ID
        """
        try:
            endpoint = f"{self.api_url}/v1/sessions"
            response = requests.post(
                endpoint,
                headers=self._get_headers(),
                json={
                    'model': self.model_id,
                    'system_prompt': 'You are an expert database migration assistant.'
                },
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            self.session_id = data.get('session_id') or data.get('id')
            logger.info(f"Created GPTe session: {self.session_id}")
            return self.session_id
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to create session: {e}")
            raise ConnectionError(f"Failed to create GPTe session: {str(e)}")

    def send_message(self, message: str, context: Optional[Dict] = None) -> Dict[str, any]:
        """
        Send a message to the GPTe API and get response.

        Args:
            message: The message/prompt to send
            context: Optional context dictionary to include

        Returns:
            Dictionary containing the response
        """
        if not self.session_id:
            self.create_session()

        # Build the full prompt with context if provided
        full_prompt = message
        if context:
            context_str = json.dumps(context, indent=2)
            full_prompt = f"{message}\n\nContext:\n```json\n{context_str}\n```"

        for attempt in range(self.max_retries):
            try:
                endpoint = f"{self.api_url}/v1/sessions/{self.session_id}/messages"
                payload = {
                    'message': full_prompt,
                    'model': self.model_id
                }

                response = requests.post(
                    endpoint,
                    headers=self._get_headers(),
                    json=payload,
                    timeout=120  # Longer timeout for complex queries
                )
                response.raise_for_status()
                data = response.json()

                # Extract response text
                response_text = self._extract_response_text(data)

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
                    'raw_data': data
                }

            except requests.exceptions.Timeout:
                logger.warning(f"Request timeout (attempt {attempt + 1}/{self.max_retries})")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                return {
                    'success': False,
                    'error': 'Request timeout',
                    'response': ''
                }

            except requests.exceptions.RequestException as e:
                logger.error(f"API request failed: {e}")
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

    def _extract_response_text(self, data: Dict) -> str:
        """
        Extract response text from API response data.

        Args:
            data: API response dictionary

        Returns:
            Extracted response text
        """
        # Try common response field patterns
        if 'response' in data:
            return str(data['response'])
        elif 'message' in data:
            return str(data['message'])
        elif 'content' in data:
            return str(data['content'])
        elif 'text' in data:
            return str(data['text'])
        elif 'choices' in data and len(data['choices']) > 0:
            choice = data['choices'][0]
            if 'message' in choice:
                return str(choice['message'].get('content', ''))
            elif 'text' in choice:
                return str(choice['text'])

        # If no standard field found, return JSON dump
        return json.dumps(data)

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
        """Reset conversation history and create new session."""
        self.conversation_history = []
        self.session_id = None
        self.create_session()

    def get_conversation_history(self) -> List[Dict]:
        """
        Get the current conversation history.

        Returns:
            List of conversation messages
        """
        return self.conversation_history.copy()


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
