func cookiePresence(_ evidence: [String: Bool]) -> AdmissionGate.Presence {
    guard evidence["policyDisallowed"] == true,
          let records = evidence["records"], let cookies = evidence["cookies"],
          records == cookies else {
        return .unknown
    }
    return cookies ? .present : .empty
}
