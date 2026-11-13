import CryptoKit
import Foundation

// Usage: harness self-test|adapter <public_suffix_list.dat> <sha256>
// Status 3 means failed self-test checks. Any other failure is a setup error for check.py.

struct HarnessError: Error, CustomStringConvertible {
    let description: String
    init(_ description: String) { self.description = description }
}

/// Parse only the bytes whose digest matches the profile, so the checked file is the one in use.
func pinnedBytes(path: String, sha256: String) throws -> [UInt8] {
    let bytes = [UInt8](try Data(contentsOf: URL(fileURLWithPath: path)))
    let digest = SHA256.hash(data: bytes).map { String(format: "%02x", $0) }.joined()
    guard digest == sha256 else { throw HarnessError("PSL SHA-256 \(digest) differs from \(sha256)") }
    return bytes
}

let arguments = CommandLine.arguments
guard arguments.count == 4 else {
    FileHandle.standardError.write(Data("usage: harness self-test|adapter <psl> <sha256>\n".utf8))
    exit(2)
}
do {
    let pinned = try pinnedBytes(path: arguments[2], sha256: arguments[3])
    switch arguments[1] {
    case "self-test": exit(try SelfTest().run(pinned))
    case "adapter": try Adapter.run(pinned)
    default: throw HarnessError("unknown command \(arguments[1])")
    }
} catch {
    FileHandle.standardError.write(Data("\(error)\n".utf8))
    exit(2)
}
