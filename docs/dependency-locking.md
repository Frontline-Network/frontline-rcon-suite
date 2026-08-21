# Reproduzierbare Python-Abhängigkeiten

`requirements.txt` und `requirements-dev.txt` beschreiben die bewusst
gewählten direkten Abhängigkeiten. Alle direkten PyPI-Abhängigkeiten müssen
auf eine exakte Version festgelegt sein. Die vollständigen, transitiven
Auflösungen werden versioniert:

- `requirements.lock` für den Produktionscontainer
- `requirements-dev.lock` für CI und Entwicklung (Produktion plus Test- und
  Formatierungswerkzeuge)

Beide Dateien enthalten die verfügbaren SHA-256-Hashes der PyPI-Artefakte. Die
einzige Ausnahme ist `discord-webhook`: Das Projekt benötigt weiterhin den
Upstream-Fork. Er ist mit dem vollständigen Git-Commit
`89ae25140b30a6747de70e5bf16bc5ba04a9b238` unveränderlich festgelegt; Git
liefert für einen Checkout keinen von pip verwendbaren Distributions-Hash.

## Installation

Container und CI installieren immer das jeweilige Lockfile mit `--no-deps`.
Damit darf pip keine weitere Version auflösen; alle Pakete einschließlich der
Transitiven stehen bereits im Lockfile. Bei Paketen mit `--hash` prüft pip das
geladene Artefakt gegen die hinterlegte Hash-Liste.

```powershell
python -m pip install --no-deps -r requirements-dev.lock --no-compile
```

## Geplanter Abhängigkeits-Update

Nur für einen bewussten Versions- oder Sicherheitsupdate werden zuerst die
direkten Pins in `requirements.txt` beziehungsweise `requirements-dev.txt`
angepasst. Danach beide Lockfiles in einer Python-3.12-Umgebung regenerieren,
den Diff prüfen und die Tests ausführen:

```powershell
uv pip compile --generate-hashes --output-file requirements.lock requirements.txt
uv pip compile --generate-hashes --output-file requirements-dev.lock requirements.txt requirements-dev.txt
python -m pip install --no-deps -r requirements-dev.lock --no-compile
python -m pytest tests/
```

Das Lockfile darf nicht für Routine-Builds regeneriert werden. Ein identischer
Commit verwendet dadurch dieselben Paketversionen und Artefakt-Hashes in
lokaler Entwicklung, CI und im Produktionscontainer.
