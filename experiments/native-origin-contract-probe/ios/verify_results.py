"""Independently verify raw positive controls; producer pass/fail fields are insufficient."""
import hashlib
import json
from pathlib import Path
import re
import sys
import uuid

ROOT = Path(__file__).resolve().parent
COUNT = 0

def check(condition, message):
    global COUNT
    if not condition:
        raise AssertionError(message)
    COUNT += 1

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def cookie_map(text):
    check(isinstance(text, str), "cookie snapshot must be a string")
    return dict(piece.split("=", 1) for piece in text.split("; ") if piece)

def verify(directory):
    vectors = json.loads((ROOT.parent / "identity-vectors.json").read_text())["vectors"]
    assigned = None
    metadata_reference = None
    for run in ["first", "repeat"]:
        for phase in ["seed", "restart"]:
            name = f"{run}-{phase}"
            data = json.loads((directory / f"{name}.json").read_text())
            check(data["complete"] and "error" not in data, f"{name}: incomplete/error")
            check(data["phase"] == phase and data["run"] == run, f"{name}: identity")
            check(data["os"] == "26.4.1", f"{name}: measured runtime")
            metadata = data["buildMetadata"]
            check(data["installedExecutableSha256"] == metadata["executableSha256"] and data["installedSignatureVerified"], f"{name}: installed artifact")
            check(metadata["sdk"] == "27.0" and metadata["codesignVerified"], f"{name}: build SDK/signature")
            expected_sources = {str(path.relative_to(ROOT)) for path in ROOT.rglob("*") if path.is_file() and path.suffix in {".py", ".swift", ".js", ".html"} and not any(part in {"build", "local-results"} for part in path.relative_to(ROOT).parts)}
            expected_fixtures = {str(path.relative_to(ROOT / "fixtures")) for path in (ROOT / "fixtures").rglob("*") if path.is_file()} | {"identity-vectors.json"}
            check(set(metadata["sources"]) == expected_sources and set(metadata["fixtures"]) == expected_fixtures, f"{name}: complete fingerprint file sets")
            for source, digest in metadata["sources"].items():
                check(sha(ROOT / source) == digest, f"{name}: source changed: {source}")
            for fixture, digest in metadata["fixtures"].items():
                path = ROOT.parent / "identity-vectors.json" if fixture == "identity-vectors.json" else ROOT / "fixtures" / fixture
                check(sha(path) == digest, f"{name}: fixture changed: {fixture}")
            if metadata_reference is None:
                metadata_reference = metadata
            check(metadata == metadata_reference, f"{name}: same final source/artifact")
            assignments = data["assignments"]
            check(set(assignments) == {"a", "b", "host", "diagnostics"}, f"{name}: four owned stores")
            check(len(set(assignments.values())) == 4 and all(uuid.UUID(value).int > 0 for value in assignments.values()), f"{name}: unique nonzero UUIDs")
            if assigned is None:
                assigned = assignments
            check(assignments == assigned, f"{name}: stable mappings across four processes")
            check({row["id"]: row["uuid"] for row in data["registry"]} == {f"com.example.probe.{app}": value for app, value in assignments.items()}, f"{name}: registry exact ids")
            for app, value in assignments.items():
                check(data["stores"][app] == {"identifier": value, "persistent": True}, f"{name}: actual persistent identified {app}")
                check(value in data["existingStoreIdentifiersBeforeOpen"], f"{name}: existing store observed before open")
                check(data["knownStoreAssignmentsBeforeOpen"][f"com.example.probe.{app}"] == value, f"{name}: durable trusted anchor {app}")
            check(len(data["identity"]) == len(vectors), f"{name}: identity count")
            for row, vector in zip(data["identity"], vectors):
                id_ = vector["id"]
                check(row["id"] == id_ and row["name"] == vector["name"], f"{name}: exact vector pairing")
                syntactic = re.fullmatch(r"[a-z0-9]+(\.[a-z0-9-]+)+", id_) is not None
                check(row["urlAdmission"] == syntactic == vector["manifestValid"], f"{name}: native URL admission {vector['name']}")
                if syntactic or vector["name"] in {"uppercase", "port", "escape"}:
                    message = row["message"]
                    origin = message["nativeOrigin"]
                    body = message["body"]
                    check(message["view"] == f"diagnostic-{vector['name']}" and message["mainFrame"], f"{name}: native sender vector pairing")
                    check(body["kind"] == "diagnostic" and row["nativeURL"] == body["href"], f"{name}: native/page URL control")
                    if syntactic:
                        check(body["host"] == origin["host"] and body["origin"] == f"moonpool://{id_}", f"{name}: actual native/JS host agreement")
                    else:
                        invalid_observations = {
                            "uppercase": ("com.Example.a", "moonpool://com.example.a", {"scheme": "moonpool", "host": "com.example.a", "port": 0}),
                            "port": ("com.example", "moonpool://com.example:443", {"scheme": "moonpool", "host": "com.example", "port": 443}),
                            "escape": ("com.%61", "moonpool://com.%61", {"scheme": "moonpool", "host": "com.%61", "port": 0}),
                        }
                        expected_host, expected_origin, expected_native = invalid_observations[vector["name"]]
                        check(body["host"] == expected_host and body["origin"] == expected_origin and origin == expected_native, f"{name}: retained actual invalid-candidate normalization")
                    expected = syntactic and origin == {"scheme": "moonpool", "host": id_, "port": 0}
                    check(row["measuredAdmission"] == expected, f"{name}: observed exact admission")
                    if syntactic:
                        check(origin == {"scheme": "moonpool", "host": id_, "port": 0} and body["href"] == f"moonpool://{id_}/diagnostic.html", f"{name}: exact valid native origin {vector['name']}")
                    else:
                        check(not row["measuredAdmission"], f"{name}: diagnostic invalid id stays rejected")
            samples = {row["label"]: row for row in data["samples"]}
            locals_ = ["initial-a", "initial-b", "same-app-second", "reload-a", "recreate-a", "b-under-a-store", "a-after-origin-control"]
            remotes = [f"https-{kind}-{app}" for kind in ["initial", "recreated"] for app in ["a", "b", "host"]]
            check(len(data["samples"]) == 13 and set(samples) == set(locals_ + remotes), f"{name}: complete named controls")
            document_tokens = [samples[label]["observation"]["documentToken"] for label in locals_]
            check(len(set(document_tokens)) == 7, f"{name}: seven distinct actually replaced documents")
            for label in locals_:
                sample = samples[label]
                value = sample["observation"]
                message = sample["freshNativeMessage"]
                check(sample["observedFreshLocalMessage"] and not sample["loadErrors"] and message["mainFrame"] and message["body"]["report"]["documentToken"] == value["documentToken"], f"{name}/{label}: fresh native document report")
                app = "b" if label in {"initial-b", "b-under-a-store"} else "a"
                store_owner = "a" if label == "b-under-a-store" else app
                check(sample["storeIdentifier"] == assignments[store_owner], f"{name}/{label}: actual per-view store")
                host = f"com.example.probe.{app}"
                other = "com.example.probe.a" if app == "b" else "com.example.probe.b"
                marker = None if label == "b-under-a-store" else f"{host}:{run}"
                check(message["nativeOrigin"] == {"scheme": "moonpool", "host": host, "port": 0}, f"{name}/{label}: actual local native securityOrigin")
                check(value["host"] == host and value["origin"] == f"moonpool://{host}", f"{name}/{label}: actual local document")
                check(value["local"] == marker and value["idb"] == marker, f"{name}/{label}: localStorage/IndexedDB exact partition")
                if phase == "restart" or label not in {"initial-a", "initial-b"}:
                    check(value["localBefore"] == marker, f"{name}/{label}: read before writes")
                check(value["customCookie"] == "", f"{name}/{label}: custom cookies unavailable")
                check(value["self"]["dom"] == host and value["self"]["storage"] == marker, f"{name}/{label}: working self DOM/storage control")
                for key, framehost in [("self", host), ("cross", other)]:
                    check(value[key].get("loaded") == {"kind": "t28-frame", "host": framehost, "eventOrigin": f"moonpool://{framehost}"}, f"{name}/{label}: actual ready frame {key}")
                    check(any(e["event"] == "scheme-delivered" and e["url"] == f"moonpool://{framehost}/frame.html" and e["bytes"] > 0 for e in data["events"]), f"{name}/{label}: frame bytes delivered {key}")
                check(value["cross"].get("domError") in {"TypeError", "SecurityError"} and "dom" not in value["cross"] and value["cross"]["storageError"] == "SecurityError", f"{name}/{label}: loaded foreign DOM/storage denied")
            for label in remotes:
                sample = samples[label]
                owner = label.rsplit("-", 1)[1]
                check(sample["owner"] == owner and sample["storeIdentifier"] == assignments[owner], f"{name}/{label}: independently bound owner/store")
                expected = f"{owner}_{run}"
                observation = sample["observation"]
                check(sample["loaded"] and observation["scheme"] == "https:" and observation["host"] == "example.com" and observation["title"] == "Example Domain" and observation["ready"] == "complete", f"{name}/{label}: actual HTTPS positive page")
                check(cookie_map(observation["cookie"]) == {"t28_remote": expected}, f"{name}/{label}: page only own sentinel")
                native = sample["nativeCookies"]
                check(len(native) == 1 and native[0]["name"] == "t28_remote" and native[0]["value"] == expected and native[0]["domain"] == "example.com" and native[0]["path"] == "/" and native[0]["secure"] and not native[0]["sessionOnly"] and native[0]["expires"] > 0, f"{name}/{label}: actual host-only persistent secure cookie")
                before = cookie_map(sample["beforeCookie"])
                check(all(k == "t28_remote" and v.startswith(f"{owner}_") for k, v in before.items()), f"{name}/{label}: no foreign cookie before seed overwrites")
                check(all(c["name"] == "t28_remote" and c["value"].startswith(f"{owner}_") for c in sample["beforeNativeCookies"]), f"{name}/{label}: native pre-seed isolation")
                if phase == "restart" or "recreated" in label:
                    check(before == {"t28_remote": expected}, f"{name}/{label}: read-only retained cookie")
                view = f"remote-recreated-{owner}" if "recreated" in label else f"remote-{owner}"
                check(any(e["event"] == "navigation-response" and e["view"] == view and e["mainFrame"] and e["status"] == 200 and e["mime"] == "text/html" and e["url"].startswith("https://example.com/") for e in data["events"]), f"{name}/{label}: native HTTPS200 control")
                check(any(m["view"] == view and m["mainFrame"] and m["nativeOrigin"] == {"scheme": "https", "host": "example.com", "port": 0} and m["body"]["kind"] == "https-control" for m in data["messages"]), f"{name}/{label}: actual native HTTPS securityOrigin")
    for mode in ["cold", "cold-callback", "initialized"]:
        for repeat in ["first", "repeat"]:
            control = json.loads((directory / f"startup-{mode}-{repeat}.json").read_text())
            check(control["mode"] == mode and control["repeat"] == repeat and control["buildMetadata"] == metadata_reference, "startup exact same artifact")
            check(control["beforeCall"]["guestLoads"] == 0 and control["installedSignatureVerified"] and control["installedExecutableSha256"] == metadata_reference["executableSha256"], "startup no-guest installed identity")
            if mode in {"cold", "cold-callback"}:
                check(control["crashMatchedLaunchProcess"] and control["outcome"] == "crashed" and control["crash"]["exceptionType"] == "EXC_BAD_ACCESS" and control["crash"]["signal"] == "SIGSEGV", "cold retained crash signature")
                symbols = [f["symbol"] for f in control["crash"]["frames"]]
                check(any("fetchAllDataStoreIdentifiers" in symbol for symbol in symbols) and any("RunLoop::dispatch" in symbol for symbol in symbols), "cold API-order stack")
            else:
                check(control["outcome"] == "completed" and control["report"]["guestLoads"] == 0 and set(assigned.values()).issubset(control["report"]["identifiedStores"]), "initialized public enumeration positive control")
    print(f"{COUNT} independent iOS assertions passed; 52 samples / 92 identity rows / 6 API-order controls")

if __name__ == "__main__":
    verify(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "results")
