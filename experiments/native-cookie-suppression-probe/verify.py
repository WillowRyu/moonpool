"""Independent checks over native snapshots and the HTTPS server's raw receipt log."""
import argparse
import json
from pathlib import Path


def expected_cases():
    return [{"id": f"{stage}-{view}-{kind}", "stage": stage, "view": view,
             "owner": "a" if view in ("a1", "a2") else view, "kind": kind,
             "blocked": (view in ("a1", "a2") and stage != "baseline") or
                        (view == "b" and stage in ("ab-blocked", "recreated", "fresh-blocked"))}
            for stage in ("baseline", "a-blocked", "ab-blocked", "recreated", "fresh-blocked")
            for view in ("a1", "a2", "b", "h", "u") for kind in ("remote", "local")]


def pairs(value):
    return dict(part.strip().split("=", 1) for part in value.split(";") if "=" in part)


def assess(report):
    count = 0
    violations = []
    def require(condition, message):
        nonlocal count
        assert condition, message
        count += 1
    def expect(condition, message):
        nonlocal count
        count += 1
        if not condition: violations.append(message)
    require(report.get("complete") is True, "incomplete report")
    require(report["platform"] in ("android", "ios"), "unknown platform")
    expected = expected_cases()
    samples = report["samples"]
    require(len(samples) == len(expected), "missing or duplicate sample")
    require([s["id"] for s in samples] == [c["id"] for c in expected], "case order/identity")
    for case, sample in zip(expected, samples):
        label = case["id"]
        doc = sample["document"]
        marker = case["owner"] + "_" + case["stage"]
        visible = not case["blocked"] and (case["kind"] == "remote" or report["platform"] == "android")
        require(sample["actualPartition"] == case["owner"], label + ": wrong partition")
        expect(sample["policyAllows"] is not case["blocked"], label + ": policy locality")
        require(sample["policyBeforeLoad"] is True and not sample["loadErrors"], label + ": load/policy failure")
        require(doc["case"] == label and doc["complete"] is True, label + ": stale document")
        require(doc["frameLoaded"] is True, label + ": missing fresh frame")
        for field in ("cookie", "prototypeRead", "frameRead"):
            cookies = pairs(doc[field])
            if visible:
                expect(all(cookies.get("t28_" + name) == marker for name in ("js", "proto", "frame")), label + ": missing script controls")
            else:
                expect(not cookies, label + ": raw cookie access " + field)
        expect(all(v.startswith(case["owner"] + "_") for v in sample["nativeCookieValues"]), label + ": foreign native cookie")
        if case["blocked"]:
            expect(marker not in sample["nativeCookieValues"], label + ": hidden native mutation")
            if case["stage"] == "fresh-blocked": expect(not sample["nativeCookieValues"], label + ": fresh store gained cookies")
        if case["kind"] != "remote": continue
        require(doc["remoteObserved"] is True and doc["secureContext"] is True, label + ": TLS positive control")
        rows = [r for r in report["requests"] if r["case"] == label]
        for path in ("/page", "/frame", "/resource", "/observe"):
            matches = [r for r in rows if r["path"] == path]
            require(len(matches) == 1 and matches[0]["tls"] is True, label + ": missing/duplicate server path " + path)
        for row in rows:
            cookies = pairs(row["cookie"])
            expect(all(v.startswith(case["owner"] + "_") for v in cookies.values()), label + ": cross-partition server receipt")
            if case["blocked"]:
                expect(not cookies, label + ": engine sent cookies " + row["path"])
            elif row["path"] == "/observe":
                expect(all(cookies.get("t28_" + name) == marker for name in ("js", "proto", "frame", "server", "resource", "frameHeader")), label + ": server did not receive positive controls")
    return {"checks":count,"violations":violations,"contractPass":not violations}


def verify(report):
    result=assess(report)
    assert not result['violations'], '; '.join(result['violations'])
    return result['checks']


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("reports", nargs="+", type=Path)
    parser.add_argument('--evidence',action='store_true',help='Validate evidence and report contract violations without treating them as success')
    args=parser.parse_args()
    for path in args.reports:
        report=json.loads(path.read_text())
        from integrity import check_artifacts, check_bindings
        check_artifacts(report); check_bindings(report)
        if args.evidence:
            result=assess(report)
            print(f"{path.name}: evidence valid, {result['checks']} checks / {len(report['samples'])} samples; proposed contract {'PASS' if result['contractPass'] else 'FAIL'} ({len(result['violations'])} violations)")
        else: print(f"{path.name}: {verify(report)} assertions / {len(report['samples'])} samples pass")
