package org.moonpool.cookieadmission;

import java.util.ArrayList;
import java.util.List;
import java.util.function.Consumer;

/** Research-only gate. All calls and completions use one native owner executor. */
final class AdmissionGate {
 enum Presence { EMPTY, PRESENT, UNKNOWN }
 interface Inspector { void inspect(String name, Consumer<Presence> complete); }
 static final class Handle {
  final String name;
  final Runnable load, retire;
  final long epoch;
  boolean live=true, started=false, completed=false;
  Handle(String name, long epoch, Runnable load, Runnable retire) {
   this.name=name; this.epoch=epoch; this.load=load; this.retire=retire;
  }
 }
 private final Inspector inspector;
 private final List<Handle> handles=new ArrayList<>();
 private Handle busy;
 private long epoch;
 private boolean blocked, closed;
 AdmissionGate(Inspector inspector) { this.inspector=inspector; }
 Handle admit(String name, Runnable load, Runnable retire) {
  Handle handle=new Handle(name,epoch,load,retire);
  if (blocked || closed) { handle.live=false; cleanup(handle); return handle; }
  handles.add(handle); pump(); return handle;
 }
 void cancel(Handle handle) {
  if (!handles.remove(handle) || !handle.live) return;
  handle.live=false; cleanup(handle); pump();
 }
 void invalidate() {
  if (blocked) return;
  blocked=true; epoch++;
  List<Handle> old=new ArrayList<>(handles); handles.clear();
  for (Handle handle:old) handle.live=false;
  for (Handle handle:old) cleanup(handle);
 }
 void close() { if (closed) return; closed=true; invalidate(); }
 void retry() { if (closed) return; blocked=false; pump(); }
 private void cleanup(Handle handle) {
  try { handle.retire.run(); } catch (RuntimeException ignored) { /* Attempt every owned cleanup. */ }
 }
 private void pump() {
  if (closed || blocked || busy!=null) return;
  for (Handle handle:handles) {
   if (!handle.live || handle.started) continue;
   handle.started=true; busy=handle;
   try { inspector.inspect(handle.name,result -> complete(handle,result)); }
   catch (RuntimeException ignored) { complete(handle,Presence.UNKNOWN); }
   return;
  }
 }
 private void complete(Handle handle, Presence presence) {
  if (busy!=handle || handle.completed) return;
  busy=null; handle.completed=true;
  if (!closed && !blocked && handle.live && handle.epoch==epoch) {
   if (presence==Presence.EMPTY) {
    try { handle.load.run(); } catch (RuntimeException ignored) { invalidate(); }
   } else { invalidate(); }
  }
  pump();
 }
}
