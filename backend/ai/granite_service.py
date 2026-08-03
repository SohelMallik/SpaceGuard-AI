"""
SpaceGuard AI — IBM Granite / watsonx.ai Integration Service
Converts structured telemetry + anomaly analysis into human-readable explanations.
"""
import json
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# Granite explanation prompt template — structured context only, no invented values
EXPLANATION_PROMPT_TEMPLATE = """You are SpaceGuard AI, an expert spacecraft health analysis system.

IMPORTANT RULES:
- Use ONLY the telemetry values provided below. Do NOT invent or estimate any sensor readings.
- If data is insufficient, say "Insufficient telemetry data is available to determine this."
- Separate observed facts from your interpretation.

SPACECRAFT TELEMETRY DATA:
{telemetry_json}

ANOMALY DETECTION RESULT:
{anomaly_json}

HEALTH SCORE:
{health_json}

TREND PREDICTIONS:
{predictions_json}

Based on the above data, provide a structured analysis with EXACTLY these sections:
DETECTED PROBLEM: [describe what is wrong, referencing specific sensor values]
AFFECTED SUBSYSTEM: [subsystem name]
SEVERITY: [NORMAL/LOW/MODERATE/HIGH/CRITICAL]
EVIDENCE: [list the specific telemetry readings that indicate the problem]
POSSIBLE CAUSE: [most likely technical explanation]
RECOMMENDED ACTION: [specific steps mission operators should take]

Remember: This is decision-support information, NOT autonomous flight commands.
"""

ASSISTANT_PROMPT_TEMPLATE = """You are SpaceGuard AI Mission Assistant, an expert spacecraft monitoring assistant.

IMPORTANT RULES:
- Answer ONLY based on the telemetry and analysis data provided below.
- Do NOT invent sensor readings or make up values not present in the data.
- If data is insufficient, say "Insufficient telemetry data is available to determine this."
- Clearly label what is measured data vs AI interpretation.

CURRENT MISSION CONTEXT:
{context_json}

OPERATOR QUESTION: {question}

Provide a clear, concise answer to the operator's question based solely on the provided context.
"""


