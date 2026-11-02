package org.moonpool.origincontract;
public final class RegistrationTest {
 public static void main(String[] args) throws Exception {
  Registration a = Registration.derive("com.example.a");
  if (!a.origin.equals("https://mp-ise6u4clw7owqxvnnmc5dvgub5ktylulowmifvqmtnv6o2stnqcq.invalid")) throw new AssertionError(a.origin);
  Registration.derive("com.-");
  Registration numeric = Registration.derive("123.456");
  Registration hyphen = Registration.derive("com.example.hyphen-app");
  Registration longId = Registration.derive("a".repeat(200) + "." + "b".repeat(100));
  for (Registration r : new Registration[]{a, numeric, hyphen, longId}) {
   if (r.key.length() != 52 || !r.key.matches("[a-z2-7]{52}") || !r.profile.equals("moonpool-v1-" + r.key)) throw new AssertionError(r.id);
  }
  expectReject(() -> Registration.admit(false, a, null, false));
  expectReject(() -> Registration.admit(true, a, null, true));
  expectReject(() -> Registration.admit(true, a, "wrong-profile", true));
  expectReject(() -> Registration.admit(true, a, a.profile, false));
  Registration.admit(true, a, a.profile, true);
  expectReject(() -> Registration.unique(a, a.origin, "other.app", a.profile));
  expectReject(() -> Registration.unique(a, "https://different.invalid", a.id, a.profile));
  int vectors = 0;
  if (args.length == 1) for (String row : java.nio.file.Files.readAllLines(java.nio.file.Path.of(args[0]))) {
   String[] fields = row.split("\\t", -1);
   try {
    Registration r = Registration.derive(fields[1]);
    if (!fields[0].equals("true") || !r.key.equals(fields[2]) || !r.origin.equals(fields[3]) || !r.profile.equals(fields[4])) throw new AssertionError("Vector: " + fields[1]);
   } catch (IllegalArgumentException error) { if (fields[0].equals("true")) throw error; }
   vectors++;
  }
  if (args.length == 1 && vectors != 23) throw new AssertionError("Missing reference vectors");
  System.out.println("Reference vectors checked: " + vectors);
  System.out.println("Mapping/admission suite passed (unsupported gate is simulated).");
 }
 private static void expectReject(Runnable action) {
  try { action.run(); } catch (IllegalStateException expected) { return; }
  throw new AssertionError("Admission must reject before load");
 }
}
