import { useEffect, useRef, useState } from "react";
import { api, uploadWithProgress } from "../../api/client.js";
import InvoiceList from "./InvoiceList.jsx";
import { creep } from "./smoothProgress.js";
import { isKTV, useUser } from "../../userContext.js";

const ACCEPT = ".pdf,.png,.jpg,.jpeg,.xml";
const MAX_MB = 10;
const MAX_FILES = 10;           // toi da so file dang cho/dang xu ly cung luc (XML doc ngay, PDF/anh phai qua OCR nen cham)
const MAX_PARALLEL_SCANS = 2;   // PDF/anh: toi da bay nhieu file duoc he thong doc cung luc; file sau cho file truoc xong
const UPLOAD_SHARE = 25;        // thanh tien do: 0-25% la tai len, 25-100% la he thong doc du lieu
const SUCCESS_SHOW_MS = 8000;   // thong bao thanh cong hien vai giay roi tu mat
const POLL_MS = 1000;
const POLL_LIMIT_MS = 10 * 60 * 1000;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// Trang tai hoa don: keo tha nhieu file (PDF, anh, XML), tai tuan tu, roi hien danh sach va trang thai.
export default function Upload() {
  const canUpload = isKTV(useUser());   // KTT chi xem danh sach va xoa, khong tai hoa don
  const [queue, setQueue] = useState([]);   // [{id, name, state: cho|dang_tai|xong|loi, msg}]
  const [refreshKey, setRefreshKey] = useState(0);
  const [over, setOver] = useState(false);
  const input = useRef(null);
  const busy = useRef(false);
  const todo = useRef([]);          // hang doi file chua tai len
  const nextId = useRef(1);
  const scansReading = useRef(0);   // so file PDF/anh dang duoc he thong doc
  const alive = useRef(true);
  useEffect(() => () => { alive.current = false; }, []);

  const patch = (id, p) => setQueue((q) => q.map((x) => (x.id === id ? { ...x, ...p } : x)));

  // Hoi tien do doc du lieu cua mot hoa don cho den khi xong; chay song song, khong chan viec tai file tiep theo.
  async function watch(id, invoiceId) {
    const t0 = Date.now();
    let fails = 0;
    let shown = 0;   // phan tram (0-100 cua giai doan doc) dang hien, de thanh nhich dan giua cac moc
    while (alive.current && Date.now() - t0 < POLL_LIMIT_MS) {
      try {
        const { data } = await api(`/api/invoices/${invoiceId}/progress`);
        fails = 0;
        if (data.status !== "dang_xu_ly") {
          if (data.status === "loi_xu_ly") {
            patch(id, { state: "loi", msg: "Không đọc được hóa đơn (dịch vụ AI tắt hoặc hết hạn mức). Vào danh sách bấm “Xử lý lại”." });
          } else {
            patch(id, { state: "xong", msg: "Đọc dữ liệu thành công" });
            setTimeout(() => alive.current && setQueue((q) => q.filter((x) => x.id !== id)), SUCCESS_SHOW_MS);
          }
          setRefreshKey((k) => k + 1);
          return;
        }
        shown = creep(shown, data.percent);
        patch(id, { state: "dang_doc", percent: UPLOAD_SHARE + Math.round((shown * (100 - UPLOAD_SHARE)) / 100), stage: data.stage });
      } catch {
        if (++fails >= 5) break;
      }
      await sleep(POLL_MS);
    }
    if (alive.current) patch(id, { state: "xong", msg: "Đã nhận; xem kết quả trong danh sách bên dưới" });
  }

  async function uploadAll(files) {
    // file con dang cho / dang tai / dang doc chiem cho; vuot MAX_FILES thi tu choi phan thua, tai lai sau khi xong
    let room = MAX_FILES - queue.filter((x) => ["cho", "dang_tai", "dang_doc"].includes(x.state)).length;
    const items = files.map((file) => {
      const ext = file.name.split(".").pop().toLowerCase();
      let bad = !ACCEPT.includes(`.${ext}`) ? "Chỉ nhận PDF, PNG, JPG, XML"
        : file.size > MAX_MB * 1024 * 1024 ? `Lớn hơn ${MAX_MB} MB` : "";
      if (!bad && room-- <= 0) bad = `Vượt giới hạn ${MAX_FILES} file mỗi lần, hãy tải lại sau khi các file trên xong`;
      return { id: nextId.current++, file, name: file.name, state: bad ? "loi" : "cho", msg: bad };
    });
    setQueue((q) => [...items.map(({ file, ...rest }) => rest), ...q]);
    todo.current.push(...items.filter((i) => i.state === "cho"));
    if (busy.current) return;           // dang tai dot truoc: vong lap hien tai se lay tiep cac file vua them vao todo
    busy.current = true;
    while (todo.current.length) {
      const it = todo.current.shift();
      const isScan = !it.name.toLowerCase().endsWith(".xml");
      // PDF/anh di qua OCR (cham, doc lan luot): chi day them file khi he thong con ranh, tranh xep hang qua dai bi timeout
      if (isScan && scansReading.current >= MAX_PARALLEL_SCANS) {
        patch(it.id, { msg: "Chờ file trước đọc xong" });
        while (alive.current && scansReading.current >= MAX_PARALLEL_SCANS) await sleep(500);
      }
      patch(it.id, { state: "dang_tai", percent: 0, stage: "Đang tải lên" });
      try {
        const fd = new FormData();
        fd.append("file", it.file);
        const { data } = await uploadWithProgress("/api/invoices", fd,
          (p) => patch(it.id, { percent: Math.round((p * UPLOAD_SHARE) / 100) }));
        if (data.status === "dang_xu_ly") {
          patch(it.id, { state: "dang_doc", percent: UPLOAD_SHARE, stage: "Đã nhận, đang chờ xử lý" });
          scansReading.current++;
          watch(it.id, data.invoice_id).finally(() => { scansReading.current--; });   // khong await: tai file ke tiep ngay
        } else if (data.status === "loi_xu_ly") {
          patch(it.id, { state: "loi", msg: "Không đọc được hóa đơn" });
        } else {                                    // XML: doc xong ngay khi tai len
          patch(it.id, { state: "xong", msg: "Đọc dữ liệu thành công" });
          setTimeout(() => alive.current && setQueue((q) => q.filter((x) => x.id !== it.id)), SUCCESS_SHOW_MS);
        }
      } catch (e) {
        patch(it.id, { state: "loi", msg: e.message });
      }
      setRefreshKey((k) => k + 1);
    }
    busy.current = false;
  }

  const pick = (list) => list.length && uploadAll([...list]);

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">{canUpload ? "Tải hóa đơn" : "Danh sách hóa đơn"}</h1>
      {canUpload && <div
        onDragOver={(e) => { e.preventDefault(); setOver(true); }}
        onDragLeave={() => setOver(false)}
        onDrop={(e) => { e.preventDefault(); setOver(false); pick(e.dataTransfer.files); }}
        onClick={() => input.current?.click()}
        role="button" tabIndex={0}
        onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && input.current?.click()}
        className={`cursor-pointer rounded-lg border-2 border-dashed p-8 text-center ${over ? "border-blue-500 bg-blue-50" : "border-slate-300 bg-white"}`}
      >
        <p className="font-medium">Kéo thả hóa đơn vào đây hoặc bấm để chọn</p>
        <p className="mt-1 text-sm text-slate-500">PDF, ảnh (PNG, JPG) hoặc XML hóa đơn điện tử · tối đa {MAX_MB} MB mỗi file · tối đa {MAX_FILES} file mỗi lần</p>
        <input ref={input} type="file" multiple accept={ACCEPT} className="hidden"
          onChange={(e) => { pick(e.target.files); e.target.value = ""; }} />
      </div>}

      {canUpload && queue.length > 0 && (
        <ul className="space-y-1 text-sm">
          {[...queue.filter((x) => x.state === "loi"), ...queue.filter((x) => x.state !== "loi")].slice(0, 12).map((x) => {   // file loi/bi tu choi len dau de khong bi che
            const working = x.state === "dang_tai" || x.state === "dang_doc";
            return (
              <li key={x.id} className="rounded border bg-white px-3 py-1.5">
                <div className="flex items-center gap-2">
                  <span className="truncate">{x.name}</span>
                  <span className={`ml-auto shrink-0 ${x.state === "loi" ? "text-red-600" : x.state === "xong" ? "text-green-700" : "text-slate-500"}`}>
                    {x.state === "cho" ? (x.msg || "Đang chờ")
                      : working ? `${x.stage} · ${x.percent}%`
                      : x.state === "xong" ? `✓ ${x.msg}` : x.msg}
                  </span>
                </div>
                {working && (
                  <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-slate-200" role="progressbar"
                    aria-valuemin={0} aria-valuemax={100} aria-valuenow={x.percent} aria-label={`Tiến độ ${x.name}`}>
                    <div className="h-full rounded-full bg-blue-600 transition-all duration-500" style={{ width: `${x.percent}%` }} />
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}

      <InvoiceList refreshKey={refreshKey} />
    </div>
  );
}
