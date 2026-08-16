# Frontline callback broker

`callback.fln.gg` maps an opaque CRCON installation UUID to the public HTTPS
address registered by the trusted WordPress provisioner. The Discord service
authenticates with a separate capability. Existing CRCON action/event
capabilities remain end-to-end and are not stored by this service.

Only the explicit Discord callback API paths are forwarded. Targets must use
HTTPS, resolve exclusively to public addresses, may not redirect, and are
re-resolved for every request to guard against SSRF and DNS rebinding.
