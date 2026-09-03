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
    Rule-based AI agent that reads real telemetry, health, anomaly and alert
    data from context and composes natural-language answers.
    Returns structured answer and source label.
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

    # Helper: format a sensor value cleanly
    def val(key, unit='', decimals=1):
        v = tel.get(key)
        if v is None:
            return 'Not available'
        return f'{round(float(v), decimals)}{unit}'

    # ── Health / status queries ────────────────────────────────────────────
    if any(w in q for w in ['health', 'status', 'overall', 'condition', 'how is', 'how are']):
        score = health.get('health_score', 'N/A')
        level = health.get('risk_level', 'N/A')
        category = health.get('health_category', 'N/A')
        breakdown = health.get('score_breakdown', {})
        bd_parts = []
        if breakdown.get('anomaly_severity', 0) < 0:
            bd_parts.append(f"anomaly severity penalty: {breakdown['anomaly_severity']} pts")
        if breakdown.get('threshold_violations', 0) < 0:
            bd_parts.append(f"threshold violations: {breakdown['threshold_violations']} pts")
        bd_str = '; '.join(bd_parts) if bd_parts else 'no deductions applied'
        answer = (
            f"**{spacecraft} — Health Report**\n\n"
            f"• Health Score: **{score}/100** ({category})\n"
            f"• Risk Level: **{level}**\n"
            f"• Mission Status: {status}\n"
            f"• Score Breakdown: {bd_str}\n\n"
        )
        if level in ('HIGH', 'CRITICAL'):
            answer += f"⚠ Action needed: {explanation.get('recommended_action', 'Review mission protocols.')}"
        else:
            answer += "✓ Systems are within acceptable operating parameters."
        return {'answer': answer, 'source': 'SpaceGuard AI (Local Agent)'}

    # ── Anomaly queries ────────────────────────────────────────────────────
    if any(w in q for w in ['anomaly', 'anomalies', 'problem', 'issue', 'fault', 'detected']):
        is_anom = anomaly.get('is_anomaly', False)
        severity = anomaly.get('severity', 'NORMAL')
        subsystem = anomaly.get('affected_subsystem', 'UNKNOWN')
        params = anomaly.get('suspicious_parameters', [])
        score = anomaly.get('anomaly_score', 0)
        if not is_anom and severity == 'NORMAL':
            answer = (
                f"✓ **No anomaly detected** on {spacecraft}.\n\n"
                f"• Anomaly Score: {score} (low = normal)\n"
                f"• All monitored parameters are within operating thresholds.\n"
                f"• Continue nominal operations."
            )
        else:
            params_str = ', '.join(params) if params else 'none identified'
            problem = explanation.get('detected_problem', 'Anomalous sensor readings detected.')
            cause = explanation.get('possible_cause', 'Under investigation.')
            action = explanation.get('recommended_action', 'Consult mission protocols.')
            answer = (
                f"⚠ **Anomaly Detected — {severity}**\n\n"
                f"• Affected Subsystem: **{subsystem}**\n"
                f"• Anomaly Score: {score}\n"
                f"• Suspicious Parameters: {params_str}\n"
                f"• Problem: {problem}\n"
                f"• Possible Cause: {cause}\n"
                f"• Recommended Action: {action}"
            )
        return {'answer': answer, 'source': 'SpaceGuard AI (Local Agent)'}

    # ── Temperature queries ────────────────────────────────────────────────
    if any(w in q for w in ['temperature', 'temp', 'thermal', 'heat', 'hot', 'cold']):
        t = tel.get('temperature')
        if t is None:
            return {'answer': 'Temperature data is not currently available.', 'source': 'SpaceGuard AI (Local Agent)'}
        t = float(t)
        status_str = '✓ Normal' if -50 <= t <= 85 else ('⚠ Warning' if t <= 100 else '🔴 Critical')
        answer = (
            f"**Thermal Subsystem — {spacecraft}**\n\n"
            f"• Current Temperature: **{round(t,1)}°C**\n"
            f"• Status: {status_str}\n"
            f"• Normal Range: -50°C to 85°C | Critical: >100°C\n"
        )
        if t > 85:
            answer += "\n⚠ Temperature is above the warning threshold. Monitor closely and consider thermal management procedures."
        elif t > 100:
            answer += "\n🔴 CRITICAL: Temperature exceeds safe limit. Immediate thermal management required."
        else:
            answer += "\n✓ Thermal conditions are nominal."
        return {'answer': answer, 'source': 'SpaceGuard AI (Local Agent)'}

    # ── Battery / power queries ────────────────────────────────────────────
    if any(w in q for w in ['battery', 'voltage', 'power', 'electrical', 'current', 'watt']):
        bv = tel.get('battery_voltage')
        bc = tel.get('battery_current')
        pc = tel.get('power_consumption')
        answer = (
            f"**Electrical Subsystem — {spacecraft}**\n\n"
            f"• Battery Voltage: **{val('battery_voltage', 'V')}**  (Normal: 22–32V | Critical: <18V)\n"
            f"• Battery Current: **{val('battery_current', 'A')}**  (Normal: -5 to 20A)\n"
            f"• Power Consumption: **{val('power_consumption', 'W', 0)}**  (Normal: <500W | Critical: >600W)\n"
        )
        warnings = []
        if bv is not None and float(bv) < 22:
            warnings.append(f"⚠ Battery voltage {round(float(bv),1)}V is below the 22V warning threshold.")
        if bv is not None and float(bv) < 18:
            warnings.append("🔴 CRITICAL: Battery voltage below 18V. Immediate action required.")
        if pc is not None and float(pc) > 500:
            warnings.append(f"⚠ Power consumption {round(float(pc),0)}W exceeds 500W warning threshold.")
        answer += '\n' + '\n'.join(warnings) if warnings else '\n✓ Electrical systems are nominal.'
        return {'answer': answer, 'source': 'SpaceGuard AI (Local Agent)'}

    # ── Fuel queries ──────────────────────────────────────────────────────
    if any(w in q for w in ['fuel', 'propulsion', 'propellant', 'thruster']):
        f = tel.get('fuel_level')
        if f is None:
            return {'answer': 'Fuel level data is not available.', 'source': 'SpaceGuard AI (Local Agent)'}
        f = float(f)
        status_str = '🔴 Critical' if f < 5 else ('⚠ Warning' if f < 20 else '✓ Normal')
        answer = (
            f"**Propulsion Subsystem — {spacecraft}**\n\n"
            f"• Fuel Level: **{round(f,1)}%**\n"
            f"• Status: {status_str}\n"
            f"• Warning threshold: <20% | Critical: <5%\n"
        )
        if f < 5:
            answer += "\n🔴 CRITICAL: Fuel level is critically low. Emergency protocols may apply."
        elif f < 20:
            answer += "\n⚠ Fuel is below 20%. Plan resupply or mission duration adjustment."
        else:
            answer += "\n✓ Fuel reserves are adequate for continued operations."
        return {'answer': answer, 'source': 'SpaceGuard AI (Local Agent)'}

    # ── Signal / communication queries ────────────────────────────────────
    if any(w in q for w in ['signal', 'communication', 'comm', 'contact', 'radio', 'link']):
        ss = tel.get('signal_strength')
        if ss is None:
            return {'answer': 'Signal strength data is not available.', 'source': 'SpaceGuard AI (Local Agent)'}
        ss = float(ss)
        status_str = '🔴 Critical' if ss < -130 else ('⚠ Weak' if ss < -120 else '✓ Normal')
        answer = (
            f"**Communication Subsystem — {spacecraft}**\n\n"
            f"• Signal Strength: **{round(ss,1)} dBm**\n"
            f"• Status: {status_str}\n"
            f"• Normal: >-120 dBm | Critical: <-130 dBm\n"
        )
        if ss < -130:
            answer += "\n🔴 CRITICAL: Signal below safe limit. Communication link may be compromised."
        elif ss < -120:
            answer += "\n⚠ Signal is weak. Monitor for communication disruptions."
        else:
            answer += "\n✓ Communication link is strong."
        return {'answer': answer, 'source': 'SpaceGuard AI (Local Agent)'}

    # ── Radiation queries ─────────────────────────────────────────────────
    if any(w in q for w in ['radiation', 'rad', 'particle', 'cosmic', 'dose']):
        r = tel.get('radiation')
        if r is None:
            return {'answer': 'Radiation data is not available.', 'source': 'SpaceGuard AI (Local Agent)'}
        r = float(r)
        status_str = '🔴 Critical' if r > 100 else ('⚠ Elevated' if r > 50 else '✓ Normal')
        answer = (
            f"**Radiation Monitor — {spacecraft}**\n\n"
            f"• Radiation Level: **{round(r,1)} mSv**\n"
            f"• Status: {status_str}\n"
            f"• Normal: <50 mSv | Critical: >100 mSv\n"
        )
        if r > 100:
            answer += "\n🔴 CRITICAL: Radiation level exceeds safe limit. Review shielding and orbital position."
        elif r > 50:
            answer += "\n⚠ Elevated radiation. Monitor cumulative exposure and solar activity."
        else:
            answer += "\n✓ Radiation levels are within safe operational limits."
        return {'answer': answer, 'source': 'SpaceGuard AI (Local Agent)'}

    # ── Velocity / navigation queries ─────────────────────────────────────
    if any(w in q for w in ['velocity', 'speed', 'navigation', 'orbit', 'altitude']):
        answer = (
            f"**Navigation — {spacecraft}**\n\n"
            f"• Velocity: **{val('velocity', ' km/s', 2)}**  (Normal: 0–30 km/s | Critical: >35 km/s)\n"
        )
        v = tel.get('velocity')
        if v and float(v) > 30:
            answer += f"\n⚠ Velocity {round(float(v),2)} km/s is above the 30 km/s warning threshold."
        else:
            answer += "\n✓ Velocity is within nominal range."
        return {'answer': answer, 'source': 'SpaceGuard AI (Local Agent)'}

    # ── Pressure / environmental queries ──────────────────────────────────
    if any(w in q for w in ['pressure', 'environmental', 'atmosphere', 'hull']):
        answer = (
            f"**Environmental — {spacecraft}**\n\n"
            f"• Pressure: **{val('pressure', ' kPa')}**  (Normal: 95–110 kPa | Critical: >120 or <90 kPa)\n"
        )
        p = tel.get('pressure')
        if p and (float(p) > 110 or float(p) < 95):
            answer += f"\n⚠ Pressure {round(float(p),1)} kPa is outside the normal range."
        else:
            answer += "\n✓ Pressure is within nominal operating range."
        return {'answer': answer, 'source': 'SpaceGuard AI (Local Agent)'}

    # ── Space weather queries ─────────────────────────────────────────────
    if any(w in q for w in ['space weather', 'solar', 'flare', 'geomagnetic', 'radiation risk',
                              'kp index', 'kp-index', 'weather', 'launch risk', 'storm']):
        if not sw:
            return {'answer': 'Space weather data is not currently available.', 'source': 'SpaceGuard AI (Local Agent)'}
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
        answer = (
            f"**Space Weather Report — {spacecraft}**\n\n"
            f"• Date: {date_str}\n"
            f"• Risk Score: **{risk_score}/100**\n"
            f"• Risk Level: **{risk_level}**\n"
            f"• Launch Recommendation: {rec_emoji} **{recommendation}**\n\n"
            f"**Solar Activity (48h):**\n"
            f"• X-class Flares: {xclass}\n"
            f"• M-class Flares: {mclass}\n"
            f"• Max Kp-Index: {kp}\n"
            f"• Significant Storms (Kp≥5): {storms}\n"
        )
        if at_risk:
            answer += f"\n⚠ **At-risk subsystems:** {', '.join(at_risk)}\n"
            answer += f"Monitor these sensors closely during elevated space weather conditions.\n"
        if risk_level == 'LOW':
            answer += "\n✓ Space weather conditions are quiet. Nominal operations may proceed."
        elif risk_level == 'MODERATE':
            answer += "\n⚠ Mild solar activity. Increase telemetry polling frequency and monitor radiation."
        elif risk_level == 'HIGH':
            answer += "\n⏳ Active solar conditions. Delay non-critical operations. Prepare safe-mode procedures."
        else:
            answer += "\n🛑 EXTREME solar storm. Switch to safe mode immediately. No launches."
        return {'answer': answer, 'source': 'SpaceGuard AI (Local Agent)'}

    # ── Alert queries ─────────────────────────────────────────────────────
    if any(w in q for w in ['alert', 'alarm', 'warning', 'critical', 'urgent']):
        if not alerts:
            answer = f"✓ **No active alerts** for {spacecraft}.\n\nAll monitored subsystems are operating within normal parameters."
        else:
            lines = [f"⚠ **{len(alerts)} Active Alert(s)** for {spacecraft}:\n"]
            for a in alerts[:5]:
                lines.append(f"• [{a.get('severity','?')}] {a.get('subsystem','?')} — {a.get('description','')[:100]}")
            answer = '\n'.join(lines)
        return {'answer': answer, 'source': 'SpaceGuard AI (Local Agent)'}

    # ── Telemetry summary queries ─────────────────────────────────────────
    if any(w in q for w in ['telemetry', 'sensors', 'readings', 'data', 'all', 'summary', 'report']):
        answer = (
            f"**Full Telemetry Summary — {spacecraft}**\n\n"
            f"• Temperature:       {val('temperature', '°C')}\n"
            f"• Battery Voltage:   {val('battery_voltage', 'V')}\n"
            f"• Battery Current:   {val('battery_current', 'A')}\n"
            f"• Fuel Level:        {val('fuel_level', '%')}\n"
            f"• Radiation:         {val('radiation', ' mSv')}\n"
            f"• Pressure:          {val('pressure', ' kPa')}\n"
            f"• Signal Strength:   {val('signal_strength', ' dBm')}\n"
            f"• Velocity:          {val('velocity', ' km/s', 2)}\n"
            f"• Power Consumption: {val('power_consumption', 'W', 0)}\n\n"
            f"Health Score: {health.get('health_score', 'N/A')}/100 | "
            f"Risk Level: {health.get('risk_level', 'N/A')}"
        )
        return {'answer': answer, 'source': 'SpaceGuard AI (Local Agent)'}

    # ── Mission / spacecraft info ─────────────────────────────────────────
    if any(w in q for w in ['mission', 'spacecraft', 'name', 'who', 'what']):
        answer = (
            f"**Mission: {mission}**\n\n"
            f"• Spacecraft: {spacecraft}\n"
            f"• Status: {status}\n"
            f"• Active Alerts: {len(alerts)}\n"
            f"• Health Score: {health.get('health_score', 'N/A')}/100\n\n"
            f"Ask me about temperature, battery, fuel, radiation, signal, anomalies, or any subsystem."
        )
        return {'answer': answer, 'source': 'SpaceGuard AI (Local Agent)'}

    # ── Help / capabilities ───────────────────────────────────────────────
    if any(w in q for w in ['help', 'can you', 'what can', 'capabilities', 'commands']):
        answer = (
            f"**SpaceGuard AI — Mission Assistant**\n\n"
            f"I can answer questions about {spacecraft} using live telemetry data. Try asking:\n\n"
            f"• 'What is the health status?'\n"
            f"• 'Are there any anomalies?'\n"
            f"• 'What is the temperature?'\n"
            f"• 'Show battery and power status'\n"
            f"• 'What is the fuel level?'\n"
            f"• 'Check signal strength'\n"
            f"• 'Show all telemetry readings'\n"
            f"• 'Are there any active alerts?'\n"
            f"• 'What is the radiation level?'"
        )
        return {'answer': answer, 'source': 'SpaceGuard AI (Local Agent)'}

    # ── Default: show current readings + context ──────────────────────────
    score = health.get('health_score', 'N/A')
    level = health.get('risk_level', 'N/A')
    severity = anomaly.get('severity', 'NORMAL')
    answer = (
        f"Based on current telemetry for **{spacecraft}**:\n\n"
        f"• Health Score: {score}/100 | Risk: {level}\n"
        f"• Anomaly Status: {severity}\n"
        f"• Temperature: {val('temperature', '°C')} | "
        f"Battery: {val('battery_voltage', 'V')} | "
        f"Fuel: {val('fuel_level', '%')}\n\n"
        f"Could you be more specific? Ask about a subsystem (temperature, battery, fuel, "
        f"radiation, signal, pressure, velocity) or say 'show all telemetry'."
    )
    return {'answer': answer, 'source': 'SpaceGuard AI (Local Agent)'}
