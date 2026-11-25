import UIKit
import WebKit

private let guardedPolicy = "default-src 'none'; script-src 'self' 'unsafe-inline'; "
    + "frame-src 'self'; worker-src 'none'; base-uri 'none'"
private let policyHeader = "Content-Security-Policy"

private struct FixtureError: LocalizedError {
    let errorDescription: String?
    init(_ message: String) { errorDescription = message }
}

@MainActor private final class FixtureLoader: NSObject, WKURLSchemeHandler {
    private let origin: String
    private let kind: String
    private let policy: String
    private let assets: [String: Data]
    private(set) var requests: [String] = []
    private(set) var policies: [String: String] = [:]

    init(origin: String, kind: String, policy: String, assets: [String: Data]) {
        self.origin = origin
        self.kind = kind
        self.policy = policy
        self.assets = assets
    }

    func webView(_ webView: WKWebView, start task: WKURLSchemeTask) {
        guard let url = task.request.url, task.request.httpMethod == "GET",
              url.absoluteString == origin + url.path else {
            task.didFailWithError(URLError(.unsupportedURL))
            return
        }

        let path = url.path
        let isDocument = path == "/entry/\(kind)" || (kind == "same" && path == "/same-frame")
        let beforeBlank = kind == "blank-navigation" && path == "/before-blank"
        var headers = ["Cache-Control": "no-store"]
        let data: Data
        if isDocument {
            headers["Content-Type"] = "text/html; charset=utf-8"
            if !policy.isEmpty { headers[policyHeader] = policy }
            data = Data("""
                <!doctype html><meta charset="utf-8"><title>Local document frames</title>
                <body><script src="/probe.js"></script>
                """.utf8)
        } else if beforeBlank {
            headers["Content-Type"] = "text/html; charset=utf-8"
            data = Data("<!doctype html><p id=\"before-blank\">Before navigation</p>".utf8)
        } else if let asset = assets[path] {
            headers["Content-Type"] = "text/javascript; charset=utf-8"
            data = asset
        } else {
            task.didFailWithError(URLError(.fileDoesNotExist))
            return
        }

        guard let response = HTTPURLResponse(url: url, statusCode: 200, httpVersion: nil, headerFields: headers) else {
            task.didFailWithError(URLError(.badServerResponse))
            return
        }
        requests.append(path)
        if isDocument || beforeBlank { policies[path] = response.value(forHTTPHeaderField: policyHeader) ?? "" }
        task.didReceive(response)
        task.didReceive(data)
        task.didFinish()
    }

    func webView(_ webView: WKWebView, stop task: WKURLSchemeTask) {}
}

@MainActor private final class FixtureController: UIViewController {
    private let run: String
    private let frameSource: String
    private let documentSet: String

    init(run: String, frameSource: String, documentSet: String) {
        self.run = run
        self.frameSource = frameSource
        self.documentSet = documentSet
        super.init(nibName: nil, bundle: nil)
    }

    required init?(coder: NSCoder) { return nil }

    private func inspect(_ store: WKWebsiteDataStore) async -> [String: Bool] {
        let jar = store.httpCookieStore
        await withCheckedContinuation { resume in
            jar.setCookiePolicy(.disallow) { resume.resume() }
        }
        let policyDisallowed: Bool = await withCheckedContinuation { resume in
            jar.getCookiePolicy { resume.resume(returning: $0 == .disallow) }
        }
        let records: Bool = await withCheckedContinuation { resume in
            store.fetchDataRecords(ofTypes: [WKWebsiteDataTypeCookies]) { resume.resume(returning: !$0.isEmpty) }
        }
        let cookies: Bool = await withCheckedContinuation { resume in
            jar.getAllCookies { resume.resume(returning: !$0.isEmpty) }
        }
        return ["policyDisallowed": policyDisallowed, "records": records, "cookies": cookies]
    }

    private func observe(_ web: WKWebView, at parent: URL) async throws -> [String: Any] {
        for _ in 0..<95 {
            if web.url == parent,
               let text = try? await web.evaluateJavaScript("JSON.stringify(window.localFramesResult || null)") as? String,
               let result = try? JSONSerialization.jsonObject(with: Data(text.utf8)) as? [String: Any] {
                return result
            }
            try await Task.sleep(nanoseconds: 200_000_000)
        }
        throw FixtureError("The fixture at \(parent) did not report")
    }

