# Security policy

## Reporting

Please report vulnerabilities privately to the repository owner instead of opening a public issue.
Include the affected component, reproduction steps, and potential impact.

## Demo boundaries

AtlasAgent is a portfolio project, not a production authorization service. Its local HMAC token
helper demonstrates an approval invariant; production deployments should use short-lived,
identity-bound approvals, a managed secret store, rate limits, and an external audit sink.

Retrieved documents are untrusted input. A production RAG deployment also needs prompt-injection
screening, document-level access control, output monitoring, and tenant isolation.

Never commit API keys or real customer data. The sample customer, order, and policy records are
fictional. Rotate `ATLAS_APPROVAL_SECRET` before exposing the API outside a local environment.
