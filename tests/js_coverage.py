"""Покрытие функций V8 по реальным вызовам в браузерных сценариях."""

import json
from pathlib import Path
from urllib.parse import urlsplit


class FunctionCoverage:
    def __init__(self, root):
        self.root = root
        self.scripts = {
            f"/static/js/{path.name}": {}
            for path in sorted((root / "static/js").glob("*.js"))
        }

    def sample(self, session, origin):
        for script in session.send("Profiler.takePreciseCoverage")["result"]:
            url = urlsplit(script["url"])
            if url.netloc != origin.netloc or url.path not in self.scripts:
                continue
            functions = self.scripts[url.path]
            for function in script["functions"]:
                span = function["ranges"][0]
                key = (span["startOffset"], span["endOffset"])
                functions[key] = functions.get(key, False) or span["count"] > 0

    def write(self):
        summary = {
            path: {"called": sum(functions.values()), "observed": len(functions)}
            for path, functions in self.scripts.items()
        }
        target = Path(self.root, "qa-results", "javascript.json")
        target.parent.mkdir(exist_ok=True)
        target.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
