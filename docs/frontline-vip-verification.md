# Frontline VIP verification

Frontline VIP links a WordPress account to the player identity reported by the
game server. The customer does not enter a Steam ID or EOS ID in checkout.

## Flow

1. The customer signs in to the FLN website and generates a one-time code in
   the WooCommerce account area before buying VIP.
2. The code is bound to that FLN account and the selected game world.
3. The customer sends `!vipverify CODE` in the game chat on a participating
   FLN server.
4. CRCON submits the chat sender's actual player ID, player name, platform,
   game and server number to the signed WordPress REST endpoint.
5. WordPress permanently links that game identity to the FLN account and
   consumes the code. The first successful verification of the FLN account
   reserves a one-time seven-day VIP bonus for that exact game identity.
6. WordPress synchronizes the bonus to every RCON endpoint configured for the
   corresponding game. The claim is uniquely bound to both the FLN account and
   the game identity, so generating another code cannot extend it again. A
   failed sync reuses the stored absolute expiration instead of adding another
   seven days.
7. Later WooCommerce purchases extend the centrally stored expiration and are
   synchronized normally. Existing paid-order verification codes remain
   supported as a legacy flow. If activation fails, the verified identity
   remains linked and the order can be retried without another verification.

A code stays valid until it is redeemed or replaced. A game identity can only
belong to one FLN account. Player names are display metadata and are never used
as proof of ownership. HLL: Vietnam continues to use the game server's EOS ID
as its player ID; a reported Steam/Xbox/PlayStation platform is stored only as
metadata.

## Configuration

Set a random secret of at least 32 characters in WordPress `wp-config.php`:

```php
define('FRONTLINE_VIP_REDEEM_SECRET', 'replace-with-a-long-random-secret');
```

Set the endpoint and the exact same secret in the CRCON `.env`:

```dotenv
FRONTLINE_VIP_REDEEM_URL=https://fln.gg/wp-json/frontline-vip/v1/redeem
FRONTLINE_VIP_REDEEM_SECRET=replace-with-the-same-long-random-secret
```

The values are passed to backend and supervisor containers by the supplied
Docker Compose templates. Keep the secret out of Git and rotate it on both
sides if it is exposed.

In the Frontline VIP WordPress settings, assign every RCON endpoint to
`Hell Let Loose` or `Hell Let Loose: Vietnam`. `Alle / Legacy` remains
available for existing installations but intentionally receives both games.

## Request authentication

CRCON signs the exact JSON request body with HMAC-SHA256. The signature input
is `timestamp + "\n" + nonce + "\n" + raw_body`. WordPress rejects invalid
signatures and timestamps older or newer than five minutes.
