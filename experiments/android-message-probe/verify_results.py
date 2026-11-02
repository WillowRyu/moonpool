"""Check actual native controls, preserving raw-port provenance failures."""

import argparse
import hashlib
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("directory", type=Path)
args = parser.parse_args()
checks = 0
metadata = None


def require(value, label):
    global checks
    if not value:
        raise AssertionError(label)
    checks += 1


for profile in ["https", "custom"]:
    for run in ["first", "repeat"]:
        report = json.loads((args.directory / f"{profile}-{run}.json").read_text())
        context = profile + "/" + run
        require(report["complete"] and report["profile"] == profile and report["run"] == run, context + " complete")
        require(all(report["features"].values()) and len(report["features"]) == 6, context + " feature matrix")
        require(metadata is None or metadata == report["buildMetadata"], "One final artifact/source set")
        metadata = report["buildMetadata"]
        samples = {s["label"]: s for s in report["samples"]}
        events = report["events"]
        require(len(samples) == (19 if profile == "https" else 3), context + " all snapshots")
        require(not any(s.get("unavailable") for s in samples.values()), context + " no missed observation")
        listener = [e for e in events if e["type"] == "listener"]
        require(not any(e["type"] in ["listener-error", "port-error", "close-error", "asset-error"] for e in events), context + " no harness error")
        require(all(e["senderMatches"] and e["claimedOrigin"] == "https://forged.invalid" for e in listener), context + " native identity distinct from forged claims")
        for label in ["initial-a", "initial-b", "same-origin-other-view"]:
            sample = samples[label]
            data = sample["observation"]
            require(data["observerPresent"] and data["ready"] and len(data["frames"]) == 2, context + "/" + label + " loaded positives")
            first = [e for e in listener if e["view"] == sample["view"] and e["kind"] == "inline" and e["mainFrame"]]
            require(first and first[0]["beforePageFinished"] and first[0]["readyState"] == "loading", context + "/" + label + " first message before finish")
            require(all(frame["observerPresent"] for frame in data["frames"]), context + "/" + label + " both frame scripts ran")
            if profile == "https":
                require(data["pinnedPresent"] and data["challengeReceived"], context + "/" + label + " admitted bootstrap")
                require(sorted(frame["pinnedPresent"] for frame in data["frames"]) == [False, True], context + "/" + label + " exact origin injection")
            else:
                require(not data["pinnedPresent"] and not data["challengeReceived"], context + "/" + label + " no custom-host fallback")
        require(any(e["type"] == "host-route-replay" and e["decision"] == "wrong-view" for e in events), context + " same-origin other-view denial")
        if profile == "custom":
            require(all(e["decision"] != "accepted" for e in listener), context + " collapsed custom origins not admitted")
            registrations = [e for e in events if e["type"] == "pinned-registration"]
            require(len(registrations) == 3 and all(not e["accepted"] for e in registrations), context + " custom hostname rules rejected")
            print(json.dumps({"run": context, "nativeOrigins": sorted({e["sourceOrigin"] for e in listener})}))
            continue
        require(all(e["mainFrame"] for e in listener if e["decision"] == "accepted"), context + " no subframe admitted")
        require(any(e["decision"] == "subframe" and e["channel"] == "pinned" for e in listener), context + " same-origin iframe rejected after injection")
        require(any(e["decision"] == "wrong-origin" and e["kind"] == "ready" for e in listener), context + " actual foreign message denied")
        for label in ["replacement", "reload"]:
            require(any(e["type"] == "proxy-comparison" and e["label"] == label and not e["sameProxy"] for e in events), context + "/" + label + " proxy replaced")
        for label in ["late-proxy-replacement", "late-proxy-reload"]:
            require(not any(reply["kind"].startswith("late-for-") for reply in samples[label]["observation"]["replies"]), context + "/" + label + " old reply excluded")
        require("wrong-target" not in samples["wrong-target"]["observation"]["bootstraps"], context + " wrong target never delivered")
        messages = [e for e in events if e["type"] == "port-message" and e["provenance"] == "platform"]
        require(not any(e["label"] == "wrong-target" for e in messages), context + " wrong target has no callback")
        for label in ["raw-positive", "proof-positive", "listener-offer", "replacement-proof-positive", "stale-origin-only", "proof-delegated"]:
            batch = [e for e in messages if e["label"] == label]
            require(len(batch) == 3 and [e["messageSequence"] for e in batch] == [0, 1, 2], context + "/" + label + " ordered receive")
            require(all(e["decision"] == "accepted" and not e["originMetadataAvailable"] and not e["frameMetadataAvailable"] for e in batch), context + "/" + label + " native port control")
            replies = [r for r in samples[label]["observation"]["portReplies"] if r["label"] == label]
            require(len(replies) == 3, context + "/" + label + " round-trip positive")
        for label in ["stale-proof", "reload-stale-proof"]:
            batch = [e for e in messages if e["label"] == label]
            require(len(batch) == 3 and all(e["decision"] == "wrong-document-proof" for e in batch), context + "/" + label + " old proof denied")
        require(any(e["type"] == "listener-port-offer" and e["sourceOrigin"] == "https://com.example.probe.a.test" and e["mainFrame"] and e["count"] == 1 for e in events), context + " port transferred with attested sender")
        require(all(e["claimedDoc"] == "a2" for e in messages if e["label"] == "stale-origin-only"), context + " origin-only bootstrap reaches replacement")
        require(any(e["kind"] == "delegated-port-received" and not e["mainFrame"] and e["sourceOrigin"] == "https://com.example.probe.b.test" for e in listener), context + " delegated port really reached foreign frame")
        require(all(e["claimedOrigin"] == "https://com.example.probe.b.test" and e["proofMatches"] for e in messages if e["label"] == "proof-delegated"), context + " proof does not prevent intentional delegation")
        require(any(e["type"] == "host-listener-replay" and e["decision"] == "retired" for e in events), context + " retired listener replay")
        require(any(e["type"] == "port-message" and e["provenance"] == "host-replay" and e["decision"] == "retired" for e in events), context + " retired port replay")
        require(any(e["type"] == "post-after-close" and e["threw"] for e in events), context + " post-after-close fails")
        require(any(e["kind"] == "after-retire" and e["decision"] == "retired" for e in listener), context + " real callback after retirement denied")

root = Path(__file__).resolve().parent
for name, sha in metadata["sources"].items():
    require(hashlib.sha256((root / name).read_bytes()).hexdigest() == sha, "Source fingerprint: " + name)
print(f"{checks} controls passed; origin-only replacement and transferable-port provenance gaps remain explicit.")
