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

CURRENT SPACE WEATHER CONDITIONS:
{space_weather_json}

Based on the above data, provide a structured analysis with EXACTLY these sections:
DETECTED PROBLEM: [describe what is wrong, referencing specific sensor values]
AFFECTED SUBSYSTEM: [subsystem name]
SEVERITY: [NORMAL/LOW/MODERATE/HIGH/CRITICAL]
EVIDENCE: [list the specific telemetry readings that indicate the problem]
POSSIBLE CAUSE: [most likely technical explanation, considering space weather if relevant]
RECOMMENDED ACTION: [specific steps mission operators should take]

Remember: This is decision-support information, NOT autonomous flight commands.
"""

ASSISTANT_PROMPT_TEMPLATE = """You are SpaceGuard AI Mission Assistant, an expert spacecraft health monitoring advisor.

IMPORTANT RULES:
- Answer ONLY based on the telemetry and analysis data provided below. Do NOT invent values.
- If data is insufficient, say "Insufficient telemetry data is available to determine this."
- Structure every answer in three parts:
  1. PROBLEM: What is happening (reference exact sensor values)
  2. WHY: Root cause or likely reason it happened
  3. FIX: Specific, actionable steps the mission operator should take right now

CURRENT MISSION CONTEXT:
{context_json}

OPERATOR QUESTION: {question}

Respond as a knowledgeable spacecraft health advisor. Be specific, reference actual numbers, and always provide the three-part structure above.
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
        self._token_expiry = 0  # unix timestamp

    def _get_iam_token(self) -> str:
        """Exchange IBM API key for IAM bearer token. Refreshes when within 5 min of expiry."""
        import time
        if not self.api_key:
            raise ValueError('WATSONX_API_KEY is not configured.')
        # Refresh if no token or expiry within 5 minutes
        if self._iam_token and time.time() < self._token_expiry - 300:
            return self._iam_token
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
        payload = response.json()
        self._iam_token = payload['access_token']
        self._token_expiry = time.time() + payload.get('expires_in', 3600)
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

    def _fallback_explanation(self, anomaly_result: dict, health_result: dict, space_weather: dict = None) -> dict:
        """
        Rule-based explanation used when watsonx API is unavailable.
        Clearly labeled as non-AI output.
        """
        severity = anomaly_result.get('severity', 'UNKNOWN')
        subsystem = anomaly_result.get('affected_subsystem', 'UNKNOWN')
        params = anomaly_result.get('suspicious_parameters', [])
        score = health_result.get('health_score', 'N/A')
        params_str = ', '.join(params) if params else 'no specific parameters identified'
        sw = space_weather or {}
        weather_note = ''
        if sw.get('risk_level') in ('HIGH', 'EXTREME'):
            weather_note = (
                f' Current space weather is {sw["risk_level"]} '
                f'(score {sw.get("risk_score", "?")}/100, recommendation: {sw.get("recommendation", "?")}). '
                'Solar activity may be contributing to this anomaly.'
            )

        return {
            'detected_problem': f'Anomaly detected with severity {severity} in {subsystem} subsystem.{weather_note}',
            'affected_subsystem': subsystem,
            'severity': severity,
            'evidence': f'Suspicious parameters: {params_str}. Health score: {score}/100.',
            'possible_cause': (
                f'Subsystem degradation detected by anomaly detection model.{weather_note}'
            ),
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
        space_weather: dict = None,
    ) -> dict:
        """
        Generate structured AI explanation for an anomaly.
        Returns the parsed explanation dict.
        """
        if not self.api_key or not self.project_id:
            logger.warning('watsonx credentials not configured — using fallback explanation.')
            fallback = self._fallback_explanation(anomaly_result, health_result, space_weather or {})
            fallback['generated_by'] = 'Rule-Based Fallback (credentials not configured)'
            return fallback

        prompt = EXPLANATION_PROMPT_TEMPLATE.format(
            telemetry_json=json.dumps(telemetry_data, indent=2, default=str),
            anomaly_json=json.dumps(anomaly_result, indent=2, default=str),
            health_json=json.dumps(health_result, indent=2, default=str),
            predictions_json=json.dumps(predictions, indent=2, default=str),
            space_weather_json=json.dumps(space_weather or {}, indent=2, default=str),
        )

        try:
            raw_text = self._call_granite(prompt)
            parsed = self._parse_explanation(raw_text, anomaly_result)
            parsed['generated_by'] = 'IBM Granite (ibm/granite-13b-instruct-v2)'
            parsed['raw_response'] = raw_text
            return parsed
        except Exception as exc:
            logger.error('Granite API call failed: %s', exc)
            fallback = self._fallback_explanation(anomaly_result, health_result, space_weather or {})
            fallback['generated_by'] = f'Rule-Based Fallback (API error: {type(exc).__name__})'
            return fallback

    def ask_assistant(self, context: dict, question: str) -> dict:
        """
        Answer a mission operator question using injected mission context.
        Uses IBM Granite if credentials are configured, otherwise uses the
        built-in rule-based AI agent which reads real telemetry data.
        Never invents sensor values.
        """
        if self.api_key and self.project_id:
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
                # Fall through to local agent

        # ── Local AI Agent — answers from real telemetry context ──────────
        return _local_ai_agent(context, question)


