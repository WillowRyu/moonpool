package org.moonpool.messageprobe;

/** Experimental sender gate only; no capability, protocol or lifecycle policy. */
final class Admission {
    static String reason(Object owner, Object sender, String expectedOrigin, String origin,
                         boolean mainFrame, boolean active) {
        if (!active) return "retired";
        if (owner != sender) return "wrong-view";
        if (!expectedOrigin.equals(origin)) return "wrong-origin";
        if (!mainFrame) return "subframe";
        return "accepted";
    }
}
