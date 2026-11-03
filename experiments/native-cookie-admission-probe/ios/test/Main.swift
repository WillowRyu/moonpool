import Foundation

@main @MainActor struct GateMain {
    static func main() throws {
        let data=try JSONSerialization.data(withJSONObject:GateCases.runAll(),options:[.sortedKeys])
        print(String(decoding:data,as:UTF8.self))
    }
}
