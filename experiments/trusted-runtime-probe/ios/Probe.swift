import UIKit
import JavaScriptCore

// Experimental engine owner only; no guest WebView or production provider API.
final class EngineOwner {
    let name: String
    let queue: DispatchQueue
    let queueKey = DispatchSpecificKey<Bool>()
    var context: JSContext?
    var machine: JSVirtualMachine?
    var active = true
    let note: (String, String) -> Void

    init(name: String, note: @escaping (String, String) -> Void) {
        self.name = name; self.note = note
        queue = DispatchQueue(label: "moonpool.t27.\(name)")
        queue.setSpecific(key: queueKey, value: true)
    }
    func start(config: String, complete: @escaping (String, Bool) -> Void) {
        queue.async {
            self.note(self.name, DispatchQueue.getSpecific(key: self.queueKey) == true && !Thread.isMainThread ? "owner-executor-confirmed" : "wrong-executor")
            self.machine = JSVirtualMachine()
            self.context = JSContext(virtualMachine: self.machine)
            self.context?.exceptionHandler = { [weak self] _, _ in self?.note(self?.name ?? "retired", "engine-exception") }
            let guest = JSContext(virtualMachine: JSVirtualMachine())!
            let isolated = guest.evaluateScript("typeof __t27")?.toString() == "undefined"
            let fixtures = Bundle.main.bundleURL.appendingPathComponent("Fixtures")
            for name in ["timer-adapter.js", "kernel-probe.js"] {
                let source = try! String(contentsOf: fixtures.appendingPathComponent(name), encoding: .utf8)
                self.context?.evaluateScript(source, withSourceURL: URL(string: "moonpool-host://trusted/\(name)")!)
            }
            let text = Self.quote(config)
            self.context?.evaluateScript("__t27.start(\(text))")
            self.poll(remaining: 400, isolated: isolated, complete: complete)
        }
    }
    private func poll(remaining: Int, isolated: Bool, complete: @escaping (String, Bool) -> Void) {
        guard active else { return }
        context?.evaluateScript("__t27Scheduler.tick()")
        let text = context?.evaluateScript("__t27.report()")?.toString() ?? "{}"
        let data = text.data(using: .utf8)!
        let report = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any]
        if report?["complete"] as? Bool == true || remaining == 0 { complete(text, isolated); return }
        queue.asyncAfter(deadline: .now() + 0.005) { self.poll(remaining: remaining - 1, isolated: isolated, complete: complete) }
    }
    func close(done: @escaping (String) -> Void) {
        queue.async {
            let text = self.context?.evaluateScript("__t27.close(); __t27Scheduler.clear(); JSON.stringify(__t27Scheduler.snapshot())")?.toString() ?? "{}"
            self.active = false
            self.context = nil; self.machine = nil
            done(text)
            // A scheduled native control keeps its original owner; it never
            // looks up whichever engine the UI might currently call active.
            self.queue.asyncAfter(deadline: .now() + 0.04) {
                guard self.active else { self.note(self.name, "late-control-dropped"); return }
                self.note(self.name, "late-control-unexpectedly-active")
            }
        }
    }
    static func quote(_ text: String) -> String {
        let bytes = try! JSONSerialization.data(withJSONObject: [text])
        let encoded = String(data: bytes, encoding: .utf8)!
        return String(encoded.dropFirst().dropLast())
    }
}

@MainActor
final class RuntimeController: UIViewController {
    let run: String
    let status = UILabel()
    var owners: [EngineOwner] = []
    var samples: [[String: Any]] = []
    var events: [[String: Any]] = []
    var snapshots: [String: String] = [:]
    var index = 0
    let cases = [("a-first", "com.example.runtime.a", "saved-A"),
                 ("a-recreated", "com.example.runtime.a", ""),
                 ("b-independent", "com.example.runtime.b", "saved-B")]
    var output: URL { FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0].appendingPathComponent("report.json") }
    init(run: String) { self.run = run; super.init(nibName: nil, bundle: nil) }
    required init?(coder: NSCoder) { fatalError("Programmatic probe") }
    override func viewDidLoad() {
        super.viewDidLoad(); view.backgroundColor = .systemBackground
        try? FileManager.default.removeItem(at: output)
        status.translatesAutoresizingMaskIntoConstraints = false; status.numberOfLines = 8; status.font = .systemFont(ofSize: 19)
        view.addSubview(status)
        NSLayoutConstraint.activate([status.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 20),
            status.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -20),status.centerYAnchor.constraint(equalTo: view.centerYAnchor)])
        next()
    }
    func next() {
        if index == cases.count {
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.15) { self.finish() }; return
        }
        let (name, app, write) = cases[index]; index += 1
        status.text = "T27 JavaScriptCore / \(run) / \(name)\nPrivate runtime on its serial queue"
        var config: [String: Any] = ["appId": app, "platform": "ios", "initialValue": snapshots[app] ?? NSNull()]
        if !write.isEmpty { config["writeValue"] = write }
        let data = try! JSONSerialization.data(withJSONObject: config, options: [.sortedKeys])
        let owner = EngineOwner(name: name) { [weak self] name, type in
            DispatchQueue.main.async { self?.events.append(["owner": name, "type": type]) }
        }
        owners.append(owner)
        owner.start(config: String(data: data, encoding: .utf8)!) { [weak self] text, isolated in
            DispatchQueue.main.async {
                guard let self else { return }
                let data = text.data(using: .utf8)!
                let value = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any] ?? [:]
                if let stored = value["storedValue"] as? String { self.snapshots[app] = stored }
                owner.close { scheduler in
                    DispatchQueue.main.async {
                        self.samples.append(["name": name, "appId": app, "common": value,
                            "guestProbeGlobalAbsent": isolated, "schedulerAfterClose": scheduler])
                        self.next()
                    }
                }
            }
        }
    }
    func finish() {
        let report: [String: Any] = ["platform": "ios", "engine": "JavaScriptCore", "run": run,
            "os": UIDevice.current.systemVersion, "executor": "one serial queue per runtime owner",
            "samples": samples, "events": events, "complete": true,
            "providerScope": "JS provider test doubles; native snapshot seeding only"]
        let bytes = try! JSONSerialization.data(withJSONObject: report, options: [.prettyPrinted, .sortedKeys])
        try! bytes.write(to: output, options: .atomic)
        status.text = "T27 JavaScriptCore / \(run) complete\n3 retired private runtime owners\nCommon real-kernel vectors executed"
    }
}

@main
@MainActor
final class RuntimeApp: UIResponder, UIApplicationDelegate {
    var window: UIWindow?
    func application(_ application: UIApplication, didFinishLaunchingWithOptions options: [UIApplication.LaunchOptionsKey: Any]? = nil) -> Bool {
        let args = ProcessInfo.processInfo.arguments; let run = args[args.firstIndex(of: "--run")! + 1]
        precondition(["first", "repeat"].contains(run))
        let window = UIWindow(frame: UIScreen.main.bounds); window.rootViewController = RuntimeController(run: run)
        self.window = window; window.makeKeyAndVisible(); return true
    }
}
