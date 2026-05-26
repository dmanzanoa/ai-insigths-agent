from __future__ import annotations


COMPRESS_SCHEMA_SPEC: dict[str, set[str] | None] = {
    "sentimiento_promedio": {"positivo", "neutral", "negativo"},
    "pain_point_del_cliente": {"financiamiento", "ingresos", "ahorro", "requisitos", "disponibilidad", "subsidios", "desconocido"},
    "perfil_del_cliente": {"primerizos", "compradores", "inversores", "habitantes", "indefinidos", "desconocido"},
    "situacion_laboral": {"dependientes", "independientes", "informales", "desconocidos"},
    "ingreso": {"bajos", "medios", "medioaltos", "altos", "desconocido"},
    "abandono": {"si", "no"},
    "motivo_abandono": {"precio", "subsidio", "requisitos", "desconfianza", "silencio", "desconocido"},
    "solucion_bot": {"informacion", "recomendacion", "financiamiento", "simulacion", "subsidios", "derivacion", "otro", "desconocido"},
    "friccion_bot": {"baja", "media", "alta"},
    "topicos_consulta": {"subsidios", "financiamiento", "propiedades", "proyectos", "precios", "caracteristicas", "requisitos", "reclamo", "otro"},
    "tipo_consulta": {"informativa", "comparativa", "financiera", "documental", "cierre"},
    "atributo_valorado": {"precio", "ubicacion", "espacio", "financiamiento", "flexibilidad", "asesoria", "subsidios", "desconocido"},
    "topico_valorado": {"ubicacion", "propiedad", "proyecto", "precio", "financiamiento", "subsidios", "desconocido"},
    "etapa_funnel": {"descubrimiento", "evaluacion", "decision", "cierre", "abandono"},
    "intencion_compra": {"baja", "media", "alta", "desconocido"},
    "capacidad_info": {"alta", "media", "baja"},
    "derivado_vendedor": {"si", "no", "desconocido"},
    "sin_pie": {"si", "no", "desconocido"},
    "proyecto_mencionado": {"si", "no", "desconocido"},
    "producto_origen": None,
    "producto_destino": None,
    "respuesta_recomendador": {"si", "no", "desconocido"},
    "demanda_no_cubierta": {"precio", "stock", "ubicacion", "financiamiento", "subsidio", "requisitos", "ninguna", "desconocido"},
    "info_complementaria": {"ggcc", "referencias_geograficas", "conectividad", "documentacion", "entrega", "ninguna", "desconocido"},
    "duda_recurrente": None,
}


INSIGHT_COLUMNS = {
    "clientId": "clientId",
    "createdAt": "createdAt",
    "subProjectInfo": "subProjectInfo",
    "Marca": "Marca",
    "sentimiento": "sentimiento_promedio",
    "pain_point": "pain_point_del_cliente",
    "perfil_cliente": "perfil_del_cliente",
    "situacion_laboral": "situacion_laboral",
    "ingreso": "ingreso",
    "abandono": "abandono",
    "motivo_abandono": "motivo_abandono",
    "solucion_bot": "solucion_bot",
    "topicos_consulta": "topicos_consulta",
    "tipo_consulta": "tipo_consulta",
    "atributo_valorado": "atributo_valorado",
    "topico_valorado": "topico_valorado",
    "etapa_funnel": "etapa_funnel",
    "intencion_compra": "intencion_compra",
    "capacidad_info": "capacidad_info",
    "friccion_bot": "friccion_bot",
    "derivado_vendedor": "derivado_vendedor",
    "sin_pie": "sin_pie",
    "producto_origen": "producto_origen",
    "producto_destino": "producto_destino",
    "respuesta_recomendador": "respuesta_recomendador",
    "demanda_no_cubierta": "demanda_no_cubierta",
    "info_complementaria": "info_complementaria",
    "proyecto_mencionado": "proyecto_mencionado",
    "duda_recurrente": "duda_recurrente",
}


def default_summary() -> dict[str, str]:
    return {field: "desconocido" for field in COMPRESS_SCHEMA_SPEC}

