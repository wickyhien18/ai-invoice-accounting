import { useEffect, useRef, useState } from "react";
import { fetchBlobUrl } from "../../api/client.js";

// Khung xem file goc DUNG CHUNG cho anh, PDF va XML: cung mot thanh cong cu (− % +, Vua khung, Xoay trai, Xoay phai)
// va cung nen/vien nen che do sang/toi khop nhau. Anh va PDF deu duoc ve len <canvas> nen phong to/xoay giong het nhau
// (khong dung trinh xem PDF cua trinh duyet vi no co thanh cong cu rieng, khong dong bo duoc).
// Thu vien pdf.js duoc nap luc chay tu CDN (khong them goi npm vao du an); neu khong nap duoc (mat mang) thi quay ve
// trinh xem PDF san co cua trinh duyet.
const PDFJS = "4.10.38";
const PDFJS_BASES = [
  `https://cdn.jsdelivr.net/npm/pdfjs-dist@${PDFJS}/build/`,
  `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${PDFJS}/`,
];
let pdfjsPromise = null;
function loadPdfjs() {
  if (!pdfjsPromise) {
    pdfjsPromise = (async () => {
      let last;
      for (const base of PDFJS_BASES) {
        try {
          const lib = await import(/* @vite-ignore */ base + "pdf.min.mjs");
          const code = await (await fetch(base + "pdf.worker.min.mjs")).text();
          lib.GlobalWorkerOptions.workerSrc = URL.createObjectURL(new Blob([code], { type: "text/javascript" }));
          return lib;
        } catch (e) { last = e; }
      }
      throw last;
    })();
    pdfjsPromise.catch(() => { pdfjsPromise = null; });
  }
  return pdfjsPromise;
}

const ZMIN = 0.5, ZMAX = 4, ZSTEP = 0.25;
const btn = "rounded border border-slate-300 bg-white px-2 py-1 text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-40";

function Toolbar({ label, zoom, setZoom, rot, setRot, extra }) {
  return (
    <div className="flex flex-wrap items-center gap-2 border-b border-slate-200 bg-white px-3 py-2 text-sm">
      <span className="mr-auto min-w-0 max-w-full truncate font-medium text-slate-700" title={label}>{label}</span>
      <div className="flex items-center gap-1">
        <button type="button" className={btn} aria-label="Thu nhỏ" onClick={() => setZoom((z) => Math.max(ZMIN, +(z - ZSTEP).toFixed(2)))} disabled={zoom <= ZMIN}>−</button>
        <span className="w-12 text-center tabular-nums text-slate-700">{Math.round(zoom * 100)}%</span>
        <button type="button" className={btn} aria-label="Phóng to" onClick={() => setZoom((z) => Math.min(ZMAX, +(z + ZSTEP).toFixed(2)))} disabled={zoom >= ZMAX}>+</button>
        <button type="button" className={btn} onClick={() => setZoom(1)}>Vừa khung</button>
      </div>
      {setRot && (
        <div className="flex items-center gap-1">
          <button type="button" className={btn} onClick={() => setRot((r) => (r + 270) % 360)} title="Xoay trái 90°">⟲ Xoay trái</button>
          <button type="button" className={btn} onClick={() => setRot((r) => (r + 90) % 360)} title="Xoay phải 90°">⟳ Xoay phải</button>
        </div>
      )}
      {extra}
    </div>
  );
}

// Ve mot trang (anh hoac trang PDF) len canvas theo be rong hien thi, goc xoay.
function CanvasPage({ item, width, rot }) {
  const ref = useRef(null);
  const [h, setH] = useState(Math.round(width * 1.3));
  useEffect(() => {
    let task = null, dead = false;
    const cv = ref.current;
    if (!cv || width < 50) return undefined;
    const dpr = Math.min(window.devicePixelRatio || 1, 4096 / Math.max(width, 1), 3);
    (async () => {
      if (item.img) {
        const im = item.img, swap = rot % 180 !== 0;
        const nw = swap ? im.naturalHeight : im.naturalWidth, nh = swap ? im.naturalWidth : im.naturalHeight;
        const cssH = width * nh / nw;
        cv.width = Math.round(width * dpr); cv.height = Math.round(cssH * dpr);
        const ctx = cv.getContext("2d");
        ctx.translate(cv.width / 2, cv.height / 2); ctx.rotate((rot * Math.PI) / 180);
        const dw = (swap ? cv.height : cv.width), dh = (swap ? cv.width : cv.height);
        ctx.drawImage(im, -dw / 2, -dh / 2, dw, dh);
        if (!dead) setH(cssH);
      } else {
        const p = item.page, r = (p.rotate + rot) % 360;
        const base = p.getViewport({ scale: 1, rotation: r });
        const vp = p.getViewport({ scale: (width * dpr) / base.width, rotation: r });
        cv.width = Math.round(vp.width); cv.height = Math.round(vp.height);
        if (!dead) setH(vp.height / dpr);
        task = p.render({ canvasContext: cv.getContext("2d"), viewport: vp });
        await task.promise.catch(() => {});
      }
    })();
    return () => { dead = true; if (task) task.cancel(); };
  }, [item, width, rot]);
  return <canvas ref={ref} style={{ width, height: h }} className="mx-auto block max-w-none rounded-sm bg-white shadow-md" />;
}

