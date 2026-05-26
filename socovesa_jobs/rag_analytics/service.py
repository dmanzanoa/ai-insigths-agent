from __future__ import annotations

import json
from typing import Any

from .tools import execute_tool
from ..aws_clients import AwsClients
from ..bedrock_client import invoke_text
from ..config import Settings, settings
from ..json_utils import extract_json_object


VALID_LABELS = {"subsidio", "no_subsidio", "recomendador"}


def detect_label_from_question(question: str) -> str | None:
    normalized = question.lower().replace("-", " ").replace("_", " ")
    if any(term in normalized for term in ["no subsidio", "sin subsidio", "no subsidios", "sin subsidios"]):
        return "no_subsidio"
    if "recomendador" in normalized:
        return "recomendador"
    if "subsidio" in normalized or "subsidios" in normalized:
        return "subsidio"
    return None


def resolve_label(body: dict[str, Any], question: str) -> dict[str, str | None]:
    detected_label = detect_label_from_question(question)
    ui_label = body.get("label")
    conversation_label = body.get("conversation_label")

    if detected_label:
        label = detected_label
        source = "question"
    elif ui_label in VALID_LABELS:
        label = ui_label
        source = "ui"
    elif conversation_label in VALID_LABELS:
        label = conversation_label
        source = "conversation"
    elif ui_label == "all":
        label = "all"
        source = "ui_all"
    else:
        label = "all"
        source = "fallback_all"

    return {
        "label": label,
        "detected_label": detected_label,
        "label_source": source,
    }


