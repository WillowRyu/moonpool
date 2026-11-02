import Foundation

// A single trusted owner serializes registration. This is not a multiprocess registry.
struct StoreAssignment: Codable { let id: String; let uuid: UUID }
enum RegistryFailure: Error { case unsupported, invalidID, lostIdentity, duplicateAssignment, invalidUUID }
struct StoreRegistry {
    let file: URL
    let knownIDs: Set<String>
    var pinned: [String: UUID] = [:]
    var allocate: () -> UUID = UUID.init

    static func requireMetadata(registryExists: Bool, anchorsExist: Bool, available: Set<UUID>) throws {
        guard registryExists || anchorsExist || available.isEmpty else { throw RegistryFailure.lostIdentity }
    }

    static func requireExisting(_ uuid: UUID, known: Bool, available: Set<UUID>) throws {
        guard !known || available.contains(uuid) else { throw RegistryFailure.lostIdentity }
    }

    func resolve(_ id: String, supported: Bool) throws -> UUID {
        guard supported else { throw RegistryFailure.unsupported }
        guard Admission.url(for: id) != nil else { throw RegistryFailure.invalidID }
        var records: [StoreAssignment] = []
        if FileManager.default.fileExists(atPath: file.path) {
            records = try JSONDecoder().decode([StoreAssignment].self, from: Data(contentsOf: file))
        } else if !knownIDs.isEmpty { throw RegistryFailure.lostIdentity }
        let zero = UUID(uuidString: "00000000-0000-0000-0000-000000000000")!
        guard records.allSatisfy({ $0.uuid != zero && Admission.url(for: $0.id) != nil }) else { throw RegistryFailure.invalidUUID }
        guard Set(records.map(\.id)).count == records.count, Set(records.map(\.uuid)).count == records.count else {
            throw RegistryFailure.duplicateAssignment
        }
        guard knownIDs.isSubset(of: Set(records.map(\.id))) else { throw RegistryFailure.lostIdentity }
        guard pinned.allSatisfy({ id, uuid in records.contains(where: { $0.id == id && $0.uuid == uuid }) }) else {
            throw RegistryFailure.lostIdentity
        }
        if let existing = records.first(where: { $0.id == id }) { return existing.uuid }
        let uuid = allocate()
        guard uuid != zero else { throw RegistryFailure.invalidUUID }
        guard !records.contains(where: { $0.uuid == uuid }) else { throw RegistryFailure.duplicateAssignment }
        records.append(StoreAssignment(id: id, uuid: uuid))
        try JSONEncoder().encode(records).write(to: file, options: .atomic)
        return uuid
    }
}
