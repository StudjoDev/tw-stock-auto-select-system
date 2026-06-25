# Deployment Notes

## Recommended v1 Hosting

- Frontend: Vercel or containerized Next.js behind Cloudflare.
- Backend: Fly.io, Render, Railway, AWS ECS, or GCP Cloud Run.
- Database: Managed PostgreSQL with TimescaleDB support.
- Queue/cache: Managed Redis.
- Secrets: platform secret manager, never committed to git.

## Production Gate

Do not launch paid real-time alerts until these are complete:

- Market data contract explicitly allows commercial use and alert distribution.
- Terms of service state the product is a screening tool, not investment advice.
- Billing provider is verified for recurring billing and e-invoice workflow.
- Delivery providers have bounce, block, quota, and retry monitoring.