class AnalyticsRagService:
    def __init__(self, clients: AwsClients, cfg: Settings = settings):
        self.clients = clients
        self.cfg = cfg

    def answer(self, body: dict[str, Any]) -> dict[str, Any]:
        question = str(body.get("question", "")).strip()
        if not question:
            raise ValueError("Missing required field: question")

        resolved = resolve_label(body, question)
        label = str(resolved["label"])
        chunks = self.retrieve_context(question, label, top_k=int(body.get("top_k", 8)))
        retrieved_context = self.format_context(chunks)
        tool_decision = self.decide_tool(question, label)
        visualization = execute_tool(self.clients, tool_decision, chunks)
        answer = self.generate_answer(
            question=question,
            label=label,
            label_source=str(resolved["label_source"]),
            tool_decision=tool_decision,
            visualization=visualization,
            retrieved_context=retrieved_context,
        )

        return {
            "answer": answer,
            "label_used": label,
            "label_detected": resolved["detected_label"],
            "label_source": resolved["label_source"],
            "tool_used": tool_decision,
            "visualization": visualization,
            "retrieved_chunks": chunks,
        }

    def build_retrieval_query(self, question: str, label: str) -> str:
        if label == "all":
            return f"""
Pregunta general sobre todos los labels.

Considera informacion de:
- subsidio
- no_subsidio
- recomendador

Pregunta del usuario:
{question}
""".strip()

        return f"""
label: {label}

Pregunta del usuario:
{question}
""".strip()

    def datasource_prefix_for_label(self, label: str) -> str:
        if label == "all":
            return f"{self.cfg.snapshot_prefix}/"
        return f"{self.cfg.snapshot_prefix}/{label}/"

    def retrieve_context(self, question: str, label: str, top_k: int = 8) -> list[dict[str, Any]]:
        if not self.cfg.analytics_kb_id:
            raise ValueError("Missing KB_ID or BEDROCK_KB_ID environment variable")

        response = self.clients.bedrock_agent_runtime.retrieve(
            knowledgeBaseId=self.cfg.analytics_kb_id,
            retrievalQuery={"text": self.build_retrieval_query(question, label)},
            retrievalConfiguration={
                "vectorSearchConfiguration": {
                    "numberOfResults": top_k * 10,
                }
            },
        )

        datasource_prefix = self.datasource_prefix_for_label(label)
        chunks: list[dict[str, Any]] = []
        for item in response.get("retrievalResults", []):
            location = item.get("location", {})
            location_text = json.dumps(location, ensure_ascii=False)
            if datasource_prefix not in location_text:
                continue

            chunks.append(
                {
                    "score": item.get("score"),
                    "text": item.get("content", {}).get("text", ""),
                    "location": location,
                    "metadata": item.get("metadata", {}),
                }
            )
            if len(chunks) >= top_k:
                break
        return chunks

    def format_context(self, chunks: list[dict[str, Any]]) -> str:
        if not chunks:
            return "No se encontro contexto historico relevante en la base de conocimiento."

        parts = []
        for i, chunk in enumerate(chunks, 1):
            parts.append(
                f"""
[CONTEXT_{i}]
score: {chunk.get("score")}
location: {json.dumps(chunk.get("location", {}), ensure_ascii=False)}
metadata: {json.dumps(chunk.get("metadata", {}), ensure_ascii=False)}

{chunk.get("text", "")}
"""
            )
        return "\n\n".join(parts)

    def decide_tool(self, question: str, label: str) -> dict[str, Any]:
        prompt = f"""
Eres un agente analitico inmobiliario. Debes elegir UNA herramienta.

TOOLS DISPONIBLES:

1. get_category_distribution
- Usar para distribucion, composicion, porcentaje por categoria, intencion de compra, pain points, sentimiento, funnel.

2. get_weekly_metric_trend
- Usar para tendencia, evolucion, grafico de linea, cambios semanales o mensuales.

3. generate_executive_report
- Usar para resumen, diagnostico, informe o pregunta general.

VALID_METRICS:
- intencion_compra
- pain_points
- sentimiento
- funnel
- conversion
- financiamiento
- segmentos_cliente
- topicos_consulta
- atributos_valorados
- demandas_no_cubiertas

QUESTION:
{question}

LABEL:
{label}

Devuelve SOLO JSON valido:
{{
  "tool": "get_category_distribution | get_weekly_metric_trend | generate_executive_report",
  "metric": "string",
  "chart_type": "bar_chart | line_chart | pie_chart | table | none",
  "reason": "string"
}}
"""
        try:
            text = invoke_text(
                self.clients,
                self.cfg.model_main,
                prompt,
                max_tokens=1000,
                temperature=0.0,
            )
            return extract_json_object(text)
        except Exception:
            return {
                "tool": "generate_executive_report",
                "metric": "general",
                "chart_type": "none",
                "reason": "Tool decision parse failed",
            }

    def generate_answer(
        self,
        *,
        question: str,
        label: str,
        label_source: str,
        tool_decision: dict[str, Any],
        visualization: dict[str, Any],
        retrieved_context: str,
    ) -> str:
        prompt = f"""
Eres un analista senior de inteligencia comercial inmobiliaria.

Debes responder usando SOLO el CONTEXTO_RECUPERADO y, si existe, la VISUALIZACION_CALCULADA.
Si el contexto no contiene informacion suficiente, dilo claramente.

No cites frases textuales de clientes salvo que aparezcan literalmente en CONTEXTO_RECUPERADO.
Si el contexto contiene solo snapshots agregados, responde solo con metricas agregadas.

REGLAS:
- No inventes metricas.
- No inventes semanas.
- No inventes proyectos, marcas ni segmentos.
- Si comparas semanas, usa solo semanas presentes en el contexto.
- Si detectas tendencias, explica que evidencia del contexto la respalda.
- Si el contexto contiene porcentajes en formato decimal, conviertelos multiplicando por 100.
- No aproximes porcentajes salvo que digas explicitamente "aprox.".
- Si sumas categorias, muestra la suma exacta.
- Usa maximo 2 decimales en porcentajes.
- Responde en espanol.
- Se claro, ejecutivo y accionable.

LABEL_USADO:
{label}

ORIGEN_DEL_LABEL:
{label_source}

TOOL_DECISION:
{json.dumps(tool_decision, ensure_ascii=False)}

VISUALIZACION_CALCULADA:
{json.dumps(visualization, ensure_ascii=False, indent=2)}

PREGUNTA_USUARIO:
{question}

CONTEXTO_RECUPERADO:
{retrieved_context}

RESPUESTA:
"""
        return invoke_text(
            self.clients,
            self.cfg.model_main,
            prompt,
            max_tokens=2500,
            temperature=0.2,
        )

