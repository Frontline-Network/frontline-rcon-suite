# Backend image source verification

The Frontline deployment helper builds the configured backend images and, before
stopping or starting any services, compares each image with a Git archive of the
target commit. The check runs in a network-isolated container. It checks the
runtime directories and files explicitly copied by the backend Dockerfile,
normalizes line endings for known text formats, compares binary assets exactly,
and reports unexpected Python files. It does not attest the installed Python
packages, image provenance, frontend assets, running container state, or live
server behavior; the other release checks remain necessary.

If the comparison fails, the helper stops before service changes and attempts to
restore its previous checkout. Read the reported paths and confirm the checkout
was restored cleanly. Check that the configured backend images were built from
the intended revision, that the Dockerfile and `.dockerignore` include the
reported runtime files, and that no older image layer left unexpected Python
modules. Correct the source or image configuration and rebuild with the normal
deployment process; do not bypass the check merely to make deployment continue.
If the checkout cannot be restored cleanly or the image is a separately managed
custom backend, inspect it and its compatibility before trying again.

The check is part of the current deployment helper. A helper from an older
checkout cannot perform a check it does not yet contain on its own first update.
Bootstrap the new helper and its dependencies with a reviewed process that
preserves local configuration and existing bind mounts before relying on it.
The source verification runs for each configured backend image, not for a
separately built frontend or shared Discord service.