def _local_ai_agent(context: dict, question: str) -> dict:
    """
    Intelligent AI agent that reads real telemetry, health, anomaly and alert
    data from context and composes structured Problem → Why → How responses.
    Always grounded in actual sensor values — never invents data.
    """
    q = question.lower().strip()
    tel = context.get('latest_telemetry', {})
    health = context.get('health', {})
    anomaly = context.get('latest_anomaly', {})
    explanation = context.get('latest_explanation', {})
    alerts = context.get('active_alerts', [])
    spacecraft = context.get('spacecraft', 'the spacecraft')
    mission = context.get('mission_name', 'this mission')
    status = context.get('mission_status', 'ACTIVE')
    sw = context.get('space_weather', {})

    # ── Helper functions ──────────────────────────────────────────────────
    def fv(key, unit='', decimals=1):
        """Format a telemetry value cleanly, return 'N/A' if missing."""
        v = tel.get(key)
        if v is None:
            return 'N/A'
        return f'{round(float(v), decimals)}{unit}'

    def _diagnose_all_problems():
        """
        Scan every telemetry sensor against thresholds.
        Returns list of dicts: {sensor, value, unit, status, why, fix}
        """
        THRESHOLDS = {
            'temperature': {
                'unit': '°C', 'normal': (-50, 85), 'warn': (85, 100), 'crit': (100, None),
                'why_high': 'Thermal regulation failure, heater malfunction, or high solar irradiance exposure.',
                'why_low': 'Deep-space cooling or thermal control system fault.',
                'fix_high': '1. Reduce non-essential power loads to cut heat generation.\n2. Orient spacecraft to reduce solar exposure if attitude permits.\n3. Activate thermal management protocols.\n4. Alert thermal engineering team.',
                'fix_low': '1. Activate supplementary heaters.\n2. Increase power to thermal control subsystem.\n3. Review thermal model for orbital position.',
            },
            'battery_voltage': {
                'unit': 'V', 'normal': (22, 32), 'warn': (18, 22), 'crit': (None, 18),
                'why_low': 'Excessive power draw, solar panel degradation, charging circuit failure, or eclipse period overrun.',
                'fix_low': '1. Immediately shed non-critical loads (science instruments, heaters).\n2. Verify solar panel orientation and output.\n3. Check charging circuit status.\n4. Enter power-safe mode if voltage drops below 20V.',
            },
            'battery_current': {
                'unit': 'A', 'normal': (-5, 20), 'warn': (20, 25), 'crit': (25, None),
                'why_high': 'Short circuit, unexpected load spike, or a subsystem drawing abnormal current.',
                'fix_high': '1. Identify the subsystem causing the current spike via individual circuit monitoring.\n2. Isolate the offending load.\n3. Run electrical fault diagnostics.',
            },
            'fuel_level': {
                'unit': '%', 'normal': (20, 100), 'warn': (5, 20), 'crit': (None, 5),
                'why_low': 'Mission duration exceeding budget, thruster leak, or unplanned maneuvers consumed excess propellant.',
                'fix_low': '1. Immediately suspend all non-essential maneuvers.\n2. Calculate remaining delta-V budget.\n3. Notify mission planning team for mission duration reassessment.\n4. If critically low (<5%), initiate end-of-mission contingency plan.',
            },
            'radiation': {
                'unit': ' mSv', 'normal': (0, 50), 'warn': (50, 100), 'crit': (100, None),
                'why_high': 'Spacecraft is passing through a radiation belt, solar energetic particle event, or X-class solar flare.',
                'fix_high': '1. Increase monitoring frequency for radiation-sensitive components.\n2. Enable radiation hardening mode if available.\n3. If SEU (Single Event Upset) risk is high, put computers into safe mode.\n4. Correlate with space weather data for solar event confirmation.',
            },
            'pressure': {
                'unit': ' kPa', 'normal': (95, 110), 'warn': (90, 95), 'crit': (None, 90),
                'why_low': 'Possible hull micro-fracture, seal degradation, or venting anomaly.',
                'why_high': 'Pressurization system overshoot or regulator malfunction.',
                'fix_low': '1. Immediately check pressure decay rate — compare current vs last 10 readings.\n2. Isolate compartments to localise the leak.\n3. Activate emergency sealing procedures if decay rate exceeds 0.5 kPa/hr.\n4. Alert crew/ground station immediately.',
                'fix_high': '1. Reduce pressurization input.\n2. Open relief valve if pressure exceeds 115 kPa.\n3. Inspect pressure regulator for malfunction.',
            },
            'signal_strength': {
                'unit': ' dBm', 'normal': (-120, -40), 'warn': (-130, -120), 'crit': (None, -130),
                'why_low': 'Antenna misalignment, atmospheric interference, large orbital distance, or hardware fault.',
                'fix_low': '1. Verify ground station antenna pointing and azimuth.\n2. Check spacecraft antenna deployment and orientation.\n3. Switch to backup transponder if available.\n4. Reduce data rate to maintain link budget.\n5. Schedule next ground pass for diagnostic command uplink.',
            },
            'velocity': {
                'unit': ' km/s', 'normal': (0, 30), 'warn': (30, 35), 'crit': (35, None),
                'why_high': 'Orbital decay burn miscalculation, unplanned thrust, or navigation anomaly.',
                'fix_high': '1. Verify navigation solution against ground tracking data.\n2. Cross-check with GPS/star tracker.\n3. Halt all thruster burns pending investigation.\n4. Issue corrective deorbit/orbit-raise burn after verification.',
            },
            'power_consumption': {
                'unit': 'W', 'normal': (0, 500), 'warn': (500, 600), 'crit': (600, None),
                'why_high': 'Multiple subsystems in active state simultaneously, thermal heater runaway, or payload instrument fault.',
                'fix_high': '1. Identify top power consumers via subsystem telemetry.\n2. Shut down non-mission-critical instruments.\n3. Reduce heater setpoints if thermal margin allows.\n4. Schedule high-power operations sequentially rather than in parallel.',
            },
        }

        problems = []
        for sensor, cfg in THRESHOLDS.items():
            v = tel.get(sensor)
            if v is None:
                continue
            v = float(v)
            unit = cfg['unit']
            norm_lo, norm_hi = cfg['normal']
            warn_lo, warn_hi = cfg.get('warn', (None, None))
            crit_lo, crit_hi = cfg.get('crit', (None, None))

            prob_status = None
            direction = None

            # Check critical
            if crit_hi is not None and v > crit_hi:
                prob_status, direction = '🔴 CRITICAL', 'high'
            elif crit_lo is not None and v < crit_lo:
                prob_status, direction = '🔴 CRITICAL', 'low'
            # Check warning
            elif warn_hi is not None and v > warn_hi:
                prob_status, direction = '⚠ WARNING', 'high'
            elif warn_lo is not None and v < warn_lo:
                prob_status, direction = '⚠ WARNING', 'low'

            if prob_status:
                why_key = f'why_{direction}'
                fix_key = f'fix_{direction}'
                why = cfg.get(why_key, cfg.get('why_high', cfg.get('why_low', 'Sensor reading outside normal operating range.')))
                fix = cfg.get(fix_key, cfg.get('fix_high', cfg.get('fix_low', 'Review subsystem telemetry and consult mission protocols.')))
                problems.append({
                    'sensor': sensor.replace('_', ' ').title(),
                    'value': f'{round(v, 2)}{unit}',
                    'status': prob_status,
                    'direction': direction,
                    'why': why,
                    'fix': fix,
                })
        return problems

    # ── Full diagnostic (default + broad queries) ─────────────────────────
    def _full_diagnostic_response():
        score = health.get('health_score', 'N/A')
        level = health.get('risk_level', 'N/A')
        category = health.get('health_category', 'Awaiting analysis')
        breakdown = health.get('score_breakdown', {})
        is_anom = anomaly.get('is_anomaly', False)
        severity = anomaly.get('severity', 'NORMAL')
        subsystem = anomaly.get('affected_subsystem', 'UNKNOWN')
        params = anomaly.get('suspicious_parameters', [])
        det_problem = explanation.get('detected_problem', '')
        possible_cause = explanation.get('possible_cause', '')
        recommended = explanation.get('recommended_action', '')
        evidence = explanation.get('evidence', '')

        problems = _diagnose_all_problems()

        # ─ HEADER
        lines = [f"**SpaceGuard AI — Full Diagnostic Report: {spacecraft}**\n"]
        lines.append(f"**Mission:** {mission} | **Status:** {status}")
        lines.append(f"**Health Score:** {score}/100 ({category}) | **Risk Level:** {level}\n")

        # ─ SCORE BREAKDOWN
        bd = breakdown
        bd_parts = []
        if bd.get('anomaly_severity', 0) != 0:
            bd_parts.append(f"Anomaly severity: {bd['anomaly_severity']:+d} pts")
        if bd.get('threshold_violations', 0) != 0:
            bd_parts.append(f"Threshold violations: {bd['threshold_violations']:+d} pts")
        if bd.get('trend_penalty', 0) != 0:
            bd_parts.append(f"Trend penalty: {bd['trend_penalty']:+d} pts")
        if bd_parts:
            lines.append("**Score Deductions:** " + " | ".join(bd_parts) + "\n")

        # ─ ANOMALY SECTION
        if is_anom or severity not in ('NORMAL', 'LOW', None, ''):
            lines.append(f"---\n**⚠ ANOMALY DETECTED — Severity: {severity}**")
            lines.append(f"**Affected Subsystem:** {subsystem}")
            if params:
                lines.append(f"**Suspicious Parameters:** {', '.join(params)}")
            if det_problem:
                lines.append(f"\n**🔍 PROBLEM:** {det_problem}")
            if evidence:
                lines.append(f"**📋 EVIDENCE:** {evidence}")
            if possible_cause:
                lines.append(f"**❓ WHY IT HAPPENED:** {possible_cause}")
            if recommended:
                lines.append(f"**✅ HOW TO FIX:** {recommended}")
        else:
            lines.append("**✓ No active ML anomaly detected.** All parameters within model bounds.")

        # ─ SENSOR-BY-SENSOR PROBLEMS
        if problems:
            lines.append(f"\n---\n**🚨 Sensor Threshold Violations ({len(problems)} found):**\n")
            for p in problems:
                lines.append(f"**{p['status']} — {p['sensor']}: {p['value']}**")
                lines.append(f"  **🔍 PROBLEM:** {p['sensor']} reading is {p['direction']} of safe operating range.")
                lines.append(f"  **❓ WHY:** {p['why']}")
                lines.append(f"  **✅ FIX:**\n{_indent(p['fix'])}\n")
        else:
            lines.append("\n**✓ All sensor readings are within normal operating thresholds.**")

        # ─ ACTIVE ALERTS
        if alerts:
            lines.append(f"\n---\n**🔔 Active Alerts ({len(alerts)}):**")
            for a in alerts[:5]:
                lines.append(f"• [{a.get('severity','?')}] **{a.get('subsystem','?')}** — {a.get('description', '')[:120]}")

        # ─ SPACE WEATHER
        if sw and sw.get('risk_level') in ('MODERATE', 'HIGH', 'EXTREME'):
            lines.append(f"\n---\n**☀ Space Weather Impact: {sw.get('risk_level')} (score {sw.get('risk_score')}/100)**")
            at_risk = sw.get('at_risk_subsystems', [])
            if at_risk:
                lines.append(f"  At-risk subsystems: {', '.join(at_risk)}")
            lines.append(f"  Recommendation: {sw.get('recommendation', 'CAUTION')}")

        return '\n'.join(lines)

    def _indent(text, prefix='    '):
        return '\n'.join(prefix + line for line in text.strip().split('\n'))

    # ── Single subsystem — Problem+Why+How ───────────────────────────────
    def _subsystem_pwh(sensor_key, display_name, value_str, norm_range_str,
                       prob_status, direction, why, fix, extra_context=''):
        lines = [f"**{display_name} — {spacecraft}**\n"]
        lines.append(f"**Current Reading:** {value_str}")
        lines.append(f"**Normal Range:** {norm_range_str}")
        lines.append(f"**Status:** {prob_status}\n")
        if prob_status not in ('✓ Normal',):
            lines.append(f"**🔍 PROBLEM:** {display_name} is {direction} of the safe operating limit.")
            lines.append(f"\n**❓ WHY IT HAPPENED:**\n{why}")
            lines.append(f"\n**✅ HOW TO FIX IT:**\n{fix}")
        else:
            lines.append(f"✓ {display_name} is operating within normal parameters.")
            if extra_context:
                lines.append(extra_context)
        return '\n'.join(lines)

    # ══════════════════════════════════════════════════════════════════════
    # ROUTING — match question intent to the right handler
    # ══════════════════════════════════════════════════════════════════════

    # ── Help / capabilities ───────────────────────────────────────────────
    if any(w in q for w in ['help', 'can you', 'what can', 'capabilities', 'commands', 'hi ', 'hello', 'hey']):
        answer = (
            f"**SpaceGuard AI Mission Assistant — {spacecraft}**\n\n"
            f"I analyze real-time spacecraft telemetry and give you structured **Problem → Why → How to Fix** answers.\n\n"
            f"**Ask me things like:**\n"
            f"• *\"What is wrong with the spacecraft?\"*\n"
            f"• *\"Why is the temperature high?\"*\n"
            f"• *\"How do I fix the battery problem?\"*\n"
            f"• *\"Show full diagnostic report\"*\n"
            f"• *\"What is the health status?\"*\n"
            f"• *\"Explain the anomaly\"*\n"
            f"• *\"Check battery and power\"*\n"
            f"• *\"What are the active alerts?\"*\n"
            f"• *\"What is the space weather risk?\"*\n\n"
            f"Every answer is grounded in live telemetry data — I never invent values."
        )
        return {'answer': answer, 'source': 'SpaceGuard AI'}

    # ── Full diagnostic / broad health / "what's wrong" ──────────────────
    if any(w in q for w in [
        'full', 'diagnostic', 'report', 'everything', 'all', 'summary',
        'what is wrong', "what's wrong", 'whats wrong', 'any problem',
        'any issue', 'check all', 'full report',
    ]):
        return {'answer': _full_diagnostic_response(), 'source': 'SpaceGuard AI'}

    # ── Health / risk level ───────────────────────────────────────────────
    if any(w in q for w in ['health', 'status', 'overall', 'condition', 'risk level',
                             'how is', 'how are', 'mission status']):
        score = health.get('health_score', 'N/A')
        level = health.get('risk_level', 'N/A')
        category = health.get('health_category', 'Awaiting analysis')
        breakdown = health.get('score_breakdown', {})
        problems = _diagnose_all_problems()

        bd_parts = []
        if breakdown.get('anomaly_severity', 0) != 0:
            bd_parts.append(f"anomaly severity: {breakdown['anomaly_severity']:+d} pts")
        if breakdown.get('threshold_violations', 0) != 0:
            bd_parts.append(f"threshold violations: {breakdown['threshold_violations']:+d} pts")
        if breakdown.get('trend_penalty', 0) != 0:
            bd_parts.append(f"trend penalty: {breakdown['trend_penalty']:+d} pts")

        lines = [f"**{spacecraft} — Health Status**\n"]
        lines.append(f"**🏥 Health Score:** {score}/100 ({category})")
        lines.append(f"**⚡ Risk Level:** {level}")
        lines.append(f"**🚀 Mission:** {mission} | Status: {status}\n")
        if bd_parts:
            lines.append("**Score Breakdown:** " + " | ".join(bd_parts) + "\n")

        if level in ('HIGH', 'CRITICAL'):
            rec = explanation.get('recommended_action', '')
            cause = explanation.get('possible_cause', '')
            problem_desc = explanation.get('detected_problem', '')
            lines.append(f"**🔍 PROBLEM:** Health is degraded — {problem_desc or f'{level} risk level detected.'}")
            if cause:
                lines.append(f"\n**❓ WHY:** {cause}")
            if rec:
                lines.append(f"\n**✅ HOW TO FIX:**\n{rec}")
            elif problems:
                lines.append(f"\n**✅ IMMEDIATE ACTIONS:**")
                for p in problems[:3]:
                    lines.append(f"• Address {p['sensor']}: {p['value']} ({p['status']})")
        elif level == 'MODERATE':
            lines.append("**⚠ PROBLEM:** Mild anomalies detected. Close monitoring required.")
            lines.append("**❓ WHY:** One or more subsystems are approaching threshold limits.")
            lines.append("**✅ HOW TO FIX:** Increase telemetry polling. Review flagged parameters. No immediate action required.")
        else:
            lines.append("**✓ PROBLEM:** None — spacecraft is healthy.")
            lines.append("**✓ WHY:** All systems are operating within design parameters.")
            lines.append("**✓ HOW TO FIX:** No intervention needed. Continue nominal operations.")
        return {'answer': '\n'.join(lines), 'source': 'SpaceGuard AI'}

    # ── Anomaly / fault / explain ─────────────────────────────────────────
    if any(w in q for w in ['anomaly', 'anomalies', 'problem', 'issue', 'fault', 'detected',
                             'explain', 'what happened', 'why did', 'cause', 'investigate']):
        is_anom = anomaly.get('is_anomaly', False)
        severity = anomaly.get('severity', 'NORMAL')
        subsystem = anomaly.get('affected_subsystem', 'UNKNOWN')
        params = anomaly.get('suspicious_parameters', [])
        anom_score = anomaly.get('anomaly_score', 0)
        det_problem = explanation.get('detected_problem', '')
        possible_cause = explanation.get('possible_cause', '')
        recommended = explanation.get('recommended_action', '')
        evidence = explanation.get('evidence', '')
        problems = _diagnose_all_problems()

        if not is_anom and severity in ('NORMAL', '', None) and not problems:
            answer = (
                f"✓ **No anomaly or threshold violation detected on {spacecraft}.**\n\n"
                f"**🔍 PROBLEM:** None found.\n"
                f"**❓ WHY:** All 9 telemetry parameters are within normal operating bounds "
                f"and the Isolation Forest model reports a normal anomaly score ({anom_score}).\n"
                f"**✅ HOW TO FIX:** No corrective action required. Continue nominal monitoring."
            )
        else:
            lines = [f"**Anomaly Analysis — {spacecraft}**\n"]
            if is_anom or severity not in ('NORMAL', '', None):
                lines.append(f"**ML Anomaly Detected — Severity: {severity}**")
                lines.append(f"• Affected Subsystem: {subsystem}")
                lines.append(f"• Anomaly Score: {anom_score}")
                if params:
                    lines.append(f"• Suspicious Parameters: {', '.join(params)}\n")
                if det_problem:
                    lines.append(f"**🔍 PROBLEM:** {det_problem}")
                if evidence:
                    lines.append(f"**📋 EVIDENCE:** {evidence}")
                if possible_cause:
                    lines.append(f"\n**❓ WHY IT HAPPENED:** {possible_cause}")
                if recommended:
                    lines.append(f"\n**✅ HOW TO FIX IT:**\n{recommended}")
                else:
                    lines.append(f"\n**✅ HOW TO FIX IT:** Review {subsystem} subsystem telemetry logs and consult anomaly response protocols.")

            if problems:
                lines.append(f"\n**Additional Sensor Violations ({len(problems)}):**")
                for p in problems:
                    lines.append(f"\n**{p['status']} — {p['sensor']}: {p['value']}**")
                    lines.append(f"  ❓ WHY: {p['why']}")
                    lines.append(f"  ✅ FIX:\n{_indent(p['fix'])}")
            answer = '\n'.join(lines)
        return {'answer': answer, 'source': 'SpaceGuard AI'}

    # ── Temperature ───────────────────────────────────────────────────────
    if any(w in q for w in ['temperature', 'temp', 'thermal', 'heat', 'hot', 'cold', 'overheating']):
        t = tel.get('temperature')
        if t is None:
            return {'answer': 'Temperature data is not currently available.', 'source': 'SpaceGuard AI'}
        t = float(t)
        if t > 100:
            prob, why, fix = '🔴 CRITICAL', (
                'Thermal regulation system failure, heater runaway, or extreme solar irradiance exposure.'
            ), (
                '1. Reduce all non-essential power loads to cut internal heat generation.\n'
                '2. Orient spacecraft to reduce solar-facing surface area (if attitude control permits).\n'
                '3. Activate emergency thermal management protocols.\n'
                '4. Notify thermal engineering team immediately.\n'
                '5. If temperature continues rising, initiate safe-mode to reduce instrument heat.'
            )
        elif t > 85:
            prob, why, fix = '⚠ WARNING', (
                'Thermal control system is stressed — likely a heater malfunction, increased power dissipation, or high solar input.'
            ), (
                '1. Reduce power to non-critical subsystems.\n'
                '2. Verify thermal control louvers/radiators are operating correctly.\n'
                '3. Monitor temperature trend — if rising >0.5°C per reading, escalate immediately.\n'
                '4. Review recent maneuvers that may have changed solar exposure angle.'
            )
        else:
            return {'answer': _subsystem_pwh(
                'temperature', 'Thermal Subsystem', f'{round(t,1)}°C',
                '-50°C to 85°C (Critical: >100°C)', '✓ Normal', '', '', ''
            ), 'source': 'SpaceGuard AI'}
        return {'answer': _subsystem_pwh(
            'temperature', 'Thermal Subsystem', f'{round(t,1)}°C',
            '-50°C to 85°C (Critical: >100°C)', prob, 'above', why, fix
        ), 'source': 'SpaceGuard AI'}

    # ── Battery / power ───────────────────────────────────────────────────
    if any(w in q for w in ['battery', 'voltage', 'power', 'electrical', 'current', 'watt']):
        bv = tel.get('battery_voltage')
        pc = tel.get('power_consumption')
        bc = tel.get('battery_current')
        lines = [f"**Electrical Subsystem — {spacecraft}**\n"]
        lines.append(f"• Battery Voltage:   **{fv('battery_voltage', 'V')}**  (Normal: 22–32V | Critical: <18V)")
        lines.append(f"• Battery Current:   **{fv('battery_current', 'A')}**  (Normal: -5 to 20A)")
        lines.append(f"• Power Consumption: **{fv('power_consumption', 'W', 0)}**  (Normal: <500W | Critical: >600W)\n")

        issues = []
        if bv is not None and float(bv) < 18:
            issues.append(('🔴 CRITICAL', 'Battery Voltage',
                'Battery voltage has dropped below the critical 18V threshold.',
                'Solar panel degradation, charging circuit failure, or excessive power draw during eclipse.',
                '1. Enter power-safe mode: shut down all non-essential instruments.\n'
                '2. Verify solar array pointing — ensure panels face the sun.\n'
                '3. Check charge controller status for faults.\n'
                '4. Shed loads until voltage stabilises above 22V.\n'
                '5. If below 16V, initiate emergency battery protection mode.'))
        elif bv is not None and float(bv) < 22:
            issues.append(('⚠ WARNING', 'Battery Voltage',
                f'Battery voltage at {round(float(bv),1)}V is below the 22V warning threshold.',
                'Elevated power consumption, partial solar panel shadowing, or battery capacity degradation over time.',
                '1. Reduce non-critical power loads.\n'
                '2. Monitor voltage trend — if dropping more than 0.5V per telemetry cycle, treat as critical.\n'
                '3. Check solar panel output telemetry.'))
        if pc is not None and float(pc) > 600:
            issues.append(('🔴 CRITICAL', 'Power Consumption',
                f'Power consumption at {round(float(pc),0)}W exceeds the 600W critical limit.',
                'Multiple high-power instruments running simultaneously, heater runaway, or electrical fault.',
                '1. Identify top power-consuming subsystems.\n'
                '2. Immediately shut down non-essential instruments.\n'
                '3. Reduce heater setpoints if thermal budget allows.\n'
                '4. Schedule high-power activities sequentially.'))
        elif pc is not None and float(pc) > 500:
            issues.append(('⚠ WARNING', 'Power Consumption',
                f'Power consumption at {round(float(pc),0)}W is above the 500W warning level.',
                'Several subsystems are running at high power simultaneously.',
                '1. Review active instrument schedule.\n'
                '2. Stagger high-power operations to reduce peak consumption.'))

        if issues:
            for sev, name, prob, why, fix in issues:
                lines.append(f"**{sev} — {name}**")
                lines.append(f"**🔍 PROBLEM:** {prob}")
                lines.append(f"\n**❓ WHY IT HAPPENED:** {why}")
                lines.append(f"\n**✅ HOW TO FIX IT:**\n{_indent(fix)}\n")
        else:
            lines.append("**✓ PROBLEM:** None — all electrical readings are nominal.")
            lines.append("**✓ WHY:** Battery, current, and power consumption are all within design limits.")
            lines.append("**✓ HOW TO FIX:** No action needed. Continue monitoring.")
        return {'answer': '\n'.join(lines), 'source': 'SpaceGuard AI'}

    # ── Fuel ──────────────────────────────────────────────────────────────
    if any(w in q for w in ['fuel', 'propulsion', 'propellant', 'thruster', 'delta-v', 'deltav']):
        f = tel.get('fuel_level')
        if f is None:
            return {'answer': 'Fuel level data is not available.', 'source': 'SpaceGuard AI'}
        f = float(f)
        if f < 5:
            prob = '🔴 CRITICAL'
            why = 'Fuel reserves are critically depleted. Possible causes: mission exceeded propellant budget, thruster leak, or unplanned emergency burns.'
            fix = ('1. Suspend ALL non-emergency maneuvers immediately.\n'
                   '2. Calculate remaining delta-V (likely <10 m/s).\n'
                   '3. Notify mission planning — assess deorbit vs station-keeping priority.\n'
                   '4. Initiate end-of-mission contingency procedures.\n'
                   '5. If thruster leak suspected, close fuel isolation valves.')
        elif f < 20:
            prob = '⚠ WARNING'
            why = 'Fuel level is approaching the warning threshold. Mission duration and remaining maneuver budget are limited.'
            fix = ('1. Suspend all non-critical maneuver activities.\n'
                   '2. Calculate minimum fuel required for safe deorbit/disposal.\n'
                   '3. Brief mission planning team on remaining propellant margin.\n'
                   '4. Delay any orbit correction burns pending fuel budget review.')
        else:
            return {'answer': _subsystem_pwh(
                'fuel_level', 'Propulsion Subsystem', f'{round(f,1)}%',
                '20–100% operational | Warning: <20% | Critical: <5%', '✓ Normal', '', '', '',
                extra_context=f'✓ Fuel reserves at {round(f,1)}% — adequate for continued operations.'
            ), 'source': 'SpaceGuard AI'}
        return {'answer': _subsystem_pwh(
            'fuel_level', 'Propulsion Subsystem', f'{round(f,1)}%',
            '20–100% | Warning: <20% | Critical: <5%', prob, 'below', why, fix
        ), 'source': 'SpaceGuard AI'}

    # ── Signal / communication ────────────────────────────────────────────
    if any(w in q for w in ['signal', 'communication', 'comm', 'contact', 'radio', 'link', 'antenna']):
        ss = tel.get('signal_strength')
        if ss is None:
            return {'answer': 'Signal strength data is not available.', 'source': 'SpaceGuard AI'}
        ss = float(ss)
        if ss < -130:
            prob = '🔴 CRITICAL'
            why = 'Signal strength has dropped below the critical threshold. Possible causes: antenna malfunction/misalignment, severe atmospheric interference, extreme orbital geometry, or hardware failure.'
            fix = ('1. Verify ground station antenna pointing and uplink power.\n'
                   '2. Check spacecraft antenna deployment — confirm omni antenna is active.\n'
                   '3. Switch to backup transponder or low-gain antenna.\n'
                   '4. Reduce downlink data rate to maintain the link budget.\n'
                   '5. Calculate next ground pass window for re-acquisition attempt.\n'
                   '6. Send emergency uplink command on alternate frequency.')
        elif ss < -120:
            prob = '⚠ WARNING'
            why = 'Signal is weak — likely due to suboptimal antenna pointing, increased orbital distance, or mild atmospheric disturbance.'
            fix = ('1. Re-optimise ground station antenna pointing.\n'
                   '2. Reduce telemetry downlink rate from current setting.\n'
                   '3. Monitor trend — if signal drops another 5 dBm, escalate to critical.')
        else:
            return {'answer': _subsystem_pwh(
                'signal_strength', 'Communication Subsystem', f'{round(ss,1)} dBm',
                '>-120 dBm normal | -120 to -130 warning | <-130 critical', '✓ Normal', '', '', '',
                extra_context='✓ Communication link is strong and stable.'
            ), 'source': 'SpaceGuard AI'}
        return {'answer': _subsystem_pwh(
            'signal_strength', 'Communication Subsystem', f'{round(ss,1)} dBm',
            '>-120 dBm | Warning: -120 to -130 | Critical: <-130', prob, 'below', why, fix
        ), 'source': 'SpaceGuard AI'}

    # ── Radiation ─────────────────────────────────────────────────────────
    if any(w in q for w in ['radiation', 'rad', 'particle', 'cosmic', 'dose', 'solar flare', 'seu']):
        r = tel.get('radiation')
        if r is None:
            return {'answer': 'Radiation data is not available.', 'source': 'SpaceGuard AI'}
        r = float(r)
        sw_level = sw.get('risk_level', 'LOW') if sw else 'LOW'
        if r > 100:
            prob = '🔴 CRITICAL'
            why = (f'Radiation at {round(r,1)} mSv exceeds the safe limit. '
                   f'This is consistent with a Solar Energetic Particle (SEP) event or passage through the radiation belts. '
                   f'Space weather is currently: {sw_level}.')
            fix = ('1. Activate radiation hardening mode on all onboard computers.\n'
                   '2. Put scientific instruments into safe mode to prevent SEU damage.\n'
                   '3. Notify crew (if crewed mission) to move to shielded compartment.\n'
                   '4. Correlate with NOAA space weather data — check for X-class flares.\n'
                   '5. If SEU risk is critical, reboot and verify memory checksums.\n'
                   '6. Review orbital trajectory — adjust to avoid radiation belt if possible.')
        elif r > 50:
            prob = '⚠ WARNING'
            why = (f'Elevated radiation at {round(r,1)} mSv. Likely caused by mild solar activity '
                   f'or the spacecraft approaching a radiation belt. Current space weather: {sw_level}.')
            fix = ('1. Increase radiation monitoring frequency.\n'
                   '2. Enable single-event upset (SEU) protection on critical computers.\n'
                   '3. Cross-reference with space weather forecast for upcoming solar events.\n'
                   '4. Reduce exposure time in high-radiation orbital segments.')
        else:
            return {'answer': _subsystem_pwh(
                'radiation', 'Radiation Monitor', f'{round(r,1)} mSv',
                '<50 mSv normal | 50–100 elevated | >100 critical', '✓ Normal', '', '', '',
                extra_context=f'✓ Radiation within safe limits. Space weather: {sw_level}.'
            ), 'source': 'SpaceGuard AI'}
        return {'answer': _subsystem_pwh(
            'radiation', 'Radiation Monitor', f'{round(r,1)} mSv',
            '<50 mSv | Warning: 50–100 | Critical: >100', prob, 'above', why, fix
        ), 'source': 'SpaceGuard AI'}

    # ── Pressure ──────────────────────────────────────────────────────────
    if any(w in q for w in ['pressure', 'environmental', 'atmosphere', 'hull', 'seal', 'leak']):
        p = tel.get('pressure')
        if p is None:
            return {'answer': 'Pressure data is not available.', 'source': 'SpaceGuard AI'}
        p = float(p)
        if p < 90:
            prob, direction = '🔴 CRITICAL', 'below'
            why = ('Pressure has dropped critically. Possible causes: hull micro-fracture, '
                   'seal or gasket failure, or a rapid decompression event.')
            fix = ('1. Immediately check the pressure decay rate (compare last 5 readings).\n'
                   '2. Isolate compartments one by one to localise the leak source.\n'
                   '3. Activate emergency sealing procedures.\n'
                   '4. If decay rate >0.5 kPa/hr, treat as emergency decompression.\n'
                   '5. Alert crew/ground station — initiate emergency protocols immediately.')
        elif p < 95:
            prob, direction = '⚠ WARNING', 'below'
            why = 'Pressure is approaching the lower warning boundary — possible slow leak or pressurisation system drift.'
            fix = ('1. Monitor pressure trend closely over the next 5 telemetry cycles.\n'
                   '2. Check pressurisation valve status.\n'
                   '3. If pressure continues dropping, escalate to critical response.')
        elif p > 120:
            prob, direction = '🔴 CRITICAL', 'above'
            why = 'Overpressure detected. Possible pressure regulator malfunction or pressurisation valve stuck open.'
            fix = ('1. Shut off pressurisation input immediately.\n'
                   '2. Open pressure relief valve if available.\n'
                   '3. Inspect pressure regulator for runaway condition.')
        elif p > 110:
            prob, direction = '⚠ WARNING', 'above'
            why = 'Mild overpressure — pressurisation input may be slightly elevated.'
            fix = ('1. Reduce pressurisation input slightly.\n2. Monitor trend for the next 10 minutes.')
        else:
            return {'answer': _subsystem_pwh(
                'pressure', 'Environmental Subsystem', f'{round(p,1)} kPa',
                '95–110 kPa normal | Critical: <90 or >120 kPa', '✓ Normal', '', '', '',
                extra_context='✓ Cabin/module pressure is nominal.'
            ), 'source': 'SpaceGuard AI'}
        return {'answer': _subsystem_pwh(
            'pressure', 'Environmental Subsystem', f'{round(p,1)} kPa',
            '95–110 kPa | Warning: 90–95 or 110–120 | Critical: <90 or >120', prob, direction, why, fix
        ), 'source': 'SpaceGuard AI'}

    # ── Velocity / navigation ─────────────────────────────────────────────
    if any(w in q for w in ['velocity', 'speed', 'navigation', 'orbit', 'altitude', 'trajectory']):
        v = tel.get('velocity')
        if v is None:
            return {'answer': 'Velocity data is not available.', 'source': 'SpaceGuard AI'}
        v = float(v)
        if v > 35:
            prob, direction = '🔴 CRITICAL', 'above'
            why = 'Velocity exceeds the critical threshold — possible thruster runaway, navigation solution error, or unexpected orbital maneuver.'
            fix = ('1. Halt all thruster burns immediately.\n'
                   '2. Cross-verify velocity with ground tracking and GPS/star tracker.\n'
                   '3. If confirmed, compute corrective deceleration burn.\n'
                   '4. Contact Flight Dynamics for emergency trajectory analysis.')
        elif v > 30:
            prob, direction = '⚠ WARNING', 'above'
            why = 'Velocity is above the nominal warning threshold — may indicate a recent burn overshoot or navigation drift.'
            fix = ('1. Verify with star tracker/IMU cross-check.\n'
                   '2. Pause any planned burns pending navigation solution confirmation.\n'
                   '3. Compare with ground tracking data.')
        else:
            return {'answer': _subsystem_pwh(
                'velocity', 'Navigation Subsystem', f'{round(v,2)} km/s',
                '0–30 km/s normal | Warning: 30–35 | Critical: >35', '✓ Normal', '', '', '',
                extra_context='✓ Velocity and trajectory are nominal.'
            ), 'source': 'SpaceGuard AI'}
        return {'answer': _subsystem_pwh(
            'velocity', 'Navigation Subsystem', f'{round(v,2)} km/s',
            '0–30 km/s | Warning: 30–35 | Critical: >35', prob, direction, why, fix
        ), 'source': 'SpaceGuard AI'}

    # ── Space weather ─────────────────────────────────────────────────────
    if any(w in q for w in ['space weather', 'solar', 'flare', 'geomagnetic', 'kp',
                             'weather', 'launch', 'storm', 'aurora']):
        if not sw:
            return {'answer': 'Space weather data is not currently available.', 'source': 'SpaceGuard AI'}
        risk_score = sw.get('risk_score', 0)
        risk_level = sw.get('risk_level', 'LOW')
        recommendation = sw.get('recommendation', 'GO')
        xclass = sw.get('xclass_flares_48h', 0)
        mclass = sw.get('mclass_flares_48h', 0)
        kp = sw.get('max_kp_index', 0)
        storms = sw.get('storm_count', 0)
        at_risk = sw.get('at_risk_subsystems', [])
        date_str = sw.get('date', 'N/A')
        rec_emoji = {'GO': '✅', 'CAUTION': '⚠', 'DELAY': '⏳', 'NO-GO': '🛑'}.get(recommendation, '❓')

        lines = [f"**Space Weather Report — {spacecraft}**\n"]
        lines.append(f"• Date: {date_str} | Risk Score: **{risk_score}/100** | Level: **{risk_level}**")
        lines.append(f"• Launch Recommendation: {rec_emoji} **{recommendation}**\n")
        lines.append(f"**Solar Activity (48h):** X-class: {xclass} | M-class: {mclass} | Max Kp: {kp} | Storms: {storms}\n")

        if at_risk:
            lines.append(f"**⚠ At-Risk Subsystems:** {', '.join(at_risk)}\n")

        if risk_level == 'EXTREME':
            lines.append("**🔍 PROBLEM:** Extreme solar storm is active — spacecraft is at immediate risk.")
            lines.append("\n**❓ WHY:** A major geomagnetic storm (Kp≥8) or X-class solar flare event is impacting the spacecraft's orbital environment. This causes elevated particle radiation, potential SEUs in onboard computers, and communication disruption.")
            lines.append("\n**✅ HOW TO FIX:**\n"
                         "    1. Switch spacecraft to safe mode immediately.\n"
                         "    2. Disable non-essential instruments to protect against SEUs.\n"
                         "    3. Increase radiation shielding mode.\n"
                         "    4. Suspend all EVA and launch activities.\n"
                         "    5. Monitor hourly until Kp index drops below 5.")
        elif risk_level == 'HIGH':
            lines.append("**🔍 PROBLEM:** Active solar conditions — elevated risk to spacecraft operations.")
            lines.append("\n**❓ WHY:** Significant solar activity (M/X-class flares or Kp≥5) is ongoing. This increases SEU risk, can degrade GPS accuracy, and may cause radio blackouts.")
            lines.append("\n**✅ HOW TO FIX:**\n"
                         "    1. Increase telemetry monitoring frequency.\n"
                         "    2. Delay non-critical maneuvers.\n"
                         "    3. Prepare safe-mode procedures for rapid deployment.\n"
                         "    4. Brief operations team on elevated risk.")
        elif risk_level == 'MODERATE':
            lines.append("**🔍 PROBLEM:** Mild solar activity — minor caution advised.")
            lines.append("\n**❓ WHY:** Low-level solar flares or moderate geomagnetic activity detected. Generally non-threatening but warrants attention.")
            lines.append("\n**✅ HOW TO FIX:** Monitor radiation and signal strength every 2 telemetry cycles. No operational changes required yet.")
        else:
            lines.append("**✓ PROBLEM:** None — space weather is quiet.")
            lines.append("**✓ WHY:** Solar activity is low. Kp index is below 3 and no significant flares detected.")
            lines.append("**✓ HOW TO FIX:** No action needed. Nominal operations may proceed.")
        return {'answer': '\n'.join(lines), 'source': 'SpaceGuard AI'}

    # ── Active alerts ─────────────────────────────────────────────────────
    if any(w in q for w in ['alert', 'alarm', 'warning', 'urgent', 'notifications', 'active alert']):
        if not alerts:
            answer = (
                f"✓ **No active alerts for {spacecraft}.**\n\n"
                f"**🔍 PROBLEM:** None.\n"
                f"**❓ WHY:** All subsystems have been operating within normal thresholds since the last analysis.\n"
                f"**✅ HOW TO FIX:** No action required. Continue nominal operations."
            )
        else:
            lines = [f"**🔔 Active Alerts — {spacecraft} ({len(alerts)} open)**\n"]
            for a in alerts[:5]:
                sev = a.get('severity', '?')
                sub = a.get('subsystem', '?')
                desc = a.get('description', '')
                stat = a.get('status', '')
                lines.append(f"**[{sev}] {sub}** (Status: {stat})")
                lines.append(f"  🔍 {desc[:150]}")
                lines.append("")
            lines.append("**✅ HOW TO FIX:**")
            lines.append("1. Investigate each alert in order of severity (CRITICAL → HIGH → MODERATE).")
            lines.append("2. Update alert status to INVESTIGATING while working the issue.")
            lines.append("3. Once resolved, mark as RESOLVED with a brief note.")
            answer = '\n'.join(lines)
        return {'answer': answer, 'source': 'SpaceGuard AI'}

    # ── Telemetry summary ─────────────────────────────────────────────────
    if any(w in q for w in ['telemetry', 'sensors', 'readings', 'show all', 'sensor data']):
        problems = _diagnose_all_problems()
        lines = [f"**Full Telemetry Readings — {spacecraft}**\n"]
        lines.append(f"• Temperature:       **{fv('temperature', '°C')}**  (Normal: -50 to 85°C)")
        lines.append(f"• Battery Voltage:   **{fv('battery_voltage', 'V')}**  (Normal: 22–32V)")
        lines.append(f"• Battery Current:   **{fv('battery_current', 'A')}**  (Normal: -5 to 20A)")
        lines.append(f"• Fuel Level:        **{fv('fuel_level', '%')}**  (Critical: <5%)")
        lines.append(f"• Radiation:         **{fv('radiation', ' mSv')}**  (Normal: <50 mSv)")
        lines.append(f"• Pressure:          **{fv('pressure', ' kPa')}**  (Normal: 95–110 kPa)")
        lines.append(f"• Signal Strength:   **{fv('signal_strength', ' dBm')}**  (Normal: >-120 dBm)")
        lines.append(f"• Velocity:          **{fv('velocity', ' km/s', 2)}**  (Normal: 0–30 km/s)")
        lines.append(f"• Power Consumption: **{fv('power_consumption', 'W', 0)}**  (Normal: <500W)")
        lines.append(f"\n**Health Score:** {health.get('health_score', 'N/A')}/100 | **Risk Level:** {health.get('risk_level', 'N/A')}")
        if problems:
            lines.append(f"\n**⚠ {len(problems)} sensor(s) outside normal range:**")
            for p in problems:
                lines.append(f"  • {p['status']} — {p['sensor']}: {p['value']}")
        else:
            lines.append("\n**✓ All sensor readings are within normal operating ranges.**")
        return {'answer': '\n'.join(lines), 'source': 'SpaceGuard AI'}

    # ── Default: auto-diagnose and return full report ─────────────────────
    return {'answer': _full_diagnostic_response(), 'source': 'SpaceGuard AI'}
