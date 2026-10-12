// Print every MIDI message the KeyLab sends on its DAW port (read-only; safe
// to run while GarageBand/MainStage are open).
// usage: swift listen-daw-port.swift [seconds]   (default 60)
import CoreMIDI
import Foundation
var client = MIDIClientRef(); MIDIClientCreate("KeyLabListen" as CFString, nil, nil, &client)
var port = MIDIPortRef()
MIDIInputPortCreateWithProtocol(client, "in" as CFString, ._1_0, &port) { list, _ in
  var l = list.pointee; withUnsafeMutablePointer(to: &l.packet) { p0 in var p = p0
    for _ in 0..<list.pointee.numPackets {
      let n = Int(p.pointee.wordCount)
      var out = ""
      withUnsafeBytes(of: p.pointee.words) { raw in
        let ws = raw.bindMemory(to: UInt32.self)
        for i in 0..<min(n, 64) { let w = ws[i]; out += String(format: "[%02X %02X %02X] ", (w >> 16) & 0xFF, (w >> 8) & 0xFF, w & 0xFF) } }
      let t = DateFormatter.localizedString(from: Date(), dateStyle: .none, timeStyle: .medium)
      print(t, out); fflush(stdout)
      p = UnsafeMutablePointer(MIDIEventPacketNext(p)) } } }
func name(_ o: MIDIObjectRef) -> String { var v: Unmanaged<CFString>?; MIDIObjectGetStringProperty(o, kMIDIPropertyDisplayName, &v); return v?.takeRetainedValue() as String? ?? "" }
for i in 0..<MIDIGetNumberOfSources() { let s = MIDIGetSource(i); if name(s).hasPrefix("KeyLab") && name(s).hasSuffix(" DAW") { MIDIPortConnectSource(port, s, nil); print("listening on", name(s)); fflush(stdout) } }
RunLoop.main.run(until: Date().addingTimeInterval(Double(CommandLine.arguments.dropFirst().first ?? "60") ?? 60))
print("done")
