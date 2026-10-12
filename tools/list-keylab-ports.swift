// List the Arturia device's MIDI ports: the endpoint name (what scripts must use,
// e.g. 'DAW') and the display name macOS shows (e.g. 'KeyLab 61 mk3 DAW').
// usage: swift list-keylab-ports.swift
import CoreMIDI
func s(_ o: MIDIObjectRef, _ k: CFString) -> String { var v: Unmanaged<CFString>?; return MIDIObjectGetStringProperty(o, k, &v) == 0 ? v!.takeRetainedValue() as String : "-" }
for d in 0..<MIDIGetNumberOfDevices() { let dev = MIDIGetDevice(d); guard s(dev,kMIDIPropertyManufacturer)=="Arturia" else {continue}
  for e in 0..<MIDIDeviceGetNumberOfEntities(dev) { let ent = MIDIDeviceGetEntity(dev,e)
    for x in 0..<MIDIEntityGetNumberOfSources(ent) { let p=MIDIEntityGetSource(ent,x); print("src name='\(s(p,kMIDIPropertyName))' display='\(s(p,kMIDIPropertyDisplayName))'") }
    for x in 0..<MIDIEntityGetNumberOfDestinations(ent) { let p=MIDIEntityGetDestination(ent,x); print("dst name='\(s(p,kMIDIPropertyName))' display='\(s(p,kMIDIPropertyDisplayName))'") } } }