    private func measureFrame(kind: String, origin: String, policy: String,
                              store: WKWebsiteDataStore, assets: [String: Data]) async throws -> [String: Any] {
        guard let entry = URL(string: origin + "/entry/" + kind) else {
            throw FixtureError("Invalid fixture URL")
        }
        let loader = FixtureLoader(origin: origin, kind: kind, policy: policy, assets: assets)
        let config = WKWebViewConfiguration()
        config.websiteDataStore = store
        config.setURLSchemeHandler(loader, forURLScheme: "moonpool")
        let web = WKWebView(frame: view.bounds, configuration: config)
        guard let bound = web.configuration.websiteDataStore.identifier, bound == store.identifier else {
            throw FixtureError("Unexpected WebView store binding")
        }

        view.addSubview(web)
        defer {
            web.stopLoading()
            web.removeFromSuperview()
        }
        web.load(URLRequest(url: entry))
        let page = try await observe(web, at: entry)
        return ["store": bound.uuidString, "parentUrl": web.url?.absoluteString ?? "",
                "page": page, "requests": loader.requests, "policies": loader.policies]
    }

    private func measure(mode: String, kinds: [String], assets: [String: Data]) async throws -> [String: Any] {
        let id = UUID()
        let store = WKWebsiteDataStore(forIdentifier: id)
        guard store.identifier == id, store.isPersistent else {
            throw FixtureError("Unexpected identified store for \(mode)")
        }
        let evidence = await inspect(store)
        guard cookiePresence(evidence) == .empty else {
            throw FixtureError("Unverified empty cookie state for \(mode)")
        }
        let origin = "moonpool://com.example.localframes.\(run).\(mode)"
        let selectedPolicy = frameSource == "origin"
            ? guardedPolicy.replacingOccurrences(of: "frame-src 'self'", with: "frame-src \(origin)")
            : guardedPolicy
        let policy = mode == "guarded" ? selectedPolicy : ""
        var frames: [String: Any] = [:]
        for kind in kinds {
            frames[kind] = try await measureFrame(kind: kind, origin: origin, policy: policy, store: store, assets: assets)
        }
        return ["store": id.uuidString, "persistent": store.isPersistent, "cookies": evidence, "frames": frames]
    }

    func runProbe() async {
        var report: [String: Any] = [
            "run": run, "release": UIDevice.current.systemVersion, "pid": Int(ProcessInfo.processInfo.processIdentifier),
            "platform": "ios", "complete": false, "frameSource": frameSource, "documentSet": documentSet,
        ]
        // Keep the never-loaded initializer alive during identified store and cookie operations.
        let warmup = WKWebViewConfiguration()
        warmup.websiteDataStore = .nonPersistent()
        let initializer = WKWebView(frame: .zero, configuration: warmup)
        defer { withExtendedLifetime(initializer) {} }
        report["initializedWebKit"] = true

        var samples: [String: Any] = [:]
        do {
            guard run.range(of: "^ios-[a-z0-9-]{1,24}$", options: .regularExpression) != nil else {
                throw FixtureError("Invalid run tag")
            }
            guard frameSource == "self" || frameSource == "origin" else {
                throw FixtureError("Invalid frame source")
            }
            let kinds: [String]
            switch documentSet {
            case "local": kinds = ["same", "blob", "data"]
            case "inherited": kinds = ["blank", "srcdoc"]
            case "navigation": kinds = ["blank-navigation"]
            default: throw FixtureError("Invalid document set")
            }
            let fixtures = Bundle.main.bundleURL.appendingPathComponent("Fixtures")
            let assets = ["/probe.js": try Data(contentsOf: fixtures.appendingPathComponent("probe.js")),
                          "/worker.js": try Data(contentsOf: fixtures.appendingPathComponent("worker.js"))]
            for mode in ["control", "guarded"] {
                samples[mode] = try await measure(mode: mode, kinds: kinds, assets: assets)
            }
            report["complete"] = true
        } catch {
            report["error"] = error.localizedDescription
        }
        report["samples"] = samples
        do {
            let output = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
                .appendingPathComponent("report.json")
            let bytes = try JSONSerialization.data(withJSONObject: report, options: [.prettyPrinted, .sortedKeys])
            try bytes.write(to: output, options: .atomic)
        } catch {
            NSLog("Failed to save fixture report: %@", error.localizedDescription)
        }
    }
}

@main @MainActor final class AppDelegate: UIResponder, UIApplicationDelegate {
    var window: UIWindow?

    func application(_ application: UIApplication,
                     didFinishLaunchingWithOptions options: [UIApplication.LaunchOptionsKey: Any]? = nil) -> Bool {
        let args = ProcessInfo.processInfo.arguments
        let run = args.firstIndex(of: "--run").flatMap { args.dropFirst($0 + 1).first } ?? ""
        let frameSource = args.firstIndex(of: "--frame-source").flatMap { args.dropFirst($0 + 1).first } ?? "self"
        let documentSet = args.firstIndex(of: "--document-set").flatMap { args.dropFirst($0 + 1).first } ?? "local"
        let controller = FixtureController(run: run, frameSource: frameSource, documentSet: documentSet)
        let window = UIWindow(frame: UIScreen.main.bounds)
        window.rootViewController = controller
        self.window = window
        window.makeKeyAndVisible()
        Task { await controller.runProbe() }
        return true
    }
}
