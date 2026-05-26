from __future__ import annotations

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from .config import PROMPTS_DIR


prompt_env = Environment(
    loader=FileSystemLoader(PROMPTS_DIR),
    undefined=StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
)


def render_prompt(template_name: str, **kwargs) -> str:
    template = prompt_env.get_template(template_name)
    return template.render(**kwargs)


def insight_template_for_label(label: str) -> str:
    return "recomendador.j2" if label == "recomendador" else "lidz.j2"

