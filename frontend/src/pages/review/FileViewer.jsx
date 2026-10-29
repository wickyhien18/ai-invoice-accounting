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

// --- XML: hien thi giong trang tra cuu hoa don dien tu (tieu de, ben ban/ben mua, bang hang hoa, tong tien) ---
// Doc theo ten the (bo namespace) de chay duoc ca file that lan file mo phong.
const ln = (n) => n.localName || n.nodeName.replace(/^.*:/, "");
const kids = (n, name) => [...n.children].filter((c) => ln(c) === name);
const pick = (n, ...path) => path.reduce((cur, name) => (cur ? kids(cur, name)[0] || null : null), n);
const val = (n, ...path) => { const e = pick(n, ...path); return e ? e.textContent.trim() : ""; };
const numVN = (v) => (v === "" || isNaN(Number(v)) ? v : new Intl.NumberFormat("vi-VN").format(Number(v)));
const dateVN = (v) => { const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(v); return m ? `${m[3]}/${m[2]}/${m[1]}` : v; };

function Party({ title, p }) {
  const rows = [["Tên đơn vị", val(p, "Ten")], ["Mã số thuế", val(p, "MST")], ["Địa chỉ", val(p, "DChi")]];
  return (
    <div style={{ marginTop: "0.9em" }}>
      <div style={{ fontWeight: 700, borderBottom: "1px solid #94a3b8", paddingBottom: 2, marginBottom: 4 }}>{title}</div>
      {rows.filter(([, v]) => v).map(([k, v]) => (
        <div key={k} style={{ display: "flex", gap: 8, padding: "1px 0" }}>
          <span style={{ width: "7.5em", flexShrink: 0, color: "#475569" }}>{k}:</span>
          <span style={{ fontWeight: k === "Tên đơn vị" ? 700 : 400, wordBreak: "break-word" }}>{v}</span>
        </div>
      ))}
    </div>
  );
}