class GraniteService:
    """
    Calls IBM Granite via watsonx.ai REST API for natural language explanations.
    Falls back to rule-based explanation if API is unavailable.
    """

    def __init__(self):
        self.api_key = settings.WATSONX_API_KEY
        self.project_id = settings.WATSONX_PROJECT_ID
        self.base_url = settings.WATSONX_URL
        self.model_id = settings.WATSONX_MODEL_ID
        self._iam_token = None

    def _get_iam_token(self) -> str:
        """Exchange IBM API key for IAM bearer token."""
        if not self.api_key:
            raise ValueError('WATSONX_API_KEY is not configured.')
        response = requests.post(
            'https://iam.cloud.ibm.com/identity/token',
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            data={
                'grant_type': 'urn:ibm:params:oauth:grant-type:apikey',
                'apikey': self.api_key,
            },
            timeout=30,
        )
        response.raise_for_status()
        self._iam_token = response.json()['access_token']
        return self._iam_token

    def _call_granite(self, prompt: str) -> str:
        """
        Call watsonx.ai text generation endpoint.
        Returns the generated text string.
        """
        token = self._get_iam_token()
        url = f'{self.base_url}/ml/v1/text/generation?version=2023-05-29'
        payload = {
            'model_id': self.model_id,
            'project_id': self.project_id,
            'input': prompt,
            'parameters': {
                'decoding_method': 'greedy',
                'max_new_tokens': 500,
                'stop_sequences': [],
                'repetition_penalty': 1.1,
            },
        }
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        result = response.json()
        return result['results'][0]['generated_text'].strip()

    def _parse_explanation(self, raw_text: str, anomaly_result: dict) -> dict:
        """
        Parse structured sections from the Granite response text.
        Gracefully handles partial responses.
        """
        sections = {
            'DETECTED PROBLEM': 'detected_problem',
            'AFFECTED SUBSYSTEM': 'affected_subsystem',
            'SEVERITY': 'severity',
            'EVIDENCE': 'evidence',
            'POSSIBLE CAUSE': 'possible_cause',
            'RECOMMENDED ACTION': 'recommended_action',
        }
        result = {}
        lines = raw_text.split('\n')
        current_key = None
        current_value = []

        for line in lines:
            matched = False
            for label, key in sections.items():
                if line.upper().startswith(label + ':'):
                    if current_key:
                        result[current_key] = ' '.join(current_value).strip()
                    current_key = key
                    current_value = [line[len(label) + 1:].strip()]
                    matched = True
                    break
            if not matched and current_key:
                current_value.append(line.strip())

        if current_key:
            result[current_key] = ' '.join(current_value).strip()

        # Fill missing fields from anomaly_result as fallback
        result.setdefault('detected_problem', 'Anomaly detected in spacecraft telemetry.')
        result.setdefault('affected_subsystem', anomaly_result.get('affected_subsystem', 'UNKNOWN'))
        result.setdefault('severity', anomaly_result.get('severity', 'UNKNOWN'))
        result.setdefault('evidence', str(anomaly_result.get('suspicious_parameters', [])))
        result.setdefault('possible_cause', 'Further investigation required.')
        result.setdefault('recommended_action', 'Review telemetry data and consult mission protocols.')
        return result

    def _fallback_explanation(self, anomaly_result: dict, health_result: dict) -> dict:
        """
        Rule-based explanation used when watsonx API is unavailable.
        Clearly labeled as non-AI output.
        """
        severity = anomaly_result.get('severity', 'UNKNOWN')
        subsystem = anomaly_result.get('affected_subsystem', 'UNKNOWN')
        params = anomaly_result.get('suspicious_parameters', [])
        score = health_result.get('health_score', 'N/A')
        params_str = ', '.join(params) if params else 'no specific parameters identified'

        return {
            'detected_problem': f'Anomaly detected with severity {severity}.',
            'affected_subsystem': subsystem,
            'severity': severity,
            'evidence': f'Suspicious parameters: {params_str}. Health score: {score}/100.',
            'possible_cause': 'Subsystem degradation detected by anomaly detection model.',
            'recommended_action': (
                'Review the identified parameters and consult mission protocols for '
                f'{subsystem.lower()} subsystem anomaly procedures.'
            ),
            'generated_by': 'Rule-Based Fallback (IBM Granite unavailable)',
        }

    def explain_anomaly(
        self,
        telemetry_data: dict,
        anomaly_result: dict,
        health_result: dict,
        predictions: list,
    ) -> dict:
        """
        Generate structured AI explanation for an anomaly.
        Returns the parsed explanation dict.
        """
        if not self.api_key or not self.project_id:
            logger.warning('watsonx credentials not configured — using fallback explanation.')
            fallback = self._fallback_explanation(anomaly_result, health_result)
            fallback['generated_by'] = 'Rule-Based Fallback (credentials not configured)'
            return fallback

        prompt = EXPLANATION_PROMPT_TEMPLATE.format(
            telemetry_json=json.dumps(telemetry_data, indent=2, default=str),
            anomaly_json=json.dumps(anomaly_result, indent=2),
            health_json=json.dumps(health_result, indent=2),
            predictions_json=json.dumps(predictions, indent=2),
        )

        try:
            raw_text = self._call_granite(prompt)
            parsed = self._parse_explanation(raw_text, anomaly_result)
            parsed['generated_by'] = 'IBM Granite (ibm/granite-13b-instruct-v2)'
            parsed['raw_response'] = raw_text
            return parsed
        except Exception as exc:
            logger.error('Granite API call failed: %s', exc)
            fallback = self._fallback_explanation(anomaly_result, health_result)
            fallback['generated_by'] = f'Rule-Based Fallback (API error: {type(exc).__name__})'
            return fallback

    def ask_assistant(self, context: dict, question: str) -> dict:
        """
        Answer a mission operator question using injected mission context.
        Never invents sensor values.
        """
        if not self.api_key or not self.project_id:
            return {
                'answer': 'IBM Granite is not configured. Please set WATSONX_API_KEY and WATSONX_PROJECT_ID.',
                'source': 'System',
            }

        prompt = ASSISTANT_PROMPT_TEMPLATE.format(
            context_json=json.dumps(context, indent=2, default=str),
            question=question,
        )

        try:
            raw_text = self._call_granite(prompt)
            return {
                'answer': raw_text,
                'source': 'IBM Granite (ibm/granite-13b-instruct-v2)',
            }
        except Exception as exc:
            logger.error('Granite assistant call failed: %s', exc)
            return {
                'answer': 'Insufficient telemetry data is available to determine this, or the AI service is temporarily unavailable.',
                'source': f'System (API error: {type(exc).__name__})',
            }
