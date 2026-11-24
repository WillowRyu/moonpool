import Foundation

/// Fixture queue. Submission and completion belong to the native owner.
@MainActor final class StoreOperations {
    typealias Operation = (@escaping () -> Void) -> Void

    private var waiting: [Operation] = []
    private var active: UUID?
    private var pumping = false
    private var closed = false

    @discardableResult
    func submit(_ operation: @escaping Operation) -> Bool {
        guard !closed else { return false }
        waiting.append(operation)
        pump()
        return true
    }

    func close() {
        closed = true
        waiting.removeAll()
        active = nil
    }

    private func pump() {
        guard !pumping else { return }
        pumping = true
        defer { pumping = false }
        while active == nil && !waiting.isEmpty {
            let reservation = UUID()
            active = reservation
            let operation = waiting.removeFirst()
            operation { [weak self] in
                guard let self, self.active == reservation else { return }
                self.active = nil
                self.pump()
            }
        }
    }
}
