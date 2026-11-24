import Foundation

@main @MainActor struct StoreOperationsCases {
    static func main() {
        let operations = StoreOperations()
        var started: [String] = []
        var completions: [() -> Void] = []
        for name in ["admission", "write", "next admission"] {
            require(operations.submit { done in
                started.append(name)
                completions.append(done)
            }, "The open owner refused a request")
        }
        require(started == ["admission"], "The writer entered an unfinished admission")
        completions[0]()
        require(started == ["admission", "write"], "The first completion did not release the writer")
        completions[0]()
        require(started == ["admission", "write"], "A stale completion released the writer")
        completions[1]()
        require(started == ["admission", "write", "next admission"], "The next admission did not start")
        require(operations.submit { _ in started.append("late write") }, "The open owner refused a request")
        operations.close()
        completions[2]()
        require(!operations.submit { _ in started.append("post-close write") }, "The closed owner accepted a request")
        require(started == ["admission", "write", "next admission"], "A write started after close")
    }

    private static func require(_ condition: Bool, _ message: String) {
        if !condition {
            FileHandle.standardError.write(Data("\(message)\n".utf8))
            exit(EXIT_FAILURE)
        }
    }
}
