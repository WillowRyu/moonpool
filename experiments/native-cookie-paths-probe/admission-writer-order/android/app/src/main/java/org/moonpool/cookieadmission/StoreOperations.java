package org.moonpool.cookieadmission;

import java.util.ArrayDeque;
import java.util.function.Consumer;

/** Fixture queue. Submission and completion belong to one native owner executor. */
final class StoreOperations {
    private final ArrayDeque<Consumer<Runnable>> waiting = new ArrayDeque<>();
    private Runnable active;
    private boolean pumping;
    private boolean closed;

    void submit(Consumer<Runnable> operation) {
        if (closed) throw new IllegalStateException("The fixture owner is closed");
        waiting.addLast(operation);
        pump();
    }

    void close() {
        closed = true;
        waiting.clear();
        active = null;
    }

    private void pump() {
        if (pumping) return;
        pumping = true;
        try {
            while (active == null && !waiting.isEmpty()) {
                Runnable complete = new Runnable() {
                    @Override public void run() {
                        if (active != this) return;
                        active = null;
                        pump();
                    }
                };
                active = complete;
                waiting.removeFirst().accept(complete);
            }
        } finally {
            pumping = false;
        }
    }
}
