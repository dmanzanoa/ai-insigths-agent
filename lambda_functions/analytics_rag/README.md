# Analytics RAG Lambda

Lambda handler:

```text
lambda_functions.analytics_rag.lambda_function.lambda_handler
```

This adapter is intentionally thin. The reusable RAG logic lives in:

```text
socovesa_jobs/rag_analytics/
```

Required environment variables:

- `AWS_REGION`
- `KB_ID` or `BEDROCK_KB_ID`
- `MODEL_ID` or `MODEL_MAIN`
- `OUTPUT_BUCKET`

The Lambda must be packaged with the `socovesa_jobs` package and dependencies from the root `requirements.txt`.
