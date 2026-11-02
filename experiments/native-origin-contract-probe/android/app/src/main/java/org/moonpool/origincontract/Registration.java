package org.moonpool.origincontract;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.net.URI;

/** Probe-only implementation of the proposed mapping, not a production registry. */
public final class Registration {
 public final String id, key, origin, profile;
 private Registration(String id, String key) {
  this.id = id; this.key = key;
  origin = "https://mp-" + key + ".invalid";
  profile = "moonpool-v1-" + key;
  URI uri = URI.create(origin);
  if (!"https".equals(uri.getScheme()) || !uri.getHost().equals("mp-" + key + ".invalid") || uri.getPort() != -1) throw new IllegalArgumentException("Origin roundtrip");
 }
 public static Registration derive(String id) {
  if (!id.matches("[a-z0-9]+(\\.[a-z0-9-]+)+")) throw new IllegalArgumentException("Exact ASCII id required");
  try {
   byte[] hash = MessageDigest.getInstance("SHA-256").digest(id.getBytes(StandardCharsets.US_ASCII));
   String alphabet = "abcdefghijklmnopqrstuvwxyz234567";
   StringBuilder key = new StringBuilder();
   int bits = 0, buffer = 0;
   for (byte item : hash) {
    buffer = (buffer << 8) | (item & 255); bits += 8;
    while (bits >= 5) { bits -= 5; key.append(alphabet.charAt((buffer >>> bits) & 31)); }
   }
   if (bits > 0) key.append(alphabet.charAt((buffer << (5 - bits)) & 31));
   return new Registration(id, key.toString());
  } catch (java.security.NoSuchAlgorithmException impossible) { throw new IllegalStateException(impossible); }
 }
 public static void admit(boolean supported, Registration expected, String storedProfile, boolean profileExists) {
  if (!supported) throw new IllegalStateException("MULTI_PROFILE unavailable");
  if (storedProfile == null) throw new IllegalStateException("Registration metadata missing");
  if (!expected.profile.equals(storedProfile)) throw new IllegalStateException("Registration remap");
  if (!profileExists) throw new IllegalStateException("Registered profile missing");
 }
 public static void unique(Registration expected, String storedOrigin, String storedId, String storedProfile) {
  if (!expected.id.equals(storedId) || !expected.origin.equals(storedOrigin) || !expected.profile.equals(storedProfile)) throw new IllegalStateException("Collision or remap");
 }
}
