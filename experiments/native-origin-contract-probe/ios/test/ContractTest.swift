import Foundation

@main
struct ContractTest {
    static func main() throws {
        let a = "com.example.probe.a"
        precondition(Admission.url(for: a)?.absoluteString == "moonpool://\(a)/")
        for invalid in ["", "com", "Com.example", "com..a", "com.example/a", "com.example:9", "com.example@a", "com.example%2ea", "com.example.a.", "com.example_a"] {
            precondition(Admission.url(for: invalid) == nil, "Invalid id admitted: \(invalid)")
        }
        for valid in ["1.2", "com.-", "com.a-", "com.-a", "com." + String(repeating: "x", count: 64), String(repeating: "a", count: 260) + ".z"] {
            precondition(Admission.url(for: valid)?.host == valid)
        }
        let file = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: file) }
        let first = try StoreRegistry(file: file, knownIDs: []).resolve(a, supported: true)
        precondition(first.uuidString != "00000000-0000-0000-0000-000000000000")
        let retained = try StoreRegistry(file: file, knownIDs: [a]).resolve(a, supported: true)
        precondition(retained == first)
        func rejects(_ name: String, _ action: () throws -> Void) {
            do { try action(); preconditionFailure("Accepted \(name)") } catch { }
        }
        rejects("unsupported API (simulated)") { _ = try StoreRegistry(file: file, knownIDs: [a]).resolve(a, supported: false) }
        rejects("collision") { _ = try StoreRegistry(file: file, knownIDs: [a], allocate: { first }).resolve("com.example.probe.b", supported: true) }
        let b = "com.example.probe.b"
        func write(_ values: [StoreAssignment]) throws { try JSONEncoder().encode(values).write(to: file, options: .atomic) }
        try write([StoreAssignment(id: a, uuid: first), StoreAssignment(id: a, uuid: UUID())])
        rejects("duplicate ids") { _ = try StoreRegistry(file: file, knownIDs: [a]).resolve(a, supported: true) }
        try write([StoreAssignment(id: a, uuid: first), StoreAssignment(id: b, uuid: first)])
        rejects("duplicate UUIDs") { _ = try StoreRegistry(file: file, knownIDs: [a]).resolve(a, supported: true) }
        try write([StoreAssignment(id: a, uuid: UUID(uuidString: "00000000-0000-0000-0000-000000000000")!)])
        rejects("zero UUID") { _ = try StoreRegistry(file: file, knownIDs: [a]).resolve(a, supported: true) }
        try write([])
        rejects("missing assignment") { _ = try StoreRegistry(file: file, knownIDs: [a]).resolve(a, supported: true) }
        try FileManager.default.removeItem(at: file)
        rejects("lost registry") { _ = try StoreRegistry(file: file, knownIDs: [a]).resolve(a, supported: true) }
        rejects("invalid registry id") { _ = try StoreRegistry(file: file, knownIDs: []).resolve("COM.a", supported: true) }
        try write([StoreAssignment(id: a, uuid: first)])
        rejects("remapped assignment") { _ = try StoreRegistry(file: file, knownIDs: [a], pinned: [a: UUID()]).resolve(a, supported: true) }
        rejects("actual identified store lost (simulated)") { try StoreRegistry.requireExisting(first, known: true, available: []) }
        try StoreRegistry.requireExisting(first, known: true, available: [first])
        rejects("complete metadata loss with retained stores (simulated)") { try StoreRegistry.requireMetadata(registryExists: false, anchorsExist: false, available: [first]) }
        try StoreRegistry.requireMetadata(registryExists: false, anchorsExist: false, available: [])
        precondition(Admission.accepts(a, scheme: "moonpool", host: a, port: 0))
        precondition(!Admission.accepts(a, scheme: "https", host: a, port: 0))
        precondition(!Admission.accepts(a, scheme: "moonpool", host: "com.example.probe.b", port: 0))
        precondition(!Admission.accepts(a, scheme: "moonpool", host: a, port: 443))
        precondition(!Admission.accepts("com.%61", scheme: "moonpool", host: "com.a", port: 0))
        print("37 admission/registry checks passed")
    }
}
