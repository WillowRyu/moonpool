import Foundation

@main @MainActor struct CookiePresenceTests {
    static func main() {
        let cases: [([String: Bool], AdmissionGate.Presence)] = [
            (["policyDisallowed": true, "records": false, "cookies": false], .empty),
            (["policyDisallowed": true, "records": true, "cookies": true], .present),
            (["policyDisallowed": true, "records": true, "cookies": false], .unknown),
            (["policyDisallowed": true, "records": false, "cookies": true], .unknown),
            (["policyDisallowed": false, "records": false, "cookies": false], .unknown),
            (["records": false, "cookies": false], .unknown),
            (["policyDisallowed": true, "records": false], .unknown),
            (["policyDisallowed": true, "cookies": false], .unknown),
            (["policyDisallowed": true], .unknown),
        ]
        for (evidence, expected) in cases {
            let result = cookiePresence(evidence)
            guard result == expected else {
                let message = "Expected \(expected), got \(result) for \(evidence)\n"
                FileHandle.standardError.write(Data(message.utf8))
                exit(EXIT_FAILURE)
            }
        }
    }
}