function InvoiceView({ doc, zoom }) {
  const root = doc.documentElement;
  const dl = pick(root, "DLHDon") || root;
  const tt = pick(dl, "TTChung"), nd = pick(dl, "NDHDon") || dl;
  const seller = pick(nd, "NBan"), buyer = pick(nd, "NMua"), tot = pick(nd, "TToan");
  const items = (pick(nd, "DSHHDVu") ? kids(pick(nd, "DSHHDVu"), "HHDVu") : []);
  const title = (tt && val(tt, "THDon")) || "Hóa đơn";
  const mccqt = val(root, "MCCQT");
  const th = { border: "1px solid #94a3b8", padding: "4px 6px", background: "#e2e8f0", fontWeight: 700, textAlign: "center" };
  const td = { border: "1px solid #cbd5e1", padding: "4px 6px", verticalAlign: "top" };
  const num = { ...td, textAlign: "right", fontVariantNumeric: "tabular-nums", whiteSpace: "nowrap" };
  const meta = tt ? [["Ký hiệu mẫu số", val(tt, "KHMSHDon")], ["Ký hiệu", val(tt, "KHHDon")], ["Số", val(tt, "SHDon")]].filter(([, v]) => v) : [];
  const sums = tot ? [["Cộng tiền hàng (chưa thuế)", val(tot, "TgTCThue")], ["Tiền thuế GTGT", val(tot, "TgTThue")]].filter(([, v]) => v) : [];
  const total = tot ? val(tot, "TgTTTBSo") : "";
  const words = tot ? val(tot, "TgTTTBChu") : "";
  const cur = tt ? val(tt, "DVTTe") : "";
  return (
    // nen giay trang co dinh (khong doi theo che do toi) de giong hoa don that
    <div style={{ background: "#fff", color: "#0f172a", fontSize: 14 * zoom, lineHeight: 1.5, padding: "1.2em 1.4em", borderRadius: 2, boxShadow: "0 1px 4px rgba(0,0,0,.25)" }}>
      <div style={{ textAlign: "center", marginBottom: "0.8em" }}>
        <div style={{ fontSize: "1.4em", fontWeight: 800, textTransform: "uppercase", color: "#1e3a8a" }}>{title}</div>
        {tt && val(tt, "NLap") && <div style={{ fontStyle: "italic" }}>Ngày lập: {dateVN(val(tt, "NLap"))}</div>}
        <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: "0 1.4em", marginTop: 4 }}>
          {meta.map(([k, v]) => <span key={k}>{k}: <b>{v}</b></span>)}
        </div>
        {mccqt && <div style={{ marginTop: 4, color: "#475569" }}>Mã của cơ quan thuế: <b style={{ color: "#0f172a" }}>{mccqt}</b></div>}
      </div>

      {seller && <Party title="Người bán" p={seller} />}
      {buyer && <Party title="Người mua" p={buyer} />}
      {tt && (val(tt, "HTTToan") || cur) && (
        <div style={{ marginTop: "0.6em", color: "#475569" }}>
          {val(tt, "HTTToan") && <>Hình thức thanh toán: <b style={{ color: "#0f172a" }}>{val(tt, "HTTToan")}</b></>}
          {val(tt, "HTTToan") && cur && " · "}
          {cur && <>Đồng tiền: <b style={{ color: "#0f172a" }}>{cur}</b></>}
        </div>
      )}

      <div style={{ overflowX: "auto", marginTop: "0.9em" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.93em" }}>
          <thead>
            <tr>{["STT", "Tên hàng hóa, dịch vụ", "ĐVT", "Số lượng", "Đơn giá", "Thành tiền", "Thuế suất"].map((h) => <th key={h} style={th}>{h}</th>)}</tr>
          </thead>
          <tbody>
            {items.map((it, i) => (
              <tr key={i}>
                <td style={{ ...td, textAlign: "center" }}>{val(it, "STT") || i + 1}</td>
                <td style={td}>{val(it, "THHDVu")}</td>
                <td style={{ ...td, textAlign: "center" }}>{val(it, "DVTinh")}</td>
                <td style={num}>{numVN(val(it, "SLuong"))}</td>
                <td style={num}>{numVN(val(it, "DGia"))}</td>
                <td style={num}>{numVN(val(it, "ThTien"))}</td>
                <td style={{ ...td, textAlign: "center" }}>{val(it, "TSuat")}</td>
              </tr>
            ))}
            {items.length === 0 && <tr><td colSpan={7} style={{ ...td, textAlign: "center", color: "#64748b" }}>Không có dòng hàng hóa, dịch vụ</td></tr>}
          </tbody>
        </table>
      </div>

      <div style={{ marginTop: "0.8em", marginLeft: "auto", maxWidth: "26em" }}>
        {sums.map(([k, v]) => (
          <div key={k} style={{ display: "flex", justifyContent: "space-between", gap: 12, padding: "2px 0" }}>
            <span>{k}:</span><span style={{ fontVariantNumeric: "tabular-nums" }}>{numVN(v)}</span>
          </div>
        ))}
        {total && (
          <div style={{ display: "flex", justifyContent: "space-between", gap: 12, padding: "4px 0", marginTop: 2, borderTop: "2px solid #1e3a8a", fontWeight: 800, fontSize: "1.08em" }}>
            <span>Tổng thanh toán:</span><span style={{ fontVariantNumeric: "tabular-nums" }}>{numVN(total)}{cur ? ` ${cur}` : ""}</span>
          </div>
        )}
      </div>
      {words && <div style={{ marginTop: "0.5em" }}>Số tiền viết bằng chữ: <i style={{ fontWeight: 600 }}>{words}</i></div>}
    </div>
  );
}

function XmlView({ text, zoom, view }) {
  const doc = new DOMParser().parseFromString(text, "application/xml");
  const ok = !doc.querySelector("parsererror");
  const isInvoice = ok && ln(doc.documentElement) === "HDon";
  const mode = view === "invoice" && !isInvoice ? "tree" : view;
  if (mode === "invoice") return <InvoiceView doc={doc} zoom={zoom} />;
  const root = ok && mode === "tree" ? [...doc.childNodes].filter((c) => c.nodeType === 1 || c.nodeType === 8) : null;
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
  const [view, setView] = useState("invoice");   // invoice | tree | raw (chi XML)
  const [width, setWidth] = useState(0);
  const area = useRef(null);

  useEffect(() => {
    let dead = false, url = null;
    setState({ status: "load" }); setZoom(1); setRot(0); setView("invoice");
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
          <div className="flex items-center gap-1" role="group" aria-label="Kiểu hiển thị XML">
            {[["invoice", "Dạng hóa đơn"], ["tree", "Dạng cây"], ["raw", "Bản gốc"]].map(([k, t]) => (
              <button key={k} type="button" aria-pressed={view === k} onClick={() => setView(k)}
                className={view === k ? "rounded border border-blue-600 bg-blue-600 px-2 py-1 text-sm font-medium text-white" : btn}>{t}</button>
            ))}
          </div>
        )} />
      <div ref={area} className="min-h-0 flex-1 overflow-auto bg-slate-200 p-3">
        {isXml
          ? <XmlView text={state.text} zoom={zoom} view={view} />
          : <div className="space-y-3">{state.items.map((it, i) => <CanvasPage key={i} item={it} width={width * zoom} rot={rot} />)}</div>}
      </div>
    </div>
  );
}
