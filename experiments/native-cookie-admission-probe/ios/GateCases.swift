import Foundation

@MainActor enum GateCases {
    final class Trace { var events:[String]=[] }
    @MainActor final class Rig {
        let trace:Trace
        var callbacks:[(AdmissionGate.Presence)->Void]=[]
        lazy var gate=AdmissionGate { [unowned self] name,done in
            trace.events.append("inspect:"+name); callbacks.append(done)
        }
        init(_ trace:Trace) { self.trace=trace }
        @discardableResult func open(_ name:String) -> AdmissionGate.Handle {
            gate.admit(name,load:{[weak self] in self?.trace.events.append("load:"+name)},retire:{[weak self] in self?.trace.events.append("retire:"+name)})
        }
        func done(_ index:Int,_ value:AdmissionGate.Presence) { callbacks[index](value) }
    }
    static func runAll() -> [String:[String]] {
        var result:[String:[String]]=[:]
        for scenario in ["queued","present","unknown","duplicate","cancel","retry","replacement","cleanup","reentrant"] {
            let trace=Trace(), a=Rig(trace)
            switch scenario {
            case "queued":
                a.open("A1"); a.open("A2"); a.done(0,.empty); a.done(1,.empty)
            case "present":
                a.open("A1"); a.done(0,.empty); a.open("A2"); a.open("A3")
                let b=Rig(trace); b.open("B1"); b.done(0,.empty); a.done(1,.present)
            case "unknown":
                a.open("A1"); a.done(0,.empty); a.open("A2"); a.done(1,.unknown)
            case "duplicate":
                a.open("A1"); a.done(0,.empty); a.open("A2")
                a.done(0,.present); a.done(1,.empty); a.done(1,.empty)
            case "cancel":
                let old=a.open("old"); a.gate.cancel(old); a.open("new"); a.done(0,.empty); a.done(1,.empty)
            case "retry":
                a.open("old"); a.gate.invalidate(); a.gate.retry(); a.open("new"); a.done(0,.present); a.done(1,.empty)
            case "replacement":
                a.open("old"); a.gate.close(); let fresh=Rig(trace); fresh.open("new"); fresh.done(0,.empty)
                a.done(0,.empty); a.gate.retry(); a.open("forbidden")
            case "cleanup":
                a.gate.admit("A1",load:{trace.events.append("load:A1")},retire:{trace.events.append("retire:A1"); throw NSError(domain:"PublicFixture",code:1)})
                a.done(0,.empty); a.open("A2"); a.done(1,.empty); a.gate.invalidate(); a.gate.invalidate()
            case "reentrant":
                a.gate.admit("A1",load:{trace.events.append("load:A1"); a.gate.invalidate()},retire:{trace.events.append("retire:A1")})
                a.open("A2"); a.done(0,.empty)
            default: preconditionFailure(scenario)
            }
            result[scenario]=trace.events
        }
        return result
    }
}
