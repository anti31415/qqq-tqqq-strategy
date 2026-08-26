# API and Setup Checklist

## Alpaca paper

1. Create paper-only API credentials.
2. Copy `autotrade/.env.example` to a local `.env`.
3. Confirm options permissions for cash-secured puts and covered calls.
4. Verify market-data entitlements and paper/live endpoints.
5. Run `python -m autotrade.cli doctor` before running a plan.

## IBKR paper

1. Create or confirm a paper account.
2. Start Client Portal Gateway locally.
3. Configure the gateway URL in `.env`.
4. Verify account, positions, orders, and option permissions.

Never commit credentials, tokens, account identifiers, or runtime logs.