// --- XML: hien dang cay co thut le, to mau, de doc thay cho mot dong dai ---
function XmlNode({ n }) {
  if (n.nodeType === 8) return <div className="italic text-slate-500">{`<!--${n.nodeValue}-->`}</div>;
  if (n.nodeType !== 1) return null;
  const attrs = [...n.attributes].map((a) => (
    <span key={a.name}> <span className="text-amber-700">{a.name}</span>=<span className="text-green-700">"{a.value}"</span></span>
  ));
  const kids = [...n.childNodes].filter((c) => c.nodeType === 1 || c.nodeType === 8);
  const text = [...n.childNodes].filter((c) => c.nodeType === 3 || c.nodeType === 4).map((c) => c.nodeValue).join("").trim();
  const open = <span className="text-blue-700">&lt;{n.nodeName}{attrs}</span>;
  const close = <span className="text-blue-700">&lt;/{n.nodeName}&gt;</span>;
  if (!kids.length) {
    return text
      ? <div className="break-words">{open}<span className="text-blue-700">&gt;</span><b className="font-semibold text-slate-900">{text}</b>{close}</div>
      : <div>{open}<span className="text-blue-700"> /&gt;</span></div>;
  }
  return (
    <div>
      <div>{open}<span className="text-blue-700">&gt;</span></div>
      <div className="ml-3 border-l border-slate-300 pl-3">{kids.map((k, i) => <XmlNode key={i} n={k} />)}</div>
      <div>{close}</div>
    </div>
  );
}

function XmlView({ text, zoom, raw }) {
  let root = null;
  if (!raw) {
    const doc = new DOMParser().parseFromString(text, "application/xml");
    if (!doc.querySelector("parsererror")) root = [...doc.childNodes].filter((c) => c.nodeType === 1 || c.nodeType === 8);
  }
  return (
    <div className="mx-auto min-h-full w-full rounded-sm bg-white p-4 font-mono shadow-md" style={{ fontSize: 13 * zoom, lineHeight: 1.6 }}>
      {root ? root.map((n, i) => <XmlNode key={i} n={n} />) : <pre className="whitespace-pre-wrap break-all">{text}</pre>}
    </div>
  );
}

export default function FileViewer({ invoiceId, fileType, filename }) {
  const [state, setState] = useState({ status: "load" });   // load | err | ready
  const [zoom, setZoom] = useState(1);
  const [rot, setRot] = useState(0);
  const [raw, setRaw] = useState(false);
  const [width, setWidth] = useState(0);
  const area = useRef(null);

  useEffect(() => {
    let dead = false, url = null;
    setState({ status: "load" }); setZoom(1); setRot(0); setRaw(false);
    (async () => {
      try {
        url = await fetchBlobUrl(`/api/invoices/${invoiceId}/file`);
        if (dead) return;
        if (fileType === "xml") {
          setState({ status: "ready", kind: "xml", text: await (await fetch(url)).text() });
        } else if (fileType === "pdf") {
          try {
            const lib = await loadPdfjs();
            const pdf = await lib.getDocument({ data: new Uint8Array(await (await fetch(url)).arrayBuffer()) }).promise;
            const pages = [];
            for (let i = 1; i <= pdf.numPages; i++) pages.push({ page: await pdf.getPage(i) });
            if (!dead) setState({ status: "ready", kind: "pdf", items: pages });
          } catch {
            if (!dead) setState({ status: "ready", kind: "pdf-native", url });   // khong nap duoc pdf.js
          }
        } else {
          const img = new Image(); img.src = url; await img.decode();
          if (!dead) setState({ status: "ready", kind: "img", items: [{ img }] });
        }
      } catch (e) { if (!dead) setState({ status: "err", msg: e.message }); }
    })();
    return () => { dead = true; if (url) setTimeout(() => URL.revokeObjectURL(url), 0); };
  }, [invoiceId, fileType]);

  // be rong kha dung theo khung (de "Vua khung" luon vua be rong, ke ca khi keo thanh chia doi)
  useEffect(() => {
    const el = area.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setWidth(Math.max(160, el.clientWidth - 24)));
    ro.observe(el); setWidth(Math.max(160, el.clientWidth - 24));
    return () => ro.disconnect();
  }, [state.status, state.kind]);

  if (state.status === "err") return <p className="p-4 text-sm text-red-600">Không mở được file gốc: {state.msg}</p>;
  if (state.status === "load") return <p className="p-4 text-sm text-slate-500">Đang tải file gốc…</p>;

  const { kind } = state;
  const name = filename ? ` · ${filename}` : "";
  if (kind === "pdf-native") {
    return (
      <div className="flex h-full flex-col">
        <Toolbar label={`PDF${name}`} zoom={1} setZoom={() => {}} />
        <p className="bg-amber-50 px-3 py-1 text-xs text-amber-800">Không nạp được trình xem tích hợp (cần mạng) nên dùng trình xem PDF của trình duyệt.</p>
        <iframe title="Hóa đơn gốc (PDF)" src={state.url} className="min-h-0 w-full flex-1 bg-slate-200" />
      </div>
    );
  }
  const isXml = kind === "xml";
  const label = isXml ? `XML${name}` : kind === "pdf" ? `PDF${name}${state.items.length > 1 ? ` · ${state.items.length} trang` : ""}` : `Ảnh${name}`;
  return (
    <div className="flex h-full flex-col bg-white">
      <Toolbar label={label} zoom={zoom} setZoom={setZoom} rot={rot} setRot={isXml ? null : setRot}
        extra={isXml && (
          <button type="button" className={btn} onClick={() => setRaw((v) => !v)}>{raw ? "Xem dạng cây" : "Xem bản gốc"}</button>
        )} />
      <div ref={area} className="min-h-0 flex-1 overflow-auto bg-slate-200 p-3">
        {isXml
          ? <XmlView text={state.text} zoom={zoom} raw={raw} />
          : <div className="space-y-3">{state.items.map((it, i) => <CanvasPage key={i} item={it} width={width * zoom} rot={rot} />)}</div>}
      </div>
    </div>
  );
}
