final class ProbeIdentity {}

@main
struct AdmissionTest {
    static func main() {
        let a = ProbeIdentity()
        let other = ProbeIdentity()
        let origin = ProbeOrigin(scheme: "moonpool", host: "com.example.probe.a", port: 0)
        var checks = 0
        func expect(_ expected: String, sender: AnyObject?, actual: ProbeOrigin? = nil,
                    main: Bool = true, world: String = "page", active: Bool = true) {
            let result = Admission.reason(owner: a, sender: sender, expected: origin,
                actual: actual ?? origin, mainFrame: main, expectedWorld: "page",
                actualWorld: world, active: active)
            precondition(result == expected, "\(expected) != \(result)")
            checks += 1
        }
        expect("accepted", sender: a)
        expect("wrong-view", sender: other)
        expect("wrong-view", sender: nil)
        expect("wrong-origin", sender: a, actual: ProbeOrigin(scheme: "moonpool", host: "com.example.probe.b", port: 0))
        expect("wrong-origin", sender: a, actual: ProbeOrigin(scheme: "https", host: "com.example.probe.a", port: 0))
        expect("wrong-origin", sender: a, actual: ProbeOrigin(scheme: "moonpool", host: "com.example.probe.a", port: 443))
        expect("subframe", sender: a, main: false)
        expect("wrong-world", sender: a, world: "isolated")
        expect("retired", sender: a, active: false)
        expect("retired", sender: other, main: false, world: "isolated", active: false)
        print("\(checks) Swift native-admission checks passed")
    }
}
