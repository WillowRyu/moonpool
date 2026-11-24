package org.moonpool.cookieadmission;

import java.util.ArrayList;
import java.util.List;

public final class StoreOperationsCases {
    public static void main(String[] args) {
        StoreOperations operations = new StoreOperations();
        List<String> started = new ArrayList<>();
        List<Runnable> completions = new ArrayList<>();
        for (String name : List.of("admission", "write", "next admission")) {
            operations.submit(done -> {
                started.add(name);
                completions.add(done);
            });
        }
        require(started.equals(List.of("admission")), "The writer entered an unfinished admission");
        completions.get(0).run();
        require(started.equals(List.of("admission", "write")), "The writer did not start after admission");
        completions.get(0).run();
        require(started.equals(List.of("admission", "write")), "A stale completion released the writer");
        completions.get(1).run();
        require(started.equals(List.of("admission", "write", "next admission")), "The next admission did not start");

        operations.submit(done -> started.add("late write"));
        operations.close();
        completions.get(2).run();
        require(started.equals(List.of("admission", "write", "next admission")), "Closing released a queued write");
    }

    private static void require(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }
}
