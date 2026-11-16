"""Judge both native admission and independent HTTPS receipts."""

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ADMITTED = ("initial", "reload", "recreated")
REFUSED = {"present": "B", "unknown": "A"}
STATIC = ("/static/seed.gif", "/static/echo.gif", "/static/redirect-other", "/static/redirect-same")
ATTEMPTS = {"fetch", "xhr", "beacon", "socket", "events", "form", "frame", "popup", "worker",
            "redirect-other", "redirect-same"}


def classify(report):
    problems = []

    def check(condition, issue):
        if not condition:
            problems.append(issue)

    check(report.get("complete") is True and not report.get("errors"), "native collection incomplete or failed")
    partitions = report["partitions"]
    check(set(partitions) == set("ABHU") and len(set(partitions.values())) == 4, "partition names overlap")
    results = {item["view"]: item for item in report["samples"]}
    check(set(results) == set(ADMITTED) | set(REFUSED) and len(results) == len(report["samples"]),
          "missing or duplicate admission samples")
    receipts = report["receipts"]
    for row in receipts:
        check(row["tls"] and row["run"] == report["run"], "foreign or non-TLS receipt")
        if row["path"] == "/denied":
            check(False, f'{row["view"]}/{row["surface"]}: denied request reached {row["host"]}')
    controls = {item["view"]: item for item in report["controls"]}
    wanted_controls = {f"{role}-{stage}" for stage, roles in (("before", "HUB"), ("after-A", "HUB"), ("after-B", "HU"))
                       for role in roles}
    check(set(controls) == wanted_controls and len(controls) == len(report["controls"]), "missing or duplicate controls")

    def cookie_pairs(text):
        return set(text.split("; ")) if text else set()

    for view, control in controls.items():
        role, stage = view.split("-", 1)
        marker = report["run"] if role == "H" else "public"
        visible = f"c09_{role.lower()}={marker}"
        expected_network = {visible, "c09_hidden=public"} if role == "B" else {visible}
        check(control["policyAllows"] is True and cookie_pairs(control["cookie"]) == {visible},
              f"{view}: host/other-profile cookie control failed")
        path = "/echo" if stage == "before" else "/control"
        rows = [row for row in receipts if row["path"] == path and row["view"] == view]
        check(len(rows) == 1 and cookie_pairs(rows[0]["cookie"]) == expected_network,
              f"{view}: no matching server cookie control")
    for view in ADMITTED:
        if view not in results:
            continue
        item = results[view]
        check(item["events"] == ["policyComplete", "policyRead", "presence", "load", "script"],
              f"{view}: wrong admission/load order")
        check(item["partition"] == partitions.get("A") and item["presence"] == "empty" and not item["policyAllows"],
              f"{view}: admission gate used an invalid store or policy")
        check(item["loadCalls"] == item["guestResources"] == 1 and item["afterPresent"] is False,
              f"{view}: guest loads or post-run jar differs")
        if report["platform"] == "ios":
            check(item.get("presenceEvidence") == {"cookies": False, "records": False},
                  f"{view}: iOS requires both empty native sources")
        guest = item.get("guest") or {}
        check(guest.get("view") == view, f"{view}: wrong guest execution marker")
        origin = (f'moonpool://com.example.paths.{report["run"]}.a' if report["platform"] == "ios"
                  else f'https://mp-{report["run"]}-a.invalid')
        check(guest.get("origin") == origin, f"{view}: guest origin differs")
        for field in ("first", "afterWrite", "last", "frame"):
            check(guest.get(field) == {"direct": "", "prototype": ""},
                  f"{view}/{field}: cookie read or write is visible")
        previous = None if view == "initial" else report["run"]
        check(guest.get("storage") == {"local": report["run"], "indexed": report["run"],
                                     "previousLocal": previous, "previousIndexed": previous},
              f"{view}: localStorage/IndexedDB evidence differs")
        check(guest.get("resources") == {"local": "loaded", "seed": "loaded", "echo": "loaded"},
              f"{view}: allowed resources failed")
        attempts = guest.get("attempts") or {}
        check(set(attempts) == ATTEMPTS and "connect-src" in guest.get("violations", []),
              f"{view}: browser attempt/violation evidence missing")
        check(not {"resolved", "opened", "executed"} &
              {value for name, value in attempts.items() if name != "popup"},
              f"{view}: forbidden browser entry point executed")
        check(attempts.get("popup") == "blocked" or item.get("popupDenials") == 1,
              f"{view}: popup has no native denial witness")
        rows = [row for row in receipts if row["view"] == view and row["path"] in STATIC]
        check(Counter(row["path"] for row in rows) == Counter(STATIC), f"{view}: missing static/echo.gif receipts")
        check(all(row["cookie"] == "" for row in rows), f"{view}: engine cookie sent with an approved resource")
    for view, role in REFUSED.items():
        if view not in results:
            continue
        item = results[view]
        check(item["events"] == ["policyComplete", "policyRead", "presence", "refuse"],
              f"{view}: wrong admission/refusal order")
        check(item["partition"] == partitions.get(role) and item["presence"] == view and not item["policyAllows"],
              f"{view}: refusal did not use the assigned partition")
        check(item["loadCalls"] == item["guestResources"] == 0 and item["guest"] is None,
              f"{view}: refused store reached guest execution")
        check(not any(row["view"] == view for row in receipts), f"{view}: refused store reached the server")
    seeded = results.get("present", {})
    check(seeded.get("afterPresent") is True and set(seeded.get("beforeCookies", [])) ==
          set(seeded.get("afterCookies", [])) == {"c09_b=public", "c09_hidden=public"},
          "present: browser cookies were lost or the hidden seed was missing")
    if report["platform"] == "ios":
        check(seeded.get("presenceEvidence") == {"cookies": True, "records": True},
              "present: missing iOS presence witness from both sources")
    check(results.get("unknown", {}).get("source") == "injected", "unknown: injected source is unlabeled")
    return problems


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_fingerprints(platform):
    admission = ROOT.parent / "native-cookie-admission-probe"
    files = [ROOT / name for name in ("runner.py", "server.py", "paths.js")]
    if platform == "android":
        files += [
            admission / "android/app/src/main/java/org/moonpool/cookieadmission/AdmissionGate.java",
            admission / "android/app/src/main/res/xml/network_security_config.xml",
            ROOT.parent / "android-origin-probe/gradlew",
        ]
        files += [path for path in (ROOT / "android").rglob("*") if path.is_file()
                  and not {"build", ".gradle"} & set(path.relative_to(ROOT).parts)]
    else:
        files += [admission / "ios/AdmissionGate.swift", ROOT / "ios/Probe.swift"]
    return {os.path.relpath(path, ROOT): sha(path) for path in sorted(files)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("reports", type=Path, nargs="+")
    args = parser.parse_args()
    failed = False
    for path in args.reports:
        report = json.loads(path.read_text())
        assert report["build"]["sources"] == source_fingerprints(report["platform"]), "Changed sources"
        assert report["installedArtifactSha256"] == report["build"]["artifactSha256"]
        problems = classify(report)
        failed |= bool(problems)
        print(f'{path.stem}: {len(report["samples"])} samples, {len(report["receipts"])} receipts, '
              f'{len(problems)} failures')
        for problem in problems:
            print("  " + problem)
    raise SystemExit(int(failed))


if __name__ == "__main__":
    main()
