# Official Meta/Instagram Publishing Path

## Supported route

Creator Ops uses the official Instagram API with Instagram Login as the default
route. It targets professional Instagram Creator/Business accounts through
`graph.instagram.com`. The adapter requires the current business scopes
`instagram_business_basic` and `instagram_business_content_publish`, plus a
publicly reachable JPEG for every carousel item.

The Facebook Login route remains a documented fallback for accounts linked to a
Facebook Page. It uses `graph.facebook.com` and its own Meta permission set; it
must not be mixed with the Instagram-Login token or host.

## Local gates

The adapter is fail-closed until all of these are true:

- Persona-to-account mapping matches the expected Instagram handle.
- The selected content is owner-approved, SFW and `PUBLIC_SFW`.
- Exactly three unpublished top-pick assets are selected for the proof carousel.
- Each manifest URL is HTTPS, public, returns `image/jpeg`, and has JPEG magic.
- Native AI disclosure is confirmed in the package metadata.
- Graph identity and content-publishing quota pass read-only preflight.
- A separate per-content live gate is present immediately before dispatch.

The local preflight command is read-only and never creates a Graph media
container or changes the database:

```text
python -m creator_ops.cli --db data/review_dashboard.db --config config.toml \
  meta-preflight --publication-id 8 --content-id 1
```

## Proof status

As of 7 September 2026 the code path and local tests are green, but
`META_GRAPH_AUTOMATION_PROOF` remains `not_yet_proven` because the owner has
not completed the Meta developer/account credential gate in this workspace.
The temporary public JPEG URLs used for local preflight are suitable for a
one-off proof only, not for production hosting.

## Post-proof evidence

When the owner gate is complete, record only non-secret evidence: Graph media
ID, Instagram permalink, confirmed local publication/queue status, receipt
filename, and sanitized error/retry outcomes. Never record access tokens,
cookies, OTPs or private URLs containing credentials.
