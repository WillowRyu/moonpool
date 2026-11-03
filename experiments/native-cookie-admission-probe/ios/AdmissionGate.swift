import Foundation

/// Research-only native owner. It has no cookie mutation, RPC or guest input API.
@MainActor final class AdmissionGate {
    enum Presence { case empty, present, unknown }
    final class Handle {
        let name: String, epoch: Int
        let load: () throws -> Void, retire: () throws -> Void
        var live=true, started=false, completed=false
        init(_ name: String,_ epoch: Int,_ load: @escaping () throws -> Void,_ retire: @escaping () throws -> Void) {
            self.name=name; self.epoch=epoch; self.load=load; self.retire=retire
        }
    }
    typealias Inspector = (String, @escaping (Presence) -> Void) throws -> Void
    let inspector: Inspector
    private var handles:[Handle]=[], busy:Handle?, epoch=0, blocked=false, closed=false
    init(_ inspector: @escaping Inspector) { self.inspector=inspector }
    @discardableResult func admit(_ name:String,load:@escaping () throws -> Void,retire:@escaping () throws -> Void) -> Handle {
        let handle=Handle(name,epoch,load,retire)
        if blocked || closed { handle.live=false; try? handle.retire(); return handle }
        handles.append(handle); pump(); return handle
    }
    func cancel(_ handle:Handle) {
        guard handle.live, let index=handles.firstIndex(where:{$0 === handle}) else { return }
        handles.remove(at:index); handle.live=false; try? handle.retire(); pump()
    }
    func invalidate() {
        guard !blocked else { return }
        blocked=true; epoch+=1
        let old=handles; handles=[]
        for handle in old { handle.live=false }
        for handle in old { try? handle.retire() }
    }
    func close() { guard !closed else { return }; closed=true; invalidate() }
    func retry() { guard !closed else { return }; blocked=false; pump() }
    private func pump() {
        guard !closed, !blocked, busy == nil,
              let handle=handles.first(where:{$0.live && !$0.started}) else { return }
        handle.started=true; busy=handle
        do { try inspector(handle.name) { [weak self] result in self?.complete(handle,result) } }
        catch { complete(handle,.unknown) }
    }
    private func complete(_ handle:Handle,_ result:Presence) {
        guard busy === handle, !handle.completed else { return }
        busy=nil; handle.completed=true
        if !closed && !blocked && handle.live && handle.epoch==epoch {
            switch result {
            case .empty: do { try handle.load() } catch { invalidate() }
            case .present,.unknown: invalidate()
            }
        }
        pump()
    }
}
