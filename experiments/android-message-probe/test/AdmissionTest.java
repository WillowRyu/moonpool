package org.moonpool.messageprobe;

/** Observable native-admission contract, independent of Android runtime classes. */
public final class AdmissionTest {
    private static int checks;
    private static void expect(String expected, Object owner, Object sender, String origin,
                               boolean mainFrame, boolean active) {
        String actual = Admission.reason(owner, sender, "https://com.example.probe.a.test", origin, mainFrame, active);
        if (!expected.equals(actual)) throw new AssertionError(expected + " != " + actual);
        checks++;
    }
    public static void main(String[] args) {
        Object a = new Object();
        Object otherSameOriginView = new Object();
        expect("accepted", a, a, "https://com.example.probe.a.test", true, true);
        expect("wrong-view", a, otherSameOriginView, "https://com.example.probe.a.test", true, true);
        expect("wrong-origin", a, a, "https://com.example.probe.b.test", true, true);
        expect("wrong-origin", a, a, "https://com.example.probe.a.test:444", true, true);
        expect("wrong-origin", a, a, "http://com.example.probe.a.test", true, true);
        expect("wrong-origin", a, a, "null", true, true);
        expect("wrong-origin", a, a, "moonpool://", true, true);
        expect("subframe", a, a, "https://com.example.probe.a.test", false, true);
        expect("retired", a, a, "https://com.example.probe.a.test", true, false);
        expect("retired", a, otherSameOriginView, "https://com.example.probe.b.test", false, false);
        expect("accepted", otherSameOriginView, otherSameOriginView, "https://com.example.probe.a.test", true, true);
        System.out.println(checks + " native-admission contract checks passed");
    }
}
