"""Independently assert raw T28 observations and exact retained source fingerprints."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit
from build import fingerprints, sha, ROOT, WRAPPER


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def cookies(value):
    return dict(item.strip().split("=", 1) for item in (value or "").split(";") if "=" in item)


def mapping(app_id):
    key = base64.b32encode(hashlib.sha256(app_id.encode("ascii")).digest()).decode().lower().rstrip("=")
    return {"id": app_id, "key": key, "origin": f"https://mp-{key}.invalid", "profile": f"moonpool-v1-{key}"}


def verify_report(report):
    require(report["multiProfile"] is True, "Real MULTI_PROFILE support required")
    require(report["providerVersion"] == "145.0.7632.218" and report["sdk"] == 37, "Retained target mismatch")
    a, b = mapping("com.example.a"), mapping("com.example.b")
    require(report["a"] == a and report["b"] == b, "Independent SHA256/base32 mapping")
    metadata = report["build"]
    require(metadata["sources"] == fingerprints(), "Source/asset fingerprints changed after capture")
    require(metadata["identityVectorsSha256"] == sha(ROOT.parent / "identity-vectors.json"), "Reference vector fingerprint")
    require(metadata["reusedWrapperSha256"] == sha(WRAPPER), "Wrapper fingerprint")
    require(metadata["reusedWrapperPropertiesSha256"] == sha(WRAPPER.parent / "gradle/wrapper/gradle-wrapper.properties"), "Wrapper properties fingerprint")
    require(report["installedApkSha256"] == metadata["apkSha256"], "Installed APK mismatch")
    require(len(metadata["apkSha256"]) == 64, "Missing APK digest")
    events = report["events"]
    require(not any(e["kind"] in {"setup-error", "tls-error", "load-error", "decode-error", "remote-decode-error"} for e in events), "Native load/decode failure")
    early = [e for e in events if e["kind"] == "early-getProfile"]
    require(len(early) == 1 and early[0]["outcome"] == "rejected" and early[0]["exception"] == "IllegalStateException", "Real early getProfile misuse must reject")
    profile_events = [e for e in events if e["kind"] == "profile-before-use"]
    expected_views = {"a1": a["profile"], "a2": a["profile"], "b": b["profile"], "b-within-a-profile": a["profile"], "a-recreated": a["profile"], "remote-a": a["profile"], "remote-b": b["profile"], "remote-host": "t28-host-public-sentinel", "remote-a-shared": a["profile"]}
    require(len(profile_events) == len(expected_views), "Every view selected a profile before use")
    require({e["view"]: e["actual"] for e in profile_events} == expected_views, "Exact guest view/profile assignment")
    require(all(e["requested"] == e["actual"] for e in profile_events), "Requested profile selected exactly")
    require(len(report["samples"]) == 11, "No missing or duplicate samples")
    samples = {s["name"]: s for s in report["samples"]}
    require(set(samples) == {"a-initial", "b-initial", "a-shared", "b-within-a-profile", "a-before-reload", "a-reload", "a-recreated", "remote-a", "remote-b", "remote-host", "remote-a-shared"}, "Missing positive/negative samples")
    tag = report["tag"]
    for name in ["a-initial", "b-initial", "a-shared", "a-before-reload", "a-reload", "a-recreated", "b-within-a-profile"]:
        sample = samples[name]
        app = "b" if name.startswith("b") else "a"
        selected = b if app == "b" else a
        other = a if app == "b" else b
        origin_only = name == "b-within-a-profile"
        require(sample["profile"] == (a["profile"] if origin_only else selected["profile"]), name + " profile")
        document = sample["document"]
        require(document["origin"] == selected["origin"] and document["secureContext"] is True, name + " loaded HTTPS origin")
        require(urlsplit(document["href"]).netloc == urlsplit(selected["origin"]).netloc, name + " exact host")
        expected = None if origin_only else f"{tag}-{app}"
        for storage in ["localStorage", "indexedDB"]:
            require(document["after"][storage] == expected, name + " storage after")
            if report["phase"] == "restart" or name not in {"a-initial", "b-initial"}:
                require(document["before"][storage] == expected, name + " read-only persistence")
            before = document["before"][storage]
            require(before is None or before.endswith("-" + app), name + " no foreign storage before seed")
        require(document["ownFrame"]["ready"] == {"origin": selected["origin"], "marker": f"loaded-{app}"}, name + " actual same-origin loaded frame")
        require(document["ownFrame"]["access"] == {"marker": f"loaded-{app}", "localStorage": expected}, name + " positive DOM/storage access")
        require(document["crossFrame"]["ready"] == {"origin": other["origin"], "marker": "loaded-" + ("a" if app == "b" else "b")}, name + " actual foreign loaded frame")
        require(document["crossFrame"]["access"] == {"error": "SecurityError"}, name + " foreign DOM blocked")
        for raw in [document["before"]["cookie"], document["after"]["cookie"], sample["ownNativeCookies"], sample["siblingNativeCookies"]]:
            require("t28_parent" not in cookies(raw) and "t28_sibling" not in cookies(raw), name + " parent/sibling Domain rejection")
        require(cookies(document["after"]["cookie"]).get("t28_local") == expected, name + " host-only cookie positive")
        require(cookies(sample["ownNativeCookies"]).get("t28_local") == expected, name + " profile native cookie positive")
        require(cookies(sample["siblingNativeCookies"]).get("t28_local") == (f"{tag}-a" if origin_only else None), name + " independent origin cookie control")
        previous_cookie = cookies(document["before"]["cookie"]).get("t28_local")
        require(previous_cookie is None or previous_cookie.endswith("-" + app), name + " no cookie bleed before seed")
    require(len({samples[name]["document"]["documentToken"] for name in samples if samples[name]["type"] == "local"}) == 7, "Replacement/reload/recreated views have fresh real documents")
    require(samples["a-reload"]["loadAction"] == "reload", "Actual reload API control")
    for owner in ["a", "b", "host", "a-shared"]:
        sample = samples["remote-" + owner]
        real_owner = "a" if owner == "a-shared" else owner
        expected_profile = a["profile"] if real_owner == "a" else b["profile"] if real_owner == "b" else "t28-host-public-sentinel"
        require(sample["profile"] == expected_profile, owner + " remote profile")
        for data in [sample["before"], sample["after"]]:
            require(data["origin"] == "https://example.com" and data["title"] == "Example Domain" and data["secureContext"] is True, owner + " actual TLS-loaded remote positive")
        before = cookies(sample["before"]["before"]).get("t28_remote")
        require(before is None or before.endswith("-" + real_owner), owner + " no remote bleed before seed")
        if report["phase"] == "restart" or owner == "a-shared":
            require(before == f"{tag}-{real_owner}", owner + " read-only shared/restart remote persistence")
        require(cookies(sample["after"]["cookie"]).get("t28_remote") == f"{tag}-{real_owner}", owner + " isolated remote cookie")
        require(cookies(sample["nativeCookies"]).get("t28_remote") == f"{tag}-{real_owner}", owner + " native Profile CookieManager corroboration")
        require(any(e["kind"] == "remote-network-request" and e["view"] == "remote-" + owner and e["mainFrame"] is True and e["url"] == "https://example.com/" for e in events), owner + " unintercepted network request")
    return len(report["samples"])


def verify_directory(directory):
    files = sorted(Path(directory).glob("t28-*.json"))
    require(len(files) == 4, "Require two seed/restart pairs")
    reports = [json.loads(path.read_text()) for path in files]
    require({(r["tag"], r["phase"]) for r in reports} == {(t, p) for t in ["t28-first", "t28-repeat"] for p in ["seed", "restart"]}, "Complete independent run pairs")
    require(len({r["build"]["apkSha256"] for r in reports}) == 1, "Same final APK across runs")
    total = sum(verify_report(report) for report in reports)
    print(f"Verified {len(reports)} Android runs / {total} raw samples; exact mappings, loaded frames, storage, cookies, profiles and source fingerprints.")
    return reports

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", nargs="?", default=str(ROOT / "results"))
    verify_directory(parser.parse_args().directory)
