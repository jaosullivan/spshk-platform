# Skills Manifest: AI Capability Matrix for SPSHK Engineering

To successfully build and support the St Patrick’s Society Hong Kong platform, the executing AI agent must possess and strictly apply the following specialized capabilities:

## 1. Advanced Django Architect Capabilities
- **Distributed Architecture Design:** Proficient in designing stateless Django architectures that offload static assets, media storage (via S3/R2), cache pipelines, and session management to external infrastructure layers.
- **Advanced ORM Optimization:** Expert in constructing zero-allocation database queries utilizing `.select_related()`, `.prefetch_related()`, and `.select_for_update()` to prevent deadlocks and race conditions in high-traffic ticket rushes.
- **Custom Event Signal Pipelines:** Capable of designing decoupled event-driven systems using Django signals linked to asynchronous task brokers (Celery) to prevent blocking web worker processes.

## 2. Cloud-Native & Kubernetes Engineering Capabilities
- **Multi-Stage Container Image Design:** Expert in multi-stage Docker builds utilizing minimal runtime distributions (`python:-slim`) that decouple compiler dependencies (`gcc`, `libpq-dev`) from the final runtime image layer.
- **Declarative GitOps Strategy Execution:** Deep knowledge of Argo CD synchronization lifecycles, configuration drift detection, self-healing sync options, and declarative Kustomize overlay structures.
- **SRE & Application Observability Design:** Capable of instrumenting applications natively with OpenTelemetry tracers and exposing structured metric feeds compatible with Prometheus `ServiceMonitor` collection standards.

## 3. High-Security Payment Gateway Operations Capabilities
- **Secure Transaction Handling:** Expert in Stripe API patterns, specifically converting floating-point values into localized integer cents, error routing, and cryptographic signature matching for webhooks.
- **Cryptographic Asset Pipelines:** Capable of transforming internal secure object IDs (UUIDv4) into highly scannable QR byte matrices embedded directly into external streaming object streams.

## 4. Regional Regulatory & Data Privacy Compliance Capabilities
- **Hong Kong PDPO Legal Standards:** Proficient in data localization, secure storage practices, and creating programmatic data destruction models (anonymization/soft deletion workflows) required under the Hong Kong Personal Data (Privacy) Ordinance.
