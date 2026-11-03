package org.moonpool.cookieadmission;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.function.Consumer;

/** Controlled callbacks; traces are checked independently by the Python oracle. */
public final class GateCases {
 static final class Rig {
  final List<String> events;
  final List<Consumer<AdmissionGate.Presence>> callbacks=new ArrayList<>();
  final AdmissionGate gate;
  Rig(List<String> events) {
   this.events=events;
   gate=new AdmissionGate((name,done) -> { events.add("inspect:"+name); callbacks.add(done); });
  }
  AdmissionGate.Handle open(String name) { return gate.admit(name,() -> events.add("load:"+name),() -> events.add("retire:"+name)); }
  void done(int index, AdmissionGate.Presence value) { callbacks.get(index).accept(value); }
 }
 public static Map<String,List<String>> runAll() {
  Map<String,List<String>> result=new LinkedHashMap<>();
  for (String scenario:new String[]{"queued","present","unknown","duplicate","cancel","retry","replacement","cleanup","reentrant"}) {
   List<String> events=new ArrayList<>(); Rig a=new Rig(events);
   switch (scenario) {
    case "queued":
     a.open("A1"); a.open("A2"); a.done(0,AdmissionGate.Presence.EMPTY); a.done(1,AdmissionGate.Presence.EMPTY); break;
    case "present":
     a.open("A1"); a.done(0,AdmissionGate.Presence.EMPTY); a.open("A2"); a.open("A3");
     Rig b=new Rig(events); b.open("B1"); b.done(0,AdmissionGate.Presence.EMPTY);
     a.done(1,AdmissionGate.Presence.PRESENT); break;
    case "unknown":
     a.open("A1"); a.done(0,AdmissionGate.Presence.EMPTY); a.open("A2"); a.done(1,AdmissionGate.Presence.UNKNOWN); break;
    case "duplicate":
     a.open("A1"); a.done(0,AdmissionGate.Presence.EMPTY); a.open("A2");
     a.done(0,AdmissionGate.Presence.PRESENT); a.done(1,AdmissionGate.Presence.EMPTY); a.done(1,AdmissionGate.Presence.EMPTY); break;
    case "cancel":
     AdmissionGate.Handle old=a.open("old"); a.gate.cancel(old); a.open("new");
     a.done(0,AdmissionGate.Presence.EMPTY); a.done(1,AdmissionGate.Presence.EMPTY); break;
    case "retry":
     a.open("old"); a.gate.invalidate(); a.gate.retry(); a.open("new");
     a.done(0,AdmissionGate.Presence.PRESENT); a.done(1,AdmissionGate.Presence.EMPTY); break;
    case "replacement":
     a.open("old"); a.gate.close(); Rig fresh=new Rig(events); fresh.open("new"); fresh.done(0,AdmissionGate.Presence.EMPTY);
     a.done(0,AdmissionGate.Presence.EMPTY); a.gate.retry(); a.open("forbidden"); break;
    case "cleanup":
     a.gate.admit("A1",() -> events.add("load:A1"),() -> { events.add("retire:A1"); throw new IllegalStateException("Public injected cleanup failure"); });
     a.done(0,AdmissionGate.Presence.EMPTY); a.open("A2"); a.done(1,AdmissionGate.Presence.EMPTY);
     a.gate.invalidate(); a.gate.invalidate(); break;
    case "reentrant":
     a.gate.admit("A1",() -> { events.add("load:A1"); a.gate.invalidate(); },() -> events.add("retire:A1"));
     a.open("A2"); a.done(0,AdmissionGate.Presence.EMPTY); break;
    default: throw new IllegalArgumentException(scenario);
   }
   result.put(scenario,events);
  }
  return result;
 }
 public static void main(String[] args) {
  runAll().forEach((name,events) -> System.out.println(name+"\t"+String.join("|",events)));
 }
}
