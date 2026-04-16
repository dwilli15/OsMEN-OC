# Single-Bot Safe Conversation Mode

## Policy
- **Ingress**: Mention-only. The bot responds only when explicitly @mentioned or directly addressed.
- **Public synthesis**: Only the steward agent publishes synthesized responses to the main channel.
- **No ambient execution**: No background processing of channel messages unless explicitly triggered.

## Scope
Applies to both Telegram and Discord in single-bot deployments where the bot shares a channel with human users.

## Rationale
Prevents the bot from flooding channels with unprompted responses while maintaining useful mention-triggered behavior.
