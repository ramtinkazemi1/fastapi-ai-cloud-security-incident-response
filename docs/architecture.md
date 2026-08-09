# Architecture and engineering decisions

## System boundary

The service accepts normalized alerts or supported subsets of AWS GuardDuty
and Wazuh payloads. It persists vendor-neutral records, groups alerts into
incidents, records an audit trail, and can queue optional AI triage.

It does not poll AWS accounts, execute remediation, or replace a SIEM. Keeping
those responsibilities outside the API makes security boundaries and failure
modes explicit.

## Request lifecycle

1. FastAPI assigns or validates an `X-Request-ID`.
2. Authentication accepts a machine API key or a user JWT.
3. Pydantic rejects malformed, extra, or out-of-range input.
4. A route invokes normalization, repository, or AI services.
5. FastAPI injects one `AsyncSession` for the request.
6. The repository commits a transaction and refreshes server-generated fields.
7. A response schema serializes the ORM object.
8. The session closes and its connection returns to the pool.

Routes translate domain and provider failures into stable HTTP responses:

- `401` for failed authentication
- `403` when a role cannot perform an action
- `404` for unknown resource UUIDs
- `409` for duplicate `(source, external_id)` values
- `429` when the local request window is exceeded
- `422` for request validation failures

## Data model

`alerts` stores:

- provider identity: `source`, `external_id`;
- finding content: title, description, severity, occurrence time;
- cloud context: account, region, and resource;
- workflow state: new, investigating, resolved, or dismissed;
- optional AI summary, recommendation, and analysis time; and
- UUID and audit timestamps.

The unique `(source, external_id)` constraint provides idempotency for provider
retries. Database check constraints preserve severity and status invariants
even when writes do not originate through FastAPI.

`users` stores Argon2 password hashes and analyst/admin roles. `incidents`
groups alerts through `alerts.incident_id`. `audit_events` is append-only at
the API layer. `analysis_jobs` exposes queued, running, completed, and failed
background work.

## Async persistence

SQLAlchemy's `AsyncSession` is request-scoped. Repository functions own normal
transaction completion and rollback after uniqueness errors. `expire_on_commit`
is disabled so response serialization does not trigger implicit asynchronous
database access after a successful commit.

List queries issue one count query and one bounded page query. Ordering by
occurrence time and UUID makes page results deterministic.

## Provider normalization

GuardDuty uses AWS camelCase aliases, while Wazuh maps nested rule and agent
metadata. Each normalizer maps only fields used by this application and
ignores unsupported provider metadata. A new provider needs only a provider
schema and a transformer into `AlertCreate`.

## AI boundary

AI analysis is isolated in an adapter and is never required for core alert
processing. Alert content is untrusted and may contain prompt-injection text,
so the system instruction explicitly identifies it as data. Provider output is
accepted only when it is valid JSON containing non-empty expected fields.

Retries are limited to transient failures. Authentication and other client
errors fail immediately. The API never returns the provider's response body,
which may contain operational details.

FastAPI `BackgroundTasks` runs analysis after the `202` response. The job uses
a new session and always records a completed or failed state. This is clear
and sufficient for one demo process; a distributed deployment needs a durable
queue.

## Testing strategy

- Schema tests verify validation boundaries and provider aliases.
- API tests exercise users and roles, persistence, conflicts, filtering,
  incidents, audit history, GuardDuty/Wazuh ingestion, jobs, and stored AI
  output.
- AI behavior is replaced with a deterministic test double; CI does not call
  paid external services.
- Endpoint tests use an isolated SQLite database for speed.
- CI starts PostgreSQL and applies all migrations to catch dialect-specific
  schema failures.

## Deliberate tradeoffs

- A machine API key keeps provider integration simple; local users and JWTs
  demonstrate role authorization without requiring an external identity
  provider.
- Offset pagination is understandable and sufficient for this project. A
  high-volume event store should use cursor pagination.
- Background jobs and rate limits are process-local. Production replicas
  should use a queue and Redis or an API gateway.
- Current status plus audit events is easy to study. A regulated environment
  should enforce append-only audit storage outside the application database.
