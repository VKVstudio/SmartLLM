The user wants a production-grade TypeScript module `form_handler.ts` with specific exports, interfaces, and functions. Let me carefully implement all requirements:

1. `ProjectTier` type
2. `FormSubmissionInput` interface
3. `ValidationIssue` interface
4. `ValidatedSubmission` interface
5. `ApiResponse<T>` interface
6. `HandlerConfig` interface
7. `buildSecurityHeaders` function
8. `generateCsrfToken` function
9. `verifyCsrfToken` function
10. `sanitizeHtmlText` function
11. `FormApiHandler` class with `handleRequest` method

Key constraints:
- Zero `any` types
- `tsc --noEmit --strict --target ES2022`
- Only `node:crypto` allowed
- Must start with `FILE: form_handler.ts`
- Single fenced `typescript` code block
- No prose outside the block

Let me implement this carefully:

For the CSRF token:
- `generateCsrfToken`: HMAC-SHA256 hex digest of `${sessionId}:${timestampMs}` under secret
- `verifyCsrfToken`: parse token, verify timestamp constraints, recompute HMAC, use `timingSafeEqual`

For the rate limiter:
- Sliding window: track requests per IP within the window
- Use `nowFn()` for time

For validation:
- fullName: trimmed length 2..120, Unicode letters (Latin or Cyrillic), spaces, hyphens, periods
- workEmail: trimmed length 5..254, valid local@domain.tld format
- company: trimmed length 2..120
- projectTier: must be one of the three values
- budgetUsd: Number.isFinite, 1000 <= budgetUsd <= 10_000_000
- message: trimmed length 10..4000

For sanitization:
- Strip ASCII control chars
- Normalize whitespace
- Escape &, <, >, ", '

Let me write this now.