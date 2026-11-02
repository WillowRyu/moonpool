// Diagnostic messages are not Moonpool protocol frames or authority claims.
(() => {
  const params = new URLSearchParams(location.search);
  const doc = params.get('doc');
  const inFrame = params.get('frame') === '1';
  const report = {
    doc,
    origin: location.origin,
    href: location.href,
    mainFrame: window === top,
    observerPresent: typeof T25Observe !== 'undefined',
    pinnedPresent: typeof T25Pinned !== 'undefined',
    replies: [],
    frames: [],
    bootstraps: [],
    portReplies: [],
    challengeReceived: false,
    ready: false,
  };
  let proof = null;
  let foreignFrame;
  const render = () => {
    const pre = document.querySelector('pre');
    if (pre) {
      pre.textContent = JSON.stringify(report, null, 2);
    }
  };
  function emit(kind) {
    const data = JSON.stringify({
      kind,
      doc,
      claimedOrigin: 'https://forged.invalid',
      claimedMainFrame: true,
    });
    if (report.observerPresent) {
      T25Observe.postMessage(data);
    }
    if (report.pinnedPresent) {
      T25Pinned.postMessage(data);
    }
  }
  if (report.observerPresent) {
    T25Observe.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.kind === 'challenge') {
        proof = data.value;
        report.challengeReceived = true;
      } else {
        report.replies.push(data);
      }
      render();
    };
  }
  if (report.pinnedPresent) {
    T25Pinned.onmessage = (event) => {
      report.replies.push(JSON.parse(event.data));
      render();
    };
  }
  function usePort(port, label, suppliedProof) {
    port.onmessage = (event) => {
      report.portReplies.push({ label, data: event.data });
      if (inFrame) {
        parent.postMessage(
          { kind: 'delegated-ack', label, data: event.data },
          params.get('parent'),
        );
      }
      render();
    };
    for (let seq = 0; seq < 3; seq++) {
      port.postMessage(
        JSON.stringify({ label, seq, doc, claimedOrigin: location.origin, proof: suppliedProof }),
      );
    }
  }
  addEventListener('message', (event) => {
    const data = typeof event.data === 'string' ? JSON.parse(event.data) : event.data;
    switch (data?.kind) {
      case 'frame-ready': {
        const frame = [...document.querySelectorAll('iframe')].find(
          (item) => item.contentWindow === event.source,
        );
        if (frame) {
          report.frames.push({ ...data, messageOrigin: event.origin });
        }
        break;
      }
      case 'delegated-ack':
        if (event.source !== foreignFrame?.contentWindow) {
          break;
        }
        report.portReplies.push({
          label: data.label,
          data: data.data,
          messageOrigin: event.origin,
        });
        break;
      case 'bootstrap':
        if (event.ports.length !== 1) {
          break;
        }
        report.bootstraps.push(data.label);
        if (data.forward) {
          foreignFrame.contentWindow.postMessage(
            { kind: 'delegated', label: data.label, proof: data.requireProof ? proof : null },
            params.get('other'),
            [event.ports[0]],
          );
        } else {
          usePort(event.ports[0], data.label, data.requireProof ? proof : null);
        }
        break;
      case 'delegated':
        if (event.ports.length !== 1) {
          break;
        }
        // Deliberate adversarial control: the top frame transfers its port and proof.
        emit('delegated-port-received');
        usePort(event.ports[0], data.label, data.proof);
        break;
      default:
        break;
    }
    render();
  });
  window.t25Send = emit;
  window.t25Offer = () => {
    const channel = new MessageChannel();
    channel.port1.onmessage = (event) => {
      report.portReplies.push({ label: 'listener-offer', data: event.data });
      render();
    };
    T25Pinned.postMessage(
      JSON.stringify({
        kind: 'offer',
        doc,
        claimedOrigin: 'https://forged.invalid',
        claimedMainFrame: true,
      }),
      [channel.port2],
    );
    for (let seq = 0; seq < 3; seq++) {
      channel.port1.postMessage(
        JSON.stringify({ label: 'listener-offer', seq, doc, claimedOrigin: location.origin }),
      );
    }
  };
  window.t25Report = report;
  emit('ready');
  addEventListener('DOMContentLoaded', () => {
    if (inFrame) {
      parent.postMessage(
        {
          kind: 'frame-ready',
          doc,
          origin: location.origin,
          observerPresent: report.observerPresent,
          pinnedPresent: report.pinnedPresent,
        },
        params.get('parent'),
      );
    } else {
      for (const [label, origin] of [
        ['self', params.get('self')],
        ['foreign', params.get('other')],
      ]) {
        const frame = document.createElement('iframe');
        const target = new URL(`${origin}/assets/index.html`);
        target.search = new URLSearchParams({
          doc: `${doc}:${label}`,
          frame: '1',
          parent: params.get('self'),
        }).toString();
        frame.src = target.href;
        if (label === 'foreign') {
          foreignFrame = frame;
        }
        document.body.append(frame);
      }
    }
    report.ready = true;
    render();
  });
})();
