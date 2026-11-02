struct ProbeOrigin: Equatable {
    let scheme: String
    let host: String
    let port: Int
}

enum Admission {
    static func reason(owner: AnyObject, sender: AnyObject?, expected: ProbeOrigin,
                       actual: ProbeOrigin, mainFrame: Bool, expectedWorld: String,
                       actualWorld: String, active: Bool) -> String {
        guard active else { return "retired" }
        guard owner === sender else { return "wrong-view" }
        guard expected == actual else { return "wrong-origin" }
        guard mainFrame else { return "subframe" }
        guard expectedWorld == actualWorld else { return "wrong-world" }
        return "accepted"
    }
}
